# test_openai.py
from openai import OpenAI
from config import Config
# Replace with your actual OpenAI API key
api_key = "YOUR_OPENAI_API_KEY"

# Initialize OpenAI client
client = OpenAI(api_key=Config.OPENAI_API_KEY)

# Create a chat completion
try:
    response = client.chat.completions.create(
        model="gpt-4.1", 
        messages=[
            {"role": "user", "content": "Hello! How are you today?"}
        ]
    )

    
    reply = response.choices[0].message.content
    print("Assistant:", reply)

except Exception as e:
    print("Error calling OpenAI:", e)
