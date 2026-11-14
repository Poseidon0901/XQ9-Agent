import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_URL = os.getenv("OPENAI_API_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else "placeholder"
MODEL = os.getenv("MODEL")

CONSOLE_REFRESH_RATE = 100
