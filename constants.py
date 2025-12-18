import os
from dotenv import load_dotenv

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key or google_api_key == "YOUR_API_KEY_HERE":
    print("Warning: GOOGLE_API_KEY is not set in .env")
