import os
import time
import random
import re
from google import genai
from google.genai.errors import ClientError

# ================= CONFIG =================
MODEL = "models/gemini-2.5-flash"
BASE_SLEEP = 1.5
MAX_SLEEP = 4.0

PROMPT_FILE = "system_prompt.txt"

LINE_RE = re.compile(r"^\s*(\d+)[\.\)\-:]\s*(.+)$")

# ================= LOAD SYSTEM PROMPT =================
if not os.path.exists(PROMPT_FILE):
    raise FileNotFoundError(
        f"Missing {PROMPT_FILE}. Create it to define translation behavior."
    )

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

if not SYSTEM_PROMPT:
    raise ValueError("system_prompt.txt is empty.")

# ================= GEMINI CLIENT =================
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


# ================= UTIL =================
def _sleep_jitter():
    time.sleep(random.uniform(BASE_SLEEP, MAX_SLEEP))


def _extract_retry_seconds(error: ClientError) -> int:
    try:
        error_data = getattr(error, "error", {}) or {}
        for detail in error_data.get("details", []):
            if isinstance(detail, dict) and "retryDelay" in detail:
                delay = detail["retryDelay"]
                if delay.endswith("s"):
                    return max(5, min(int(float(delay[:-1])) + 1, 300))
    except Exception:
        pass
    return 60


# ================= MAIN =================
def batch_translate(lines: list[str]) -> list[str]:
    """
    Translate a batch of lines.
    NEVER raises on quota exhaustion.
    Guarantees output length == input length.
    """
    assert lines, "batch_translate called with empty list"

    while True:
        try:
            prompt = SYSTEM_PROMPT + "\n\nJapanese lines:\n"
            for i, line in enumerate(lines, 1):
                prompt += f"{i}. {line}\n"
            prompt += "\nReturn ONLY the numbered English translations."

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            text = (response.text or "").strip()

            results = {}
            for raw in text.splitlines():
                m = LINE_RE.match(raw)
                if m:
                    idx = int(m.group(1))
                    results[idx] = m.group(2).strip()

            # Build output safely
            output = []
            for i in range(1, len(lines) + 1):
                if i in results and results[i]:
                    output.append(results[i])
                else:
                    # Fallback: preserve original JP to avoid corruption
                    output.append(lines[i - 1])

            _sleep_jitter()
            return output

        except ClientError as e:
            error_data = getattr(e, "error", {}) or {}
            status = error_data.get("status")

            if status == "RESOURCE_EXHAUSTED":
                wait = _extract_retry_seconds(e)
                print(f"⏳ Gemini quota exhausted — waiting {wait}s…")
                time.sleep(wait)
                continue

            # Any other error is real
            raise
