import spacy
from typing import List, Dict, Tuple
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extract named entities using spaCy NER"""
    
    MODEL_NAME = "en_core_web_sm"
    
    def __init__(self):
        """Initialize spaCy model"""
        try:
            self.nlp = spacy.load(self.MODEL_NAME)
        except OSError:
            logger.warning(f"Model {self.MODEL_NAME} not found. Downloading...")
            os.system(f"python -m spacy download {self.MODEL_NAME}")
            self.nlp = spacy.load(self.MODEL_NAME)
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract named entities from text using spaCy
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with entity lists grouped by type
        """
        doc = self.nlp(text)
        
        entities = {
            "organizations": [],
            "persons": [],
            "gpe": [],  # Geopolitical entities
            "money": [],
            "dates": [],
            "percent": [],
            "raw_ents": []
        }
        
        for ent in doc.ents:
            entity_info = {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            }
            
            if ent.label_ == "ORG":
                entities["organizations"].append(entity_info)
            elif ent.label_ == "PERSON":
                entities["persons"].append(entity_info)
            elif ent.label_ == "GPE":
                entities["gpe"].append(entity_info)
            elif ent.label_ == "MONEY":
                entities["money"].append(entity_info)
            elif ent.label_ == "DATE":
                entities["dates"].append(entity_info)
            elif ent.label_ == "PERCENT":
                entities["percent"].append(entity_info)
            
            entities["raw_ents"].append(entity_info)
        
        return entities
    
    def extract_financial_metrics(self, entities: Dict) -> Dict:
        """
        Extract key financial metrics from entities
        
        Args:
            entities: Entity dictionary from extract_entities
            
        Returns:
            Dictionary of financial metrics
        """
        metrics = {}
        
        # Extract monetary values
        if entities["money"]:
            metrics["monetary_values"] = [ent["text"] for ent in entities["money"]]
        
        # Extract percentages
        if entities["percent"]:
            metrics["percentages"] = [ent["text"] for ent in entities["percent"]]
        
        # Extract dates
        if entities["dates"]:
            metrics["dates"] = [ent["text"] for ent in entities["dates"]]
        
        return metrics
    
    def extract_companies(self, entities: Dict) -> List[str]:
        """
        Extract company/organization names
        
        Args:
            entities: Entity dictionary from extract_entities
            
        Returns:
            List of company names
        """
        companies = [ent["text"] for ent in entities["organizations"]]
        return list(set(companies))  # Remove duplicates
    
    def get_entity_summary(self, text: str) -> Dict:
        """
        Get summary of all extracted entities
        
        Args:
            text: Input text
            
        Returns:
            Complete entity extraction summary
        """
        entities = self.extract_entities(text)
        metrics = self.extract_financial_metrics(entities)
        companies = self.extract_companies(entities)
        
        return {
            "entities": entities,
            "metrics": metrics,
            "companies": companies,
            "total_entities": len(entities["raw_ents"])
        }
