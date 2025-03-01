# Use Python 3.10 slim image as base (to match requires-python in pyproject.toml)
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system .

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 