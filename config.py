import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB_NAME= os.getenv("MONGO_DB_NAME")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")