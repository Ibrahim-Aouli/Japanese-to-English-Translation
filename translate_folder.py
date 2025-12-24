import os
import re
import json
import time
from gemini_client import batch_translate

# ================= CONFIG =================
INPUT_DIR = "input_jp"
OUTPUT_DIR = "output_en"
CACHE_FILE = "translation_cache.json"
PROGRESS_FILE = "progress.json"

DEBUG = True
BATCH_SIZE = 30

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= REGEX =================
JAPANESE = re.compile(r"[ぁ-んァ-ン一-龯]")
PURE_TAG = re.compile(r"^\{[^}]+\}$")
SEPARATOR = re.compile(r"^-{5,}End--$")
INLINE_TAG = re.compile(r"\{[^}]+\}")
MISSING_KANJI = re.compile(r"\[[^\]]+\]")
MATH_ONLY = re.compile(r"^\d+\s*[\+\-\*/]\s*\d+$")

# ================= CACHE =================
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
else:
    CACHE = {}

# ================= PROGRESS =================
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        PROGRESS = json.load(f)
else:
    PROGRESS = {"file_index": 0}

# ================= DEBUG =================
def debug(msg):
    if DEBUG:
        print(msg)

# ================= HELPERS =================
def should_translate(line: str) -> bool:
    if not line.strip():
        return False
    if PURE_TAG.match(line):
        return False
    if SEPARATOR.match(line):
        return False
    if MATH_ONLY.match(line):
        return False
    return bool(JAPANESE.search(line))

def protect(line: str):
    placeholders = {}

    def repl(match):
        key = f"__P{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    line = INLINE_TAG.sub(repl, line)
    line = MISSING_KANJI.sub(repl, line)
    return line, placeholders

def restore(line: str, placeholders: dict):
    for k, v in placeholders.items():
        line = line.replace(k, v)
    return line

# ================= SAFE WRAPPER =================
def safe_batch_translate(batch):
    """
    Batch is a list of protected JP strings.
    Returns list of translated EN strings in same order.
    """
    while True:
        try:
            numbered_input = "\n".join(
                f"{i+1}. {line}" for i, line in enumerate(batch)
            )

            prompt = (
                "Translate the following Japanese lines into natural but faithful English.\n"
                "Preserve tone, ellipses, and intent.\n"
                "Return ONLY numbered translations matching the input numbers.\n\n"
                f"{numbered_input}"
            )

            response = batch_translate([prompt])[0]

            # Parse numbered output
            results = {}
            for line in response.splitlines():
                if "." in line:
                    num, text = line.split(".", 1)
                    if num.strip().isdigit():
                        results[int(num.strip())] = text.strip()

            translations = [
                results.get(i+1, batch[i]) for i in range(len(batch))
            ]

            return translations

        except Exception as e:
            msg = str(e)
            wait_seconds = 60

            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                if "retryDelay" in msg:
                    digits = "".join(c for c in msg if c.isdigit())
                    if digits:
                        wait_seconds = int(digits) + 1

                debug(f"⏳ Rate-limited — waiting {wait_seconds}s")
                time.sleep(wait_seconds)
                continue

            raise

# ================= MAIN LOOP =================
files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")])
total_files = len(files)

start_index = PROGRESS.get("file_index", 0)

for file_idx in range(start_index, total_files):
    fname = files[file_idx]
    debug(f"\n📄 Processing file {file_idx+1}/{total_files}: {fname}")

    in_path = os.path.join(INPUT_DIR, fname)
    out_path = os.path.join(OUTPUT_DIR, fname)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    batch = []
    batch_meta = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped in CACHE:
            out_lines.append(CACHE[stripped] + "\n")
            continue

        if not should_translate(stripped):
            out_lines.append(line)
            continue

        safe, placeholders = protect(stripped)
        batch.append(safe)
        batch_meta.append((idx, stripped, placeholders))

        if len(batch) == BATCH_SIZE:
            translations = safe_batch_translate(batch)

            for (ln, original, ph), translated in zip(batch_meta, translations):
                restored = restore(translated, ph)
                CACHE[original] = restored
                out_lines.append(restored + "\n")
                debug(f"  [L{ln}] 🤖 {original} → {restored}")

            batch.clear()
            batch_meta.clear()

    # Flush remainder
    if batch:
        translations = safe_batch_translate(batch)
        for (ln, original, ph), translated in zip(batch_meta, translations):
            restored = restore(translated, ph)
            CACHE[original] = restored
            out_lines.append(restored + "\n")
            debug(f"  [L{ln}] 🤖 {original} → {restored}")

    # Write outputs
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)

    PROGRESS["file_index"] = file_idx + 1
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(PROGRESS, f, indent=2)

    debug(f"✅ Finished file {file_idx+1}/{total_files}")

print("\n🔥 All files processed (or safely paused).")
