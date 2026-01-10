"""
LLM Configuration Module

Centralized configuration for all LLM/AI model integrations.
Currently supports: Google Gemini API
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger("PDF_Agent.LLM")


class LLMConfig:
    """Centralized LLM configuration and model management"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini API
        genai.configure(api_key=self.api_key)
        
        # Model configuration
        self.model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        self.model = None
        
        logger.info(f"LLM Config initialized with model: {self.model_name}")
    
    def get_model(self):
        """Get or create the Gemini model instance"""
        if self.model is None:
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Created Gemini model: {self.model_name}")
        return self.model
    
    def upload_file(self, file_path: str, mime_type: str):
        """Upload file to Gemini API"""
        return genai.upload_file(file_path, mime_type=mime_type)
    
    def get_file(self, file_name: str):
        """Get file status from Gemini API"""
        return genai.get_file(file_name)
    
    def delete_file(self, file_name: str):
        """Delete file from Gemini API"""
        try:
            genai.delete_file(file_name)
            logger.info(f"Deleted file from Gemini: {file_name}")
        except Exception as e:
            logger.warning(f"Failed to delete file {file_name}: {e}")


# Singleton instance
_llm_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """Get the singleton LLM configuration instance"""
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig()
    return _llm_config
