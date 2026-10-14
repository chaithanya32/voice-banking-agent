
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing from backend/.env")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=model,
    contents='Reply with exactly: VoxBank Gemini connection successful',
)

print(response.text)
