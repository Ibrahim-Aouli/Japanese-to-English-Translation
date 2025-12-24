import os
import re
import json
from gemini_client import batch_translate

# ================= CONFIG =================
INPUT_DIR = "input_jp"
OUTPUT_DIR = "output_en"

CACHE_FILE = "translation_cache.json"
TEMPLATE_CACHE_FILE = "template_cache.json"
PROGRESS_FILE = "progress.json"

DEBUG = True
BATCH_SIZE = 20

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================= REGEX =================
JAPANESE = re.compile(r"[ぁ-んァ-ン一-龯]")
PURE_TAG = re.compile(r"^\{[^}]+\}$")
SEPARATOR = re.compile(r"^-{5,}End--$")
INLINE_TAG = re.compile(r"\{[^}]+\}")
MISSING_KANJI = re.compile(r"\[[^\]]+\]")
MATH_ONLY = re.compile(r"^\d+\s*[\+\-\*/]\s*$")

TAG_ANY = re.compile(r"\{[^}]+\}")
MISS_ANY = re.compile(r"\[[^\]]+\]")
WS_ANY = re.compile(r"\s+")

# ================= LOAD JSON =================
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

CACHE = load_json(CACHE_FILE, {})
TEMPLATE_CACHE = load_json(TEMPLATE_CACHE_FILE, {})
PROGRESS = load_json(PROGRESS_FILE, {"file_index": 0})

# ================= DEBUG =================
def debug(msg):
    if DEBUG:
        print(msg)

# ================= FILTER =================
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

# ================= PLACEHOLDERS =================
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

# ================= MAIN =================
files = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".txt"))
total_files = len(files)
start_index = PROGRESS.get("file_index", 0)

for file_idx in range(start_index, total_files):
    fname = files[file_idx]
    debug(f"\n📄 Processing {file_idx + 1}/{total_files}: {fname}")

    in_path = os.path.join(INPUT_DIR, fname)
    out_path = os.path.join(OUTPUT_DIR, fname)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = list(lines)  # <-- preserve structure
    batch = []
    batch_meta = []

    for ln, line in enumerate(lines):
        stripped = line.strip()

        if stripped in CACHE:
            out_lines[ln] = CACHE[stripped] + "\n"
            continue

        if not should_translate(stripped):
            continue

        safe, placeholders = protect(stripped)
        batch.append(safe)
        batch_meta.append((ln, stripped, placeholders))

        if len(batch) == BATCH_SIZE:
            translations = batch_translate(batch)

            for (idx, orig, ph), trans in zip(batch_meta, translations):
                restored = restore(trans, ph)
                CACHE[orig] = restored
                out_lines[idx] = restored + "\n"
                debug(f"  [L{idx+1}] 🤖 {orig} → {restored}")

            batch.clear()
            batch_meta.clear()

    # Flush remainder
    if batch:
        translations = batch_translate(batch)
        for (idx, orig, ph), trans in zip(batch_meta, translations):
            restored = restore(trans, ph)
            CACHE[orig] = restored
            out_lines[idx] = restored + "\n"
            debug(f"  [L{idx+1}] 🤖 {orig} → {restored}")

    # Write output
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)

    PROGRESS["file_index"] = file_idx + 1
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(PROGRESS, f, indent=2)

    debug(f"✅ Finished {fname}")

print("\n🔥 All files processed (layout preserved).")
