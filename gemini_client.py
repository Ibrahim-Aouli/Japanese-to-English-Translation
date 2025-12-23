import os
import time
from google import genai
from google.genai.errors import ClientError

MODEL = "models/gemini-flash-latest"
BASE_SLEEP = 2

PROMPT_FILE = "system_prompt.txt"

# ---------- LOAD SYSTEM PROMPT ----------
if not os.path.exists(PROMPT_FILE):
    raise FileNotFoundError(
        f"Missing {PROMPT_FILE}. Create it to define translation behavior."
    )

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

if not SYSTEM_PROMPT:
    raise ValueError("system_prompt.txt is empty.")

# ---------- GEMINI CLIENT ----------
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def extract_retry_seconds(error: ClientError) -> int:
    try:
        error_dict = error.error or {}
        details = error_dict.get("details", [])
        for d in details:
            if isinstance(d, dict) and "retryDelay" in d:
                delay = d["retryDelay"]
                if delay.endswith("s"):
                    return int(float(delay[:-1])) + 1
    except Exception:
        pass
    return 60


def is_quota_error(error: ClientError) -> bool:
    try:
        return error.error.get("status") == "RESOURCE_EXHAUSTED"
    except Exception:
        return False


def batch_translate(lines: list[str]) -> list[str]:
    """
    Translate a batch of lines.
    This function NEVER raises on quota exhaustion.
    It will wait and retry indefinitely.
    """
    while True:
        try:
            prompt = SYSTEM_PROMPT + "\n\nJapanese lines:\n"
            for i, line in enumerate(lines, 1):
                prompt += f"{i}. {line}\n"
            prompt += "\nReturn the English lines in the same numbered order."

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            text = (response.text or "").strip()
            results = []

            for line in text.splitlines():
                if "." in line:
                    results.append(line.split(".", 1)[1].strip())

            while len(results) < len(lines):
                results.append(lines[len(results)])

            time.sleep(BASE_SLEEP)
            return results

        except ClientError as e:
            # Safely inspect Gemini error payload
            error_data = getattr(e, "error", {}) or {}
            status = error_data.get("status")

            if status == "RESOURCE_EXHAUSTED":
                # Try to extract retryDelay
                retry_seconds = 60
                for detail in error_data.get("details", []):
                    if isinstance(detail, dict) and "retryDelay" in detail:
                        delay = detail["retryDelay"]
                        if delay.endswith("s"):
                            retry_seconds = int(float(delay[:-1])) + 1

                print(f"⏳ Gemini quota exhausted — waiting {retry_seconds}s and retrying…")
                time.sleep(retry_seconds)
                continue

            # Any other ClientError is real and should stop execution
            raise