import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()



def get_groq_llm():
    """
    Initialize Groq LLM for semantic interpretation.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not set in environment.")
    
    model = os.getenv("GROQ_MODEL")
    
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model=model,
        temperature=0,  
    )
    
    return llm
