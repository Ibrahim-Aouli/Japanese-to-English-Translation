import os
import json
from openai import OpenAI

client = OpenAI()

MODEL = "gpt-4o-mini"  # fast + cheap + good for dialogue
BATCH_SIZE = 20        # safe size, adjust later

SYSTEM_PROMPT = (
    "You are translating Japanese video game dialogue.\n"
    "Rules:\n"
    "- Output ONLY natural English dialogue.\n"
    "- Keep it short.\n"
    "- Do NOT explain.\n"
    "- Do NOT add quotes.\n"
    "- Preserve placeholders like {TAGS} and [40+48?] exactly.\n"
    "- If the meaning is unclear, give the closest natural reaction."
)

def batch_translate(japanese_lines: list[str]) -> list[str]:
    """
    Takes a list of Japanese lines.
    Returns a list of English translations in the same order.
    """

    numbered_lines = "\n".join(
        f"{i+1}. {line}" for i, line in enumerate(japanese_lines)
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Japanese dialogue lines:\n{numbered_lines}\n\n"
                           f"Return the English lines in the same numbered order."
            }
        ],
        temperature=0.2,
    )

    text = response.choices[0].message.content.strip()

    # Parse numbered output
    translations = []
    for line in text.splitlines():
        if "." in line:
            translations.append(line.split(".", 1)[1].strip())

    return translations
