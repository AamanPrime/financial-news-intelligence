import re
import string
from typing import List, Tuple

class TextPreprocessor:
    """Clean and preprocess financial news text"""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text: lowercase, remove extra whitespace
        
        Args:
            text: Raw text
            
        Returns:
            Normalized text
        """
        # Lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove HTML entities
        text = re.sub(r'&\w+;', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def remove_noise(text: str) -> str:
        """
        Remove noise: special characters, numbers (optional)
        Preserves monetary values and percentages
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Keep monetary patterns like $100, €50, etc.
        # Keep percentage patterns like 5%, 10.5%
        # Keep numbers in context
        
        # Remove excessive punctuation
        text = re.sub(r'[^\w\s$€£¥%\-\.]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split long articles into overlapping chunks for NLP processing
        
        Args:
            text: Full article text
            chunk_size: Number of characters per chunk
            overlap: Number of overlapping characters between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            
            if end >= len(text):
                break
        
        return chunks if chunks else [text]
    
    @staticmethod
    def extract_sentences(text: str) -> List[str]:
        """
        Extract sentences from text
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Split by common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    @staticmethod
    def preprocess_pipeline(text: str, chunk: bool = True) -> List[str]:
        """
        Complete preprocessing pipeline
        
        Args:
            text: Raw article text
            chunk: Whether to chunk long texts
            
        Returns:
            List of processed text chunks/sentences
        """
        # Normalize
        text = TextPreprocessor.normalize_text(text)
        
        # Remove noise
        text = TextPreprocessor.remove_noise(text)
        
        # Chunk if needed
        if chunk and len(text) > 1024:
            chunks = TextPreprocessor.chunk_text(text)
            return chunks
        else:
            return [text]
