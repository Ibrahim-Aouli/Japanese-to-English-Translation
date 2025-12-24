import os
import re
import math

# ================= CONFIG =================
INPUT_DIR = "input_jp"
BATCH_SIZE = 20

# Gemini Flash pricing (USD per 1M tokens)
PRICE_INPUT = 0.35
PRICE_OUTPUT = 0.53

# Token estimation ratios (conservative)
JP_CHARS_PER_TOKEN = 1.5
EN_CHARS_PER_TOKEN = 4.0

# ================= REGEX =================
JAPANESE = re.compile(r"[ぁ-んァ-ン一-龯]")
PURE_TAG = re.compile(r"^\{[^}]+\}$")
SEPARATOR = re.compile(r"^-{5,}End--$")
MATH_ONLY = re.compile(r"^\d+\s*[\+\-\*/]\s*$")

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

def safe_read_lines(path):
    """Try UTF-8, then CP1252, then ignore errors."""
    for encoding in ("utf-8", "cp1252"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue

    # Last resort: ignore bad bytes
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()

# ================= SCAN FILES =================
total_lines = 0
total_chars_jp = 0
total_batches = 0
batch_count = 0

files = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".txt"))

for fname in files:
    path = os.path.join(INPUT_DIR, fname)
    lines = safe_read_lines(path)

    for line in lines:
        if should_translate(line.strip()):
            total_lines += 1
            total_chars_jp += len(line.strip())
            batch_count += 1

            if batch_count == BATCH_SIZE:
                total_batches += 1
                batch_count = 0

# Flush partial batch
if batch_count > 0:
    total_batches += 1

# ================= TOKEN ESTIMATION =================
input_tokens = math.ceil(total_chars_jp / JP_CHARS_PER_TOKEN)
estimated_en_chars = total_chars_jp * 1.1
output_tokens = math.ceil(estimated_en_chars / EN_CHARS_PER_TOKEN)

# ================= COST =================
cost_input = (input_tokens / 1_000_000) * PRICE_INPUT
cost_output = (output_tokens / 1_000_000) * PRICE_OUTPUT
total_cost = cost_input + cost_output

# ================= REPORT =================
print("\n📊 GEMINI COST ESTIMATE")
print("────────────────────────────")
print(f"Files scanned        : {len(files)}")
print(f"Translatable lines   : {total_lines}")
print(f"Batch size           : {BATCH_SIZE}")
print(f"Estimated requests   : {total_batches}")
print()
print(f"Estimated input tokens  : {input_tokens:,}")
print(f"Estimated output tokens : {output_tokens:,}")
print()
print(f"Input cost  (${PRICE_INPUT}/1M)  : ${cost_input:.4f}")
print(f"Output cost (${PRICE_OUTPUT}/1M) : ${cost_output:.4f}")
print("────────────────────────────")
print(f"💰 TOTAL ESTIMATED COST : ${total_cost:.4f}\n")

print("✅ Estimate complete (encoding-safe).")
print("⚠️ Conservative estimate — real cost will be LOWER due to caching.")
