"""
LCSH Similarity Engine

This module provides functionality to compute semantic similarities between search terms
and Library of Congress Subject Headings (LCSH). It uses TF-IDF vectorization and
cosine similarity to find the most relevant LCSH terms for given search queries.

The implementation is designed to be resource-efficient, using scikit-learn's TF-IDF
vectorizer instead of heavy neural network models.

Example:
    engine = SimilarityEngine()
    candidates = [
        {"term": "China--History--Republic, 1912-1949", "id": "sh85024107"},
        {"term": "World War, 1939-1945", "id": "sh85148273"}
    ]
    results = engine.compute_similarities(["China history"], candidates)
    for result in results:
        print(f"Term: {result['term']}")
        print(f"Score: {result['similarity_score']}")
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import numpy as np

class SimilarityEngine:
    """
    A lightweight engine for computing similarities between search terms and LCSH terms.
    
    This class uses TF-IDF (Term Frequency-Inverse Document Frequency) vectorization
    to convert text into numerical vectors, then computes cosine similarity between
    these vectors to find the most relevant matches.

    The engine is optimized for performance and resource usage, making it suitable
    for deployment without GPU requirements.

    Attributes:
        vectorizer (TfidfVectorizer): Scikit-learn vectorizer for text processing
    """

    def __init__(self):
        """
        Initialize the similarity engine with a TF-IDF vectorizer.
        
        The vectorizer is configured to:
        - Convert text to lowercase
        - Use both unigrams and bigrams for better phrase matching
        - Remove English stop words
        """
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Use both unigrams and bigrams
            stop_words='english'
        )

    def compute_similarities(
        self,
        query_terms: List[str],
        candidates: List[Dict[str, str]],
        top_k: int = 10
    ) -> List[Dict]:
        """
        Compute similarities between query terms and candidate LCSH terms.

        This method performs the following steps:
        1. Combines all query terms into a single string
        2. Extracts terms from candidate dictionaries
        3. Computes TF-IDF vectors for all texts
        4. Calculates cosine similarities between query and candidates
        5. Returns the top_k most similar terms

        Args:
            query_terms (List[str]): List of search query terms
            candidates (List[Dict[str, str]]): List of candidate LCSH terms with their metadata
            top_k (int, optional): Number of top matches to return. Defaults to 10.

        Returns:
            List[Dict]: A list of dictionaries containing the top_k most similar terms,
                       sorted by similarity score in descending order. Each dictionary contains:
                       - term: The LCSH term
                       - id: The LCSH identifier
                       - url: The term's URL
                       - similarity_score: Cosine similarity score (0 to 1)

        Example:
            >>> engine = SimilarityEngine()
            >>> results = engine.compute_similarities(
            ...     ["World War II"],
            ...     [{"term": "World War, 1939-1945", "id": "sh85148273"}]
            ... )
            >>> results[0]
            {
                'term': 'World War, 1939-1945',
                'id': 'sh85148273',
                'similarity_score': 0.876
            }
        """
        if not query_terms or not candidates:
            return []

        # Combine query terms into a single string
        query_text = " ".join(query_terms)
        
        # Get candidate terms
        candidate_terms = [c["term"] for c in candidates]
        
        # Add query to the list of texts to vectorize
        all_texts = [query_text] + candidate_terms
        
        # Compute TF-IDF vectors
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        
        # Get query vector (first row) and candidate vectors
        query_vector = tfidf_matrix[0:1]
        candidate_vectors = tfidf_matrix[1:]
        
        # Compute cosine similarities
        similarities = cosine_similarity(query_vector, candidate_vectors)[0]
        
        # Get top_k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Create result list
        results = []
        for idx in top_indices:
            candidate = candidates[idx]
            score = similarities[idx]
            results.append({
                "term": candidate["term"],
                "id": candidate["id"],
                "url": candidate["url"],
                "similarity_score": round(float(score), 3)
            })
        
        return results 