import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file (search in backend directory)
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# Get API key from environment variable (REQUIRED)
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("[LLM] WARNING: GEMINI_API_KEY not set! Get one from https://aistudio.google.com/apikey")
    print(f"[LLM] Set it in {env_path} or as environment variable")

MODEL_NAME = "gemini-2.5-flash"


def llm_complete(prompt: str, timeout: int = 30) -> str:
    """
    TEA-safe LLM call:
    - No tools
    - No browsing
    - No memory
    - Deterministic output
    """
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Get one from https://aistudio.google.com/apikey")
    
    try:
        client = genai.Client(api_key=API_KEY)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                top_p=1.0,
                top_k=1,
                max_output_tokens=1024  # Increased for claim extraction
            )
        )

        if not response or not response.text:
            print("[LLM] Empty response from Gemini")
            return ""

        return response.text.strip()
    except Exception as e:
        print(f"[LLM] Error calling Gemini API: {e}")
        raise
