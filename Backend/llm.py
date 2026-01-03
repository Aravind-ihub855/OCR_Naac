"""
LLM Configuration Module

Provides LLM initialization for semantic interpretation layer.
Uses Groq for fast inference.
"""

import os
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

logger = logging.getLogger("PDF_Agent.LLM")


def get_groq_llm():
    """
    Initialize Groq LLM for semantic interpretation.
    
    Uses low temperature (0.2) for consistent, factual outputs.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        logger.error("GROQ_API_KEY not found in environment")
        raise ValueError("GROQ_API_KEY not set in environment. Add it to .env file.")
    
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    logger.info(f"Initializing Groq LLM with model: {model}")
    
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model=model,
        temperature=0,  # Low temperature for consistent outputs
    )
    
    return llm
