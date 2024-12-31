# LCSH VALIDATION API

A FastAPI-based API service that provides Library of Congress Subject Headings (LCSH) recommendations based on input keywords. The service scrapes the Library of Congress website, performs similarity comparisons, and returns the most relevant LCSH terms.

## Features

- Web scraping of LOC website for LCSH terms
- Semantic similarity comparison using TF-IDF vectorization
- FastAPI endpoint for term recommendations
- Rate limiting and CORS support
- Docker containerization
- Resource management and health checks

## Installation

### Local Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Docker Installation

1. Clone the repository
2. Build and run using Docker Compose:
```bash
docker-compose up --build
```

Or run in detached mode:
```bash
docker-compose up -d --build
```

## Usage

### Running Locally

Start the server:
```bash
uvicorn main:app --reload
```

### Running with Docker

The Docker container will automatically start the server and expose port 8000. The service includes:
- Resource limits (1 CPU, 1GB RAM)
- Automatic restart on failure
- Health checks every 30 seconds
- 4 Uvicorn workers for better performance

### Making Requests

Send a POST request to `/recommend` endpoint:
```bash
curl -X POST "http://localhost:8000/recommend" \
     -H "Content-Type: application/json" \
     -d '{"terms": ["China--History--Republic, 1912-1949"]}'
```

Example response:
```json
{
    "recommendations": [
        {
            "term": "China--History--Republic, 1912-1949",
            "id": "sh85024107",
            "similarity_score": 0.92,
            "url": "https://id.loc.gov/authorities/subjects/sh85024107"
        }
    ]
}
```

## API Documentation

Once the server is running, visit:
- `/docs` for the interactive Swagger documentation
- `/redoc` for the ReDoc documentation

## Rate Limiting

The API includes rate limiting protection:
- 10 requests per minute per client IP
- HTTP 429 response when limit is exceeded
- Automatic cleanup of rate limit records

## Docker Configuration

### Resource Limits
- CPU: 1 core (minimum 0.5)
- Memory: 1GB (minimum 512MB)
- Workers: 4 Uvicorn workers

### Health Checks
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 3 attempts

### Volume Mounting
Development mode mounts the local directory to `/app` in the container for live code updates.

## Development

To modify resource limits or other Docker settings, adjust the `docker-compose.yml` file:
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
``` 