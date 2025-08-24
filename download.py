from google import genai
from config import Config
client = genai.Client(api_key=Config.GEMINI_API_KEY)
chat = client.chats.create(model="gemini-2.5-flash")
response = chat.send_message("Hello!")
print(response.text)
