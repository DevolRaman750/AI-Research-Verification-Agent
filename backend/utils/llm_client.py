import os
from google import genai
from google.genai import types

# TODO: Move this to an environment variable for security
API_KEY = "AIzaSyCyd3vL04o4HaSfsrtSOaKeCWwtB8lvvlM"

MODEL_NAME = "gemini-2.5-flash"


def llm_complete(prompt: str) -> str:
    """
    TEA-safe LLM call:
    - No tools
    - No browsing
    - No memory
    - Deterministic output
    """
    client = genai.Client(api_key=API_KEY)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            top_p=1.0,
            top_k=1,
            max_output_tokens=512
        )
    )

    if not response or not response.text:
        return ""

    return response.text.strip()
