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
    - Automatic API documentation (available at /docs)

Example Usage:
    curl -X POST "http://localhost:8000/recommend" \\
         -H "Content-Type: application/json" \\
         -d '{"terms": ["World War II", "Pacific Theater"]}'
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

from scraper import LCSHScraper
from similarity import SimilarityEngine

# Initialize FastAPI application with metadata
app = FastAPI(
    title="LCSH API",
    description="API for Library of Congress Subject Headings recommendations",
    version="1.0.0"
)

class RecommendRequest(BaseModel):
    """
    Pydantic model for the recommendation request payload.
    
    Attributes:
        terms (List[str]): List of search terms to find LCSH recommendations for.
            Example: ["China--History--Republic, 1912-1949"]
    """
    terms: List[str]

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

# Initialize components
scraper = LCSHScraper()
similarity_engine = SimilarityEngine()

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """
    Endpoint to get LCSH recommendations based on input terms.
    
    This endpoint performs the following steps:
    1. Validates the input terms
    2. Searches the LOC website for candidate terms
    3. Computes similarity scores between input and candidates
    4. Returns the most similar terms as recommendations

    Args:
        request (RecommendRequest): The request object containing search terms

    Returns:
        RecommendResponse: Object containing list of recommendations, each with:
            - term: The LCSH term
            - id: LOC identifier
            - url: Term's URL
            - similarity_score: Relevance score

    Raises:
        HTTPException(400): If no terms are provided in the request
        HTTPException(404): If no LCSH terms are found for the provided terms

    Example:
        Request:
        {
            "terms": ["China--History--Republic, 1912-1949"]
        }

        Response:
        {
            "recommendations": [
                {
                    "term": "China--History--Republic, 1912-1949",
                    "id": "sh85024107",
                    "url": "https://id.loc.gov/authorities/subjects/sh85024107",
                    "similarity_score": 1.0
                },
                ...
            ]
        }
    """
    if not request.terms:
        raise HTTPException(status_code=400, detail="No terms provided")
    
    # Collect candidates from all terms
    all_candidates = []
    for term in request.terms:
        candidates = scraper.search_terms(term)
        all_candidates.extend(candidates)
    
    if not all_candidates:
        raise HTTPException(
            status_code=404,
            detail="No LCSH terms found for the provided terms"
        )
    
    # Compute similarities and get top recommendations
    recommendations = similarity_engine.compute_similarities(
        request.terms,
        all_candidates,
        top_k=10
    )
    
    return RecommendResponse(recommendations=recommendations)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 