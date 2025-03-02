#!/usr/bin/env python3
"""
API Key Generator for LCSH API

This script generates secure random API keys that can be used with the LCSH API.
It outputs the key to the console and provides instructions on how to use it.

Usage:
    python generate_api_key.py
"""

import secrets
import string
import argparse

def generate_api_key(length=32):
    """
    Generate a secure random API key.
    
    Args:
        length (int): Length of the API key to generate
        
    Returns:
        str: A secure random API key
    """
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key

def main():
    parser = argparse.ArgumentParser(description='Generate a secure API key for LCSH API')
    parser.add_argument('--length', type=int, default=32, help='Length of the API key (default: 32)')
    args = parser.parse_args()
    
    api_key = generate_api_key(args.length)
    
    print("\n=== LCSH API Key Generator ===\n")
    print(f"Your new API key: {api_key}")
    print("\nTo use this key with the API:")
    print("1. Add it to your .env file:")
    print(f'   API_KEYS="{api_key}"')
    print("   (You can add multiple keys separated by commas)")
    print("\n2. Or pass it as an environment variable when running the container:")
    print(f'   docker run -e API_KEYS="{api_key}" -p 8000:8000 lcsh-api')
    print("\n3. Include it in your API requests:")
    print(f'   curl -H "X-API-Key: {api_key}" -X POST "http://localhost:8000/recommend" -H "Content-Type: application/json" -d \'{"terms": ["Digital humanities"]}\'')
    print("\nKeep this key secure and don't share it publicly!")

if __name__ == "__main__":
    main() 