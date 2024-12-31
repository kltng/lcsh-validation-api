# LCSH API

A FastAPI-based API service that provides Library of Congress Subject Headings (LCSH) recommendations based on input keywords. The service scrapes the Library of Congress website, performs similarity comparisons, and returns the most relevant LCSH terms.

## Features

- Web scraping of LOC website for LCSH terms
- Semantic similarity comparison using sentence transformers
- FastAPI endpoint for term recommendations
- Rate limiting and caching support

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
uvicorn main:app --reload
```

2. Send a POST request to `/recommend` endpoint:
```json
{
    "terms": ["China--History--Republic, 1912-1949"]
}
```

3. Get recommendations in response:
```json
{
    "recommendations": [
        {
            "term": "...",
            "id": "sh85024107",
            "similarity_score": 0.92,
            "source": "LCSH"
        }
    ]
}
```

## API Documentation

Once the server is running, visit `/docs` for the interactive API documentation. 