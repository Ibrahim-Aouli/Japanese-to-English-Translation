import os
import re
import json
from typing import List

# ======================
# CONFIG
# ======================
INPUT_DIR = "input_jp"
OUTPUT_DIR = "output_en"
CACHE_FILE = "translation_cache.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ======================
# REGEX DEFINITIONS
# ======================
JAPANESE_RE = re.compile(r"[ぁ-んァ-ン一-龯]")
PURE_TAG_RE = re.compile(r"^\{[^}]+\}$")
SEPARATOR_RE = re.compile(r"^-{5,}End--$")
INLINE_TAG_RE = re.compile(r"\{[^}]+\}")
MISSING_KANJI_RE = re.compile(r"\[[^\]]+\]")
MATH_RE = re.compile(r"^\d+\s*[\+\-\*/]\s*\d+$")

# ======================
# LOAD CACHE
# ======================
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

# ======================
# AI CALL (REPLACE THIS)
# ======================
def ask_ai(japanese_text: str) -> str:
    """
    Replace this function with your AI model call.
    The AI should return ONLY the English line.
    """
    # ---- PLACEHOLDER ----
    # Example expected return:
    # "That was easy."
    return f"[AI_TRANSLATED] {japanese_text}"

# ======================
# UTILS
# ======================
def should_translate(line: str) -> bool:
    if not line.strip():
        return False
    if PURE_TAG_RE.match(line):
        return False
    if SEPARATOR_RE.match(line):
        return False
    if MATH_RE.match(line):
        return False
    return bool(JAPANESE_RE.search(line))

def protect_elements(line: str):
    """
    Temporarily replace protected elements with placeholders.
    """
    placeholders = {}

    def repl(match):
        key = f"__P{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    line = INLINE_TAG_RE.sub(repl, line)
    line = MISSING_KANJI_RE.sub(repl, line)

    return line, placeholders

def restore_elements(line: str, placeholders: dict):
    for k, v in placeholders.items():
        line = line.replace(k, v)
    return line

# ======================
# PROCESS FILES
# ======================
for filename in os.listdir(INPUT_DIR):
    if not filename.lower().endswith(".txt"):
        continue

    in_path = os.path.join(INPUT_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        if not should_translate(stripped):
            output_lines.append(line)
            continue

        # Cache hit
        if stripped in CACHE:
            output_lines.append(CACHE[stripped] + "\n")
            continue

        # Protect tags and placeholders
        protected_line, placeholders = protect_elements(stripped)

        # Ask AI
        translation = ask_ai(protected_line).strip()

        # If AI fails or returns nothing → keep original JP
        if not translation or translation == protected_line:
            output_lines.append(line)
            continue

        # Restore protected parts
        translation = restore_elements(translation, placeholders)

        CACHE[stripped] = translation
        output_lines.append(translation + "\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"✅ Processed: {filename}")

# ======================
# SAVE CACHE
# ======================
with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(CACHE, f, ensure_ascii=False, indent=2)

print("\n🔥 All files processed safely.")
