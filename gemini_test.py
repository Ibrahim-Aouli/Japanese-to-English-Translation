from google import genai
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print(
    client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents="Ping"
    ).text
)
