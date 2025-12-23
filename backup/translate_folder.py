import os
import re
import argostranslate.package
import argostranslate.translate

FROM_LANG = "ja"
TO_LANG = "en"

INPUT_DIR = "input_jp"
OUTPUT_DIR = "output_en"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Ensure model installed
argostranslate.package.update_package_index()
installed = argostranslate.translate.get_installed_languages()
if not any(l.code == FROM_LANG for l in installed):
    pkg = next(
        p for p in argostranslate.package.get_available_packages()
        if p.from_code == FROM_LANG and p.to_code == TO_LANG
    )
    argostranslate.package.install_from_path(pkg.download())

langs = argostranslate.translate.get_installed_languages()
from_lang = next(l for l in langs if l.code == FROM_LANG)
to_lang = next(l for l in langs if l.code == TO_LANG)
translator = from_lang.get_translation(to_lang)

# Regex rules
SPEAKER_TAG = re.compile(r"^\{.*?\}$")
SEPARATOR = re.compile(r"^-{5,}End--$")

def should_translate(line):
    if not line.strip():
        return False
    if SPEAKER_TAG.match(line):
        return False
    if SEPARATOR.match(line):
        return False
    return True

for filename in os.listdir(INPUT_DIR):
    if not filename.lower().endswith(".txt"):
        continue

    in_path = os.path.join(INPUT_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    for line in lines:
        if should_translate(line.strip()):
            out_lines.append(translator.translate(line))
        else:
            out_lines.append(line)

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(out_lines)

    print(f"✅ Translated safely: {filename}")

print("\n🔥 Done. Structure preserved.")
