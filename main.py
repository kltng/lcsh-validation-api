"""
LCSH Recommendation API

This module provides a FastAPI-based web service that recommends Library of Congress
Subject Headings (LCSH) based on input keywords. It combines web scraping of the LOC
website with similarity-based term matching to suggest relevant subject headings.

The API accepts search terms, fetches candidate terms from LOC, and returns the most
semantically similar LCSH terms along with their metadata.

Features:
    - FastAPI endpoint for LCSH recommendations
    - Input validation using Pydantic models
    - Configurable number of recommendations
    - Detailed error handling
    - Rate limiting protection
    - API key authentication
    - OpenAPI documentation (available at /docs and /openapi.json)
    - Automatic API documentation (available at /docs)

Example Usage:
    # Multiple terms (recommended format)
    curl -X POST "http://localhost:8000/recommend" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: your_api_key_here" \\
         -d '{"terms": ["Digital humanities", "Data modeling"]}'

    # Single term
    curl -X POST "http://localhost:8000/recommend" \\
         -H "Content-Type: application/json" \\
         -H "X-API-Key: your_api_key_here" \\
         -d '{"terms": "Digital humanities"}'
    
    # Get OpenAPI schema
    curl -X GET "http://localhost:8000/openapi.json" > openapi.json
"""

from fastapi import FastAPI, HTTPException, Request, Depends, Security, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, validator
from typing import List, Dict, Union, Any, Optional
import uvicorn
import time
from datetime import datetime, timedelta
import logging
import ast
import json
import os
from dotenv import load_dotenv

from scraper import LCSHScraper
from similarity import SimilarityEngine

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API key configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get API keys from environment variables or use a default for development
API_KEYS = os.getenv("API_KEYS", "test_key").split(",")

# Initialize FastAPI application with metadata
app = FastAPI(
    title="LCSH API",
    description="API for Library of Congress Subject Headings recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Custom OpenAPI schema with additional information
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="LCSH Validation API",
        version="1.0.0",
        description="API for Library of Congress Subject Headings recommendations and validation",
        routes=app.routes,
    )
    
    # Add additional information
    openapi_schema["info"]["x-logo"] = {
        "url": "https://www.loc.gov/static/images/logo-loc-new-branding.svg"
    }
    
    openapi_schema["info"]["contact"] = {
        "name": "LCSH Validation API Support",
        "url": "https://github.com/kltng/lcsh-validation-api",
        "email": "support@example.com"  # Replace with actual support email
    }
    
    # Add security scheme for API key
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": API_KEY_NAME
        }
    }
    
    # Apply security requirement to all endpoints
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    # Add examples to the schema
    for path in openapi_schema["paths"]:
        if path == "/recommend":
            for method in openapi_schema["paths"][path]:
                if method == "post":
                    # Add request examples
                    openapi_schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"] = {
                        "multiple_terms": {
                            "summary": "Multiple terms (recommended)",
                            "value": {"terms": ["Digital humanities", "Data modeling"]}
                        },
                        "single_term": {
                            "summary": "Single term",
                            "value": {"terms": "Digital humanities"}
                        }
                    }
                    
                    # Add response examples
                    openapi_schema["paths"][path][method]["responses"]["200"]["content"]["application/json"]["examples"] = {
                        "successful_response": {
                            "summary": "Successful response",
                            "value": {
                                "recommendations": [
                                    {
                                        "term": "Digital humanities",
                                        "id": "sh85124003",
                                        "url": "https://id.loc.gov/authorities/subjects/sh85124003",
                                        "similarity_score": 1.0
                                    },
                                    {
                                        "term": "Humanities--Data processing",
                                        "id": "sh85062987",
                                        "url": "https://id.loc.gov/authorities/subjects/sh85062987",
                                        "similarity_score": 0.85
                                    }
                                ]
                            }
                        }
                    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Create a dedicated endpoint for OpenAPI schema
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """
    Get the OpenAPI schema as JSON.
    
    This endpoint returns the complete OpenAPI schema for the API,
    which can be used with tools like Swagger UI, Postman, or
    for generating client libraries.
    """
    return JSONResponse(content=app.openapi())

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Dependency to validate API key.
    
    Args:
        api_key_header (str): API key from request header
        
    Returns:
        str: Validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if api_key_header is None:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=401,
            detail="API key is missing. Please provide a valid API key in the X-API-Key header."
        )
    
    if api_key_header not in API_KEYS:
        logger.warning(f"Invalid API key: {api_key_header[:5]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please provide a valid API key."
        )
    
    return api_key_header

class RateLimiter:
    """
    Simple in-memory rate limiter to protect the API from too frequent requests.
    
    Attributes:
        requests (Dict): Dictionary storing request timestamps for each client
        rate_limit (int): Maximum number of requests allowed per time window
        time_window (int): Time window in seconds
    """
    def __init__(self, rate_limit: int = 10, time_window: int = 60):
        """
        Initialize rate limiter with configurable limits.
        
        Args:
            rate_limit (int): Maximum requests allowed per time window
            time_window (int): Time window in seconds
        """
        self.requests: Dict[str, List[datetime]] = {}
        self.rate_limit = rate_limit
        self.time_window = time_window

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if a request from the client is allowed.
        
        Args:
            client_id (str): Identifier for the client (e.g., IP address)
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        now = datetime.now()
        
        # Initialize client's request history if not exists
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the time window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        
        # Check if client has exceeded rate limit
        if len(self.requests[client_id]) >= self.rate_limit:
            return False
        
        # Add current request timestamp
        self.requests[client_id].append(now)
        return True

# Initialize components
scraper = LCSHScraper()
similarity_engine = SimilarityEngine()
rate_limiter = RateLimiter(rate_limit=10, time_window=60)  # 10 requests per minute

class RecommendRequest(BaseModel):
    """
    Pydantic model for the recommendation request payload.
    
    Attributes:
        terms (Union[List[str], str]): Search terms to find LCSH recommendations for.
            Can be either:
            1. A list of strings (recommended):
               {"terms": ["Digital humanities", "Data modeling"]}
            2. A single string:
               {"terms": "Digital humanities"}
    """
    terms: Union[List[str], str]

    @validator('terms')
    def validate_terms(cls, v):
        """
        Validate and convert terms input to proper format.
        Handles both list and string inputs.
        
        For GenAI agents and programmatic access, use a proper JSON array:
        {"terms": ["term1", "term2"]}
        """
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                # If it's a single string, wrap it in a list
                return [v]
        elif isinstance(v, list):
            return v
        raise ValueError("Terms must be either a list of strings or a single string")

class Recommendation(BaseModel):
    """
    Pydantic model for a single LCSH recommendation.
    
    Attributes:
        term (str): The recommended LCSH term
        id (str): The LOC identifier for the term
        url (str): The full URL to the term's page on id.loc.gov
        similarity_score (float): Cosine similarity score between input and this term
    """
    term: str
    id: str
    url: str
    similarity_score: float

class RecommendResponse(BaseModel):
    """
    Pydantic model for the recommendation response.
    
    Attributes:
        recommendations (List[Recommendation]): List of recommended LCSH terms
            with their metadata and similarity scores
    """
    recommendations: List[Recommendation]

async def check_rate_limit(request: Request):
    """
    Dependency to check rate limit before processing request.
    
    Args:
        request (Request): FastAPI request object
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    client_id = request.client.host
    if not rate_limiter.is_allowed(client_id):
        logger.warning(f"Rate limit exceeded for client: {client_id}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(
    request: Request, 
    req: RecommendRequest, 
    api_key: str = Depends(get_api_key),
    rate_check=Depends(check_rate_limit)
):
    """
    Endpoint to get LCSH recommendations based on input terms.
    
    This endpoint performs the following steps:
    1. Validates the API key
    2. Validates the input terms
    3. Checks rate limiting
    4. Searches the LOC website for candidate terms
    5. Computes similarity scores between input and candidates
    6. Returns the most similar terms as recommendations

    Args:
        request (Request): FastAPI request object
        req (RecommendRequest): The request object containing search terms
        api_key (str): API key for authentication
        rate_check: Dependency injection for rate limiting

    Returns:
        RecommendResponse: Object containing list of recommendations, each with:
            - term: The LCSH term
            - id: LOC identifier
            - url: Term's URL
            - similarity_score: Relevance score

    Raises:
        HTTPException(400): If no terms are provided in the request
        HTTPException(401): If API key is missing or invalid
        HTTPException(404): If no LCSH terms are found for the provided terms
        HTTPException(429): If rate limit is exceeded

    Example Request Formats:
        1. Multiple terms (recommended for GenAI agents):
           {
               "terms": ["Digital humanities", "Data modeling"]
           }

        2. Single term:
           {
               "terms": "Digital humanities"
           }

    Example Response:
        {
            "recommendations": [
                {
                    "term": "Digital humanities",
                    "id": "sh85124003",
                    "url": "https://id.loc.gov/authorities/subjects/sh85124003",
                    "similarity_score": 1.0
                },
                ...
            ]
        }
    """
    if not req.terms:
        raise HTTPException(status_code=400, detail="No terms provided")
    
    # Log request
    logger.info(f"Processing authenticated request from {request.client.host} with terms: {req.terms}")
    
    # Collect candidates from all terms
    all_candidates = []
    for term in req.terms:
        candidates = scraper.search_terms(term)
        all_candidates.extend(candidates)
    
    if not all_candidates:
        raise HTTPException(
            status_code=404,
            detail="No LCSH terms found for the provided terms"
        )
    
    # Compute similarities and get top recommendations
    recommendations = similarity_engine.compute_similarities(
        req.terms,
        all_candidates,
        top_k=20
    )
    
    logger.info(f"Returning {len(recommendations)} recommendations")
    return RecommendResponse(recommendations=recommendations)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 