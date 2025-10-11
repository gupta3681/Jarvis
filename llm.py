"""
Centralized LLM configuration for Jarvis.
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# Configure LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "jarvis-assistant")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

def get_llm(temperature: float = 0.7, model: str = None):
    """
    Get configured LLM instance.
    
    Args:
        temperature: Temperature for the LLM (0.0 to 1.0)
        model: Model name to use. If None, uses env var or default.
    
    Returns:
        ChatOpenAI instance
    """
    # Get model from parameter, env var, or default
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Get API key from env
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file or export it."
        )
    
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key
    )


# Convenience instances
def get_conversation_llm():
    """Get LLM configured for conversation (higher temperature)."""
    return get_llm(temperature=0.7)


def get_tool_llm():
    """Get LLM configured for tool calling (lower temperature)."""
    return get_llm(temperature=0.3)
