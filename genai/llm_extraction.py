import json
from typing import Dict, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMExtractor:
    """Extract structured financial intelligence using Generative AI"""
    
    EVENT_TYPES = [
        "earnings",
        "merger",
        "acquisition",
        "lawsuit",
        "downgrade",
        "upgrade",
        "expansion",
        "regulation",
        "partnership",
        "bankruptcy",
        "other"
    ]
    
    SENTIMENT_OPTIONS = ["positive", "neutral", "negative"]
    
    EXTRACTION_PROMPT = """You are a financial intelligence expert. Extract structured information from the following news article.

ARTICLE TEXT:
{text}

Extract and return ONLY valid JSON (no markdown, no extra text) with this exact structure:
{{
    "company": "primary company mentioned (string or null)",
    "sector": "industry/sector (string or null)",
    "event_type": "one of: earnings, merger, acquisition, lawsuit, downgrade, upgrade, expansion, regulation, partnership, bankruptcy, other",
    "sentiment": "positive, neutral, or negative",
    "confidence_score": 0.0-1.0,
    "key_metrics": {{
        "revenue": "if mentioned",
        "profit": "if mentioned",
        "growth_percent": "if mentioned",
        "loss": "if mentioned"
    }},
    "summary": "brief 1-2 sentence summary"
}}

Return ONLY the JSON object, nothing else."""

    def __init__(self):
        """Initialize LLM client based on environment variables"""
        self.api_key = os.getenv("GENAI_API_KEY")
        self.model = os.getenv("GENAI_MODEL", "gemini-pro")
        self.use_gemini = os.getenv("USE_GEMINI", "true").lower() == "true"
        
        if self.use_gemini:
            self._init_gemini()
        else:
            self._init_openai()
    
    def _init_gemini(self):
        """Initialize Google Generative AI (Gemini)"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"Initialized Gemini with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.client = None
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            import openai
            openai.api_key = self.api_key
            self.client = openai
            logger.info(f"Initialized OpenAI with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.client = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def extract_with_retry(self, text: str) -> Optional[Dict]:
        """
        Extract structured information with retry logic
        
        Args:
            text: Article text to extract from
            
        Returns:
            Structured extraction dictionary or None
        """
        if not self.client:
            logger.error("LLM client not initialized")
            return None
        
        if not self.api_key:
            logger.error("GENAI_API_KEY not set in environment")
            return None
        
        try:
            prompt = self.EXTRACTION_PROMPT.format(text=text[:3000])  # Limit input
            
            if self.use_gemini:
                response = self.client.generate_content(prompt)
                response_text = response.text
            else:
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                response_text = response.choices[0].message.content
            
            # Parse JSON response
            extracted = self._parse_json_response(response_text)
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting with LLM: {e}")
            raise
    
    @staticmethod
    def _parse_json_response(response_text: str) -> Optional[Dict]:
        """
        Parse JSON from LLM response
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed dictionary or None
        """
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            # Parse JSON
            data = json.loads(response_text.strip())
            
            # Validate structure
            required_fields = ["company", "event_type", "sentiment"]
            if all(field in data for field in required_fields):
                return data
            else:
                logger.warning("Extracted JSON missing required fields")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response_text[:200]}")
            return None
    
    def validate_extraction(self, extraction: Dict) -> bool:
        """
        Validate extraction output against schema
        
        Args:
            extraction: Extracted data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        if not extraction:
            return False
        
        # Check event type
        if extraction.get("event_type") not in self.EVENT_TYPES:
            logger.warning(f"Invalid event_type: {extraction.get('event_type')}")
            return False
        
        # Check sentiment
        if extraction.get("sentiment") not in self.SENTIMENT_OPTIONS:
            logger.warning(f"Invalid sentiment: {extraction.get('sentiment')}")
            return False
        
        # Check confidence score
        confidence = extraction.get("confidence_score", 0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            logger.warning(f"Invalid confidence_score: {confidence}")
            return False
        
        return True
    
    def extract(self, text: str) -> Optional[Dict]:
        """
        Main extraction method with validation
        
        Args:
            text: Article text to extract from
            
        Returns:
            Validated extraction dictionary or None
        """
        try:
            extraction = self.extract_with_retry(text)
            if extraction and self.validate_extraction(extraction):
                return extraction
            else:
                logger.warning("Extraction validation failed")
                return None
        except Exception as e:
            logger.error(f"Extraction failed after retries: {e}")
            return None
