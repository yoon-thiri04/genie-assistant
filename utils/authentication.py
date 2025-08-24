from fastapi.security import OAuth2PasswordBearer
from fastapi import Security, HTTPException
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
import os

from config import Config


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = os.getenv("SECRET_KEY")

def generate_jwt_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=60)
    to_encode.update(
        {"exp":expire}
    )

    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm="HS256")
    return encoded_jwt

def decode_jwt_token(token:str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms="HS256")
        if payload.get("exp") and payload["exp"] >= datetime.now().timestamp():
            return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
async def get_current_user(token: str = Security(oauth2_scheme)) -> dict:
    return decode_jwt_token(token)

from google import genai

# You can optionally store chat_id per user to maintain conversation context
user_chat_sessions = {}

def call_llm(user_id: str, prompt: str) -> str:
    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    # Reuse chat session if exists

    chat = client.chats.create(model="gemini-2.5-flash")
    response = chat.send_message(prompt)
    return response.text

