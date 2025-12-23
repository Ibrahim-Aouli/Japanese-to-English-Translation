import os
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="models/gemini-flash-latest",
    contents=(
        "Translate this Japanese video game dialogue into natural English. "
        "Keep it short. Do not explain.\n\n"
        "楽勝ッスね"
    )
)

print(response.text)
