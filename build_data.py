import os
import csv
import json
import re
import math  # Added for KL Divergence calculation

# --- CONFIGURATION ---
INPUT_ROOT = "csv_files"  # The root of your experiment outputs
OUTPUT_DIR = "data"       # Where the website reads from

# Regex to clean up model names from folder paths
def clean_model_name(folder_name):
    name = folder_name.replace("las-", "")
    name = re.sub(r'-\d{4}-\d{2}-\d{2}.*', '', name)
    return name

def process_directory():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inventory = []
    
    print(f"📂 Scanning '{INPUT_ROOT}' for experimental results...")

    for root, dirs, files in os.walk(INPUT_ROOT):
        csv_files = [f for f in files if f.startswith("las_word_") and f.endswith(".csv")]
        
        for csv_file in csv_files:
            lang = csv_file.replace("las_word_", "").replace(".csv", "")
            summary_file = f"summary_{lang}.json"
            
            if summary_file not in files:
                continue

            # --- 1. EXTRACT METADATA ---
            path_parts = os.path.normpath(root).split(os.sep)
            try:
                try:
                    root_idx = path_parts.index(os.path.basename(INPUT_ROOT))
                    register = path_parts[root_idx + 1]
                    model_raw = path_parts[root_idx + 2]
                except (ValueError, IndexError):
                    continue
                model_clean = clean_model_name(model_raw)
            except Exception as e:
                continue

            # --- 2. READ SUMMARY JSON ---
            summary_path = os.path.join(root, summary_file)
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    k_window = summary.get("params", {}).get("windowk", 40)
                    n_pairs = 0
                    if "pairing_qc" in summary:
                        n_pairs = summary["pairing_qc"].get("model_lines", 0)
                    if n_pairs == 0 and "qc" in summary:
                        n_pairs = summary["qc"].get("n_pairs", 0)
                    
                    # ---------------------------------------------------------
                    # CRITICAL: Calculate Total Tokens for Normalization
                    # We assume paired data, so Total Human Tokens ≈ Total AI Tokens
                    # ---------------------------------------------------------
                    total_tokens = n_pairs * k_window

            except Exception as e:
                print(f"❌ Error reading JSON {summary_path}: {e}")
                total_tokens = 0

            # --- 3. READ CSV DATA & CALCULATE METRICS ---
            csv_path = os.path.join(root, csv_file)
            rows = []
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        
                        # 1. Get raw counts (for OPM)
                        raw_count_ai = float(row['c_M']) if row.get('c_M') else 0.0
                        raw_count_human = float(row['c_H']) if row.get('c_H') else 0.0
                        
                        # 2. Get Prevalence (ell) for Distinctiveness
                        #    LAS score is based on these document frequencies.
                        ell_m = float(row.get('ell_M', 0))
                        ell_h = float(row.get('ell_H', 0))

                        # 3. Calculate OPM (Occurrences Per Million)
                        if total_tokens > 0:
                            opm_ai = (raw_count_ai / total_tokens) * 1_000_000
                            opm_human = (raw_count_human / total_tokens) * 1_000_000
                        else:
                            opm_ai = 0.0
                            opm_human = 0.0

                        # 4. Calculate Ratio (Multiplier)
                        if opm_human > 0:
                            ratio = opm_ai / opm_human
                        else:
                            ratio = None 

                        # 5. Calculate Pointwise KL Divergence (Distinctiveness)
                        #    Formula: P(M) * log(P(M) / P(H))
                        #    We use ell (prevalence) as P.
                        epsilon = 1e-9 # Small value to prevent division by zero
                        
                        if ell_m > 0 and ell_h > 0:
                            distinctiveness = ell_m * math.log(ell_m / ell_h)
                        elif ell_m > 0 and ell_h == 0:
                            # Use epsilon for ell_h to avoid infinite score, 
                            # or just use a high proxy based on ell_m
                            distinctiveness = ell_m * math.log(ell_m / epsilon)
                        else:
                            distinctiveness = 0.0

                        clean_row = {
                            "rank": int(row['rank_LAS']),
                            "word": row['form'],
                            "upos": row.get('upos', 'UNK'), 
                            "score": round(float(row['LAS']), 4),
                            
                            # METRICS
                            "ai_freq": round(opm_ai, 2),
                            "human_freq": round(opm_human, 2),
                            "ratio": round(ratio, 1) if ratio is not None else None,
                            "distinctiveness": round(distinctiveness, 5)
                        }
                        rows.append(clean_row)
                
                rows.sort(key=lambda x: x['rank'])
                
                # --- 4. SAVE OUTPUT ---
                output_filename = f"{lang}_{register}_{model_clean}.json"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                
                final_data = {
                    "meta": {
                        "n_pairs": n_pairs,
                        "k_window": k_window,
                        "total_tokens": total_tokens,
                        "source_path": root
                    },
                    "data": rows
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f)
                
                inventory.append({
                    "lang": lang,
                    "register": register,
                    "model": model_clean
                })
                print(f"✅ Generated: {lang.upper()} | {register} | {model_clean} (N={n_pairs})")

            except Exception as e:
                print(f"❌ Error processing CSV {csv_path}: {e}")

    # --- 5. INDEX ---
    with open(os.path.join(OUTPUT_DIR, "index.json"), 'w', encoding='utf-8') as f:
        json.dump(inventory, f)
    
    print(f"\n🎉 Done! Created {len(inventory)} datasets.")

if __name__ == "__main__":
    process_directory()
