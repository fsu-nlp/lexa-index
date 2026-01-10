import os
import json
import random

# --- CONFIGURATION ---
OUTPUT_DIR = "data"
LANGS = ["en", "de"]
REGISTERS = ["news", "wikipedia", "science"]
MODELS = ["gpt-4", "gpt-5.2", "claude-3"]

# Ensure directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Generate Index (so the dropdowns know what options exist)
index = {
    "languages": LANGS,
    "registers": REGISTERS,
    "models": MODELS
}
with open(f"{OUTPUT_DIR}/index.json", "w") as f:
    json.dump(index, f)

# Generate Dummy Data Files
# File pattern: data/{lang}_{register}_{model}.json
for lang in LANGS:
    for reg in REGISTERS:
        for mod in MODELS:
            rows = []
            # Make some dummy words
            vocab = ["delve", "crucial", "tapestry", "landscape", "foster", "underscore", "realm", "nuance"]
            
            for i, word in enumerate(vocab):
                # Randomize scores based on "model" to show difference
                bias = 2.0 if "gpt" in mod else 0.5
                score = round(random.uniform(0.1, 1.0) * bias, 3)
                
                rows.append({
                    "rank": i + 1,
                    "word": word,
                    "score": score,
                    "human_freq": round(random.uniform(0.001, 0.005), 5),
                    "ai_freq": round(random.uniform(0.005, 0.01), 5)
                })
            
            # Sort by score descending
            rows.sort(key=lambda x: x['score'], reverse=True)

            filename = f"{OUTPUT_DIR}/{lang}_{reg}_{mod}.json"
            with open(filename, "w") as f:
                json.dump({"meta": {"k": 50}, "data": rows}, f)

print(f"✅ Generated {len(LANGS)*len(REGISTERS)*len(MODELS)} JSON files in '/{OUTPUT_DIR}'")
