import os
import numpy as np
from google import genai

# TODO: Move this to an environment variable for security
API_KEY = "AIzaSyCyd3vL04o4HaSfsrtSOaKeCWwtB8lvvlM"

client = genai.Client(api_key=API_KEY)


def embed_text(text: str) -> list:
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text
    )
    # The new SDK returns an object with an 'embeddings' attribute,
    # which is a list of embedding objects. We take the first one's values.
    return result.embeddings[0].values


def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
