#!/usr/bin/env python3
import os
import csv
import json
import re
import math
import argparse
import html as _html
import datetime

# --- CONFIGURATION DEFAULTS ---
DEFAULT_INPUT_ROOT = "csv_files"  # The root of your experiment outputs
DEFAULT_OUTPUT_DIR = "data"       # Where the website reads from

# Guardrail: words must appear at least this many times in AI text
# to be considered for "High Impact" ranking.
DEFAULT_MIN_AI_COUNT_FOR_IMPACT = 20

# Jeffreys smoothing for ratios (prevents division by zero and "NEW" masking spikes)
DEFAULT_RATIO_SMOOTH = 0.5


def clean_model_name(folder_name: str) -> str:
    """Clean up model names from folder paths."""
    name = folder_name.replace("las-", "")
    name = re.sub(r"-\d{4}-\d{2}-\d{2}.*", "", name)
    return name


# Unicode-aware "has at least one alphanumeric char" check.
# Using str.isalnum() keeps this robust for non-Latin scripts.
def has_any_alnum(token: str) -> bool:
    if token is None:
        return False
    token = str(token).strip()
    if not token:
        return False
    return any(ch.isalnum() for ch in token)


def process_directory(
    input_root: str,
    output_dir: str,
    min_ai_count_for_impact: int,
    mode: str,
    ratio_smooth: float,
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    inventory = []

    print(f"📂 Scanning '{input_root}' for experimental results...")
    print(
        f"🧰 Output mode: {mode} (min_ai_count_for_impact={min_ai_count_for_impact}, ratio_smooth={ratio_smooth})"
    )

    for root, _, files in os.walk(input_root):
        csv_files = [f for f in files if f.startswith("las_word_") and f.endswith(".csv")]

        for csv_file in csv_files:
            lang = csv_file.replace("las_word_", "").replace(".csv", "")
            summary_file = f"summary_{lang}.json"

            if summary_file not in files:
                continue

            # --- 1) EXTRACT METADATA ---
            path_parts = os.path.normpath(root).split(os.sep)
            try:
                try:
                    root_idx = path_parts.index(os.path.basename(input_root))
                    register = path_parts[root_idx + 1]
                    model_raw = path_parts[root_idx + 2]
                except (ValueError, IndexError):
                    continue
                model_clean = clean_model_name(model_raw)
            except Exception:
                continue

            # --- 2) READ SUMMARY JSON ---
            summary_path = os.path.join(root, summary_file)
            k_window = 40
            n_pairs = 0
            total_tokens = 0
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)
                    k_window = summary.get("params", {}).get("windowk", 40)

                    if "pairing_qc" in summary:
                        n_pairs = summary["pairing_qc"].get("model_lines", 0)
                    if n_pairs == 0 and "qc" in summary:
                        n_pairs = summary["qc"].get("n_pairs", 0)

                    # We assume paired data, so Total Human Tokens ≈ Total AI Tokens
                    total_tokens = n_pairs * k_window if (n_pairs and k_window) else 0
            except Exception as e:
                print(f"❌ Error reading JSON {summary_path}: {e}")

            # --- 3) READ CSV DATA & CALCULATE METRICS ---
            csv_path = os.path.join(root, csv_file)
            rows = []
            n_rows_csv = 0
            n_rows_written = 0
            n_rows_dropped_non_alnum = 0

            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)

                    for row in reader:
                        n_rows_csv += 1

                        # --- NEW: Drop tokens that are purely "special characters" ---
                        form = row.get("form", "")
                        if not has_any_alnum(form):
                            n_rows_dropped_non_alnum += 1
                            continue

                        # Raw counts (critical for LPR + smoothed ratio)
                        raw_count_ai = float(row["c_M"]) if row.get("c_M") else 0.0
                        raw_count_human = float(row["c_H"]) if row.get("c_H") else 0.0

                        # --- SPACE-SAVING FILTER (optional) ---
                        # In compact mode, drop rows where AI count is zero.
                        # (And also drop rows where both are zero.)
                        if mode == "compact":
                            if raw_count_ai == 0.0:
                                continue
                            if raw_count_ai == 0.0 and raw_count_human == 0.0:
                                continue

                        # OPM (Occurrences Per Million) for display
                        if total_tokens > 0:
                            opm_ai = (raw_count_ai / total_tokens) * 1_000_000
                            opm_human = (raw_count_human / total_tokens) * 1_000_000
                        else:
                            opm_ai = 0.0
                            opm_human = 0.0

                        # Smoothed ratio using Jeffreys smoothing on counts.
                        ratio = (raw_count_ai + ratio_smooth) / (raw_count_human + ratio_smooth)

                        # Log Prevalence Ratio (Impact)
                        # Log2( (AI + 1) / (Human + 1) )
                        if raw_count_ai >= min_ai_count_for_impact:
                            smoothed_ai = raw_count_ai + 1.0
                            smoothed_human = raw_count_human + 1.0
                            lpr = math.log2(smoothed_ai / smoothed_human)
                        else:
                            lpr = 0.0

                        las = float(row.get("LAS", 0.0)) if row.get("LAS") else 0.0

                        # Store row (compact keys; ranks assigned later)
                        # Keys:
                        #   w      word (surface form)
                        #   u      UPOS
                        #   las    volume (LAS)
                        #   lpr    impact (LPR)
                        #   a      AI OPM
                        #   h      Human OPM
                        #   r      ratio (smoothed)
                        #   rk_las rank by LAS (desc)
                        #   rk_lpr rank by LPR (desc)
                        rows.append({
                            "w": str(form).strip(),
                            "u": row.get("upos", "UNK"),
                            "las": las,
                            "lpr": lpr,
                            "a": round(opm_ai, 2),
                            "h": round(opm_human, 2),
                            "r": round(ratio, 1),
                            "rk_las": 0,
                            "rk_lpr": 0,
                        })

                # --- 4) MULTI-PASS SORTING & RANKING ---
                # A) LAS ranks (desc)
                rows.sort(key=lambda x: x["las"], reverse=True)
                for i, r in enumerate(rows):
                    r["rk_las"] = i + 1

                # B) LPR ranks (desc)
                rows.sort(key=lambda x: x["lpr"], reverse=True)
                for i, r in enumerate(rows):
                    r["rk_lpr"] = i + 1

                # C) Final sort by LAS rank (default view) & rounding
                rows.sort(key=lambda x: x["rk_las"])
                for r in rows:
                    r["las"] = round(r["las"], 4)
                    r["lpr"] = round(r["lpr"], 4)

                n_rows_written = len(rows)

                # --- 5) SAVE OUTPUT ---
                output_filename = f"{lang}_{register}_{model_clean}.json"
                output_path = os.path.join(output_dir, output_filename)

                # Compact meta keys too (optional, but helps):
                #   np   n_pairs
                #   kw   k_window
                #   tt   total_tokens
                #   src  source_path
                #   md   mode
                #   min  min_ai_count_for_impact
                #   sm   ratio_smooth
                #   n0   n_rows_csv
                #   n1   n_rows_written
                #   nx   rows dropped for non-alnum
                final_data = {
                    "meta": {
                        "np": n_pairs,
                        "kw": k_window,
                        "tt": total_tokens,
                        "src": root,
                        "md": mode,
                        "min": min_ai_count_for_impact,
                        "sm": ratio_smooth,
                        "n0": n_rows_csv,
                        "n1": n_rows_written,
                        "nx": n_rows_dropped_non_alnum,
                    },
                    "data": rows,
                }

                # separators removes whitespace; ensure_ascii=False keeps non-ASCII chars readable
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, ensure_ascii=False, separators=(",", ":"))

                inventory.append({
                    "lang": lang,
                    "register": register,
                    "model": model_clean
                })

                print(
                    f"✅ Generated: {lang.upper()} | {register} | {model_clean} "
                    f"(N={n_pairs}, rows={n_rows_written}/{n_rows_csv}, dropped_non_alnum={n_rows_dropped_non_alnum})"
                )

            except Exception as e:
                print(f"❌ Error processing CSV {csv_path}: {e}")

    # --- 6) INDEX ---
    with open(os.path.join(output_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\n🎉 Done! Created {len(inventory)} datasets.")


# --- Per-language labels for words.html (item 7a: a static, crawler-readable page). ---
# Each entry: (English name, autonym/endonym, native query phrase for "words AI overuses").
# NOTE: the native phrasings are a DRAFT pending linguistic review before publish.
LANG_INFO = {
    "en": ("English", "English", "Words AI overuses"),
    "nl": ("Dutch", "Nederlands", "Woorden die AI te vaak gebruikt"),
    "de": ("German", "Deutsch", "Wörter, die KI zu oft benutzt"),
    "fr": ("French", "Français", "Mots que l'IA surutilise"),
    "es": ("Spanish", "Español", "Palabras que la IA usa en exceso"),
    "it": ("Italian", "Italiano", "Parole che l'IA usa troppo"),
    "pt": ("Portuguese", "Português", "Palavras que a IA usa em excesso"),
    "ru": ("Russian", "Русский", "Слова, которые ИИ использует слишком часто"),
    "uk": ("Ukrainian", "Українська", "Слова, які ШІ вживає надто часто"),
    "pl": ("Polish", "Polski", "Słowa nadużywane przez AI"),
    "cs": ("Czech", "Čeština", "Slova nadužívaná umělou inteligencí"),
    "bg": ("Bulgarian", "Български", "Думи, които ИИ използва прекомерно"),
    "el": ("Greek", "Ελληνικά", "Λέξεις που υπερχρησιμοποιεί η ΤΝ"),
    "ro": ("Romanian", "Română", "Cuvinte suprautilizate de IA"),
    "hr": ("Croatian", "Hrvatski", "Riječi koje AI prečesto koristi"),
    "sr": ("Serbian", "Српски", "Речи које вештачка интелигенција прекомерно користи"),
    "lt": ("Lithuanian", "Lietuvių", "Žodžiai, kuriuos DI vartoja per dažnai"),
    "lv": ("Latvian", "Latviešu", "Vārdi, ko MI lieto pārāk bieži"),
    "et": ("Estonian", "Eesti", "Sõnad, mida tehisintellekt liialt kasutab"),
    "fi": ("Finnish", "Suomi", "Sanat, joita tekoäly käyttää liikaa"),
    "is": ("Icelandic", "Íslenska", "Orð sem gervigreind ofnotar"),
    "tr": ("Turkish", "Türkçe", "Yapay zekânın aşırı kullandığı kelimeler"),
    "ar": ("Arabic", "العربية", "الكلمات التي يفرط الذكاء الاصطناعي في استخدامها"),
    "fa": ("Persian", "فارسی", "واژه‌هایی که هوش مصنوعی زیاد به کار می‌برد"),
    "hi": ("Hindi", "हिन्दी", "शब्द जो AI बहुत ज़्यादा इस्तेमाल करता है"),
    "mr": ("Marathi", "मराठी", "AI जास्त वापरत असलेले शब्द"),
    "ta": ("Tamil", "தமிழ்", "AI அதிகம் பயன்படுத்தும் சொற்கள்"),
    "ja": ("Japanese", "日本語", "AIが多用する言葉"),
    "ko": ("Korean", "한국어", "AI가 자주 쓰는 단어"),
    "zh": ("Chinese", "中文", "AI 过度使用的词语"),
    "id": ("Indonesian", "Bahasa Indonesia", "Kata-kata yang terlalu sering dipakai AI"),
    "kk": ("Kazakh", "Қазақша", "Жасанды интеллект жиі қолданатын сөздер"),
    "ky": ("Kyrgyz", "Кыргызча", "Жасалма интеллект көп колдонгон сөздөр"),
    "af": ("Afrikaans", "Afrikaans", "Woorde wat KI te veel gebruik"),
}

WORDS_MODEL_LABEL = "GPT-4.1 mini"
WORDS_TOP_N = 20

_WORDS_CSS = (
    "*{box-sizing:border-box}"
    "body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;margin:0;line-height:1.55;background:#fff}"
    ".wrap{max-width:920px;margin:0 auto;padding:0 20px}"
    "header{background:#f8fafc;border-bottom:1px solid #e2e8f0;padding:26px 0 30px}"
    "header nav,footer{font-size:14px;color:#475569}"
    "header nav a,footer a,.toc a{color:#1e3a8a;text-decoration:none}"
    "header nav a:hover,footer a:hover,.toc a:hover{text-decoration:underline}"
    "h1{font-size:30px;margin:14px 0 10px;color:#1e3a8a}"
    ".intro{color:#475569;font-size:16px;max-width:780px;margin:0}"
    ".note{color:#94a3b8;font-size:13px;max-width:780px;margin:10px 0 0}"
    ".note a{color:#64748b}"
    ".toc{padding:16px 0;border-bottom:1px solid #e2e8f0;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:14px}"
    "main{padding:8px 0 40px}"
    "section{padding:20px 0;border-bottom:1px solid #e2e8f0}"
    "section h2{font-size:20px;margin:0 0 2px;color:#0f172a}"
    "section h2 .en{color:#475569;font-weight:400;font-size:15px;margin-left:8px}"
    ".native{font-weight:600;color:#1e3a8a;margin:2px 0 4px}"
    ".desc{color:#475569;font-size:14px;margin:0 0 12px;max-width:820px}"
    "ul.words{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:4px 18px}"
    "ul.words li{display:flex;justify-content:space-between;border-bottom:1px dotted #e2e8f0;padding:3px 0}"
    "ul.words .word{font-weight:600}"
    "ul.words .ratio{color:#475569;font-variant-numeric:tabular-nums}"
    "footer{padding:22px 0;color:#475569;font-size:14px;border-top:1px solid #e2e8f0}"
)


def build_words_page(output_dir: str, site_url: str = "https://www.aiwordexplorer.com") -> None:
    """Generate words.html: top-N news words by LPR per language (item 7a).

    Reads the already-built data/*_news_gpt4.1-mini.json so it does NOT depend on
    csv_files being unpacked. Static, JS-free, for AI crawlers + readers. Output is
    written next to this script (the site root), not into the data/ directory.
    """
    model_slug = "gpt4.1-mini"
    build_date = datetime.date.today().isoformat()
    ordered = ["en"] + sorted([c for c in LANG_INFO if c != "en"], key=lambda c: LANG_INFO[c][0])

    toc_links = []
    sections = []
    n_langs = 0
    for code in ordered:
        path = os.path.join(output_dir, code + "_news_" + model_slug + ".json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        rows = [r for r in d.get("data", []) if r.get("lpr", 0) > 0]
        rows.sort(key=lambda x: x.get("lpr", 0), reverse=True)
        top = rows[:WORDS_TOP_N]
        if not top:
            continue
        en_name, autonym, native_q = LANG_INFO.get(code, (code.upper(), code, "Words AI overuses"))
        n_langs += 1
        toc_links.append('<a href="#' + code + '">' + _html.escape(autonym) + "</a>")
        items = []
        for r in top:
            w = _html.escape(str(r.get("w", "")))
            ratio = r.get("r", "")
            items.append('<li><span class="word">' + w + '</span><span class="ratio">' + str(ratio) + "×</span></li>")
        sections.append(
            '<section id="' + code + '" lang="' + code + '">\n'
            "  <h2>" + _html.escape(autonym) + ' <span class="en">' + _html.escape(en_name) + "</span></h2>\n"
            '  <p class="native">' + _html.escape(native_q) + "</p>\n"
            '  <p class="desc">The words ' + WORDS_MODEL_LABEL + " produces most disproportionately versus a matched human baseline in "
            + _html.escape(en_name) + " news text — top " + str(len(top))
            + " by Log Prevalence Ratio; the figure is how many times more frequent each word is in the model’s text.</p>\n"
            '  <ul class="words">' + "".join(items) + "</ul>\n"
            "</section>"
        )

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Words AI overuses, by language",
        "url": site_url + "/words.html",
        "isPartOf": {"@type": "WebSite", "name": "AI Word Explorer", "url": site_url + "/"},
        "dateModified": build_date,
        "about": "Words overused by " + WORDS_MODEL_LABEL + " relative to a matched human baseline across 34 languages",
        "author": {"@type": "Person", "name": "Thomas Stephan Juzek", "url": "https://ai.fsu.edu/research/thomas-stephan-juzek"},
        "citation": "https://arxiv.org/abs/2605.25358",
    }, ensure_ascii=False)

    page = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Words AI Overuses, by Language | AI Word Explorer</title>\n"
        "<meta name=\"description\" content=\"The words " + WORDS_MODEL_LABEL + " produces far more than a matched human baseline in news text — top " + str(WORDS_TOP_N) + " per language by Log Prevalence Ratio, across 34 languages. A measurement of model output.\">\n"
        "<link rel=\"canonical\" href=\"" + site_url + "/words.html\">\n"
        "<link rel=\"icon\" href=\"/favicon.ico\">\n"
        "<style>" + _WORDS_CSS + "</style>\n"
        "<script type=\"application/ld+json\">" + jsonld + "</script>\n"
        "</head>\n<body>\n"
        "<!-- words.html is generated by build_data.py. Native-language phrasings are DRAFT, pending linguistic review before publish. -->\n"
        "<header><div class=\"wrap\">\n"
        "<nav><a href=\"index.html\">Explorer</a> &middot; <a href=\"about.html\">About &amp; Method</a> &middot; <a href=\"https://github.com/fsu-nlp/lexa-index\">GitHub</a></nav>\n"
        "<h1>Words AI overuses, by language</h1>\n"
        "<p class=\"intro\">The words <strong>" + WORDS_MODEL_LABEL + "</strong> produces far more often than a matched human baseline in news text — the top " + str(WORDS_TOP_N) + " per language, ranked by Log Prevalence Ratio (LPR). The figure after each word is how many times more frequent it is in the model’s text than in human text. This describes the <em>model’s output</em>, not how people write or speak. See the <a href=\"about.html\">method and caveats</a>; data from <a href=\"https://arxiv.org/abs/2605.25358\">AI-Associated Lexical Shifts Across 34 Languages</a> (arXiv:2605.25358).</p>\n"
        "<p class=\"note\">This page is auto-generated for search and AI indexing — the interactive <a href=\"index.html\">Explorer</a> is the main experience. The native-language headings are machine-assisted and may contain errors.</p>\n"
        "</div></header>\n"
        "<div class=\"wrap\">\n"
        "<nav class=\"toc\" aria-label=\"Languages\">" + " ".join(toc_links) + "</nav>\n"
        "<main>\n" + "\n".join(sections) + "\n</main>\n"
        "<footer><p>&copy; 2026 <a href=\"https://tjuzek.com/\">TSJ</a> &middot; <a href=\"https://creativecommons.org/publicdomain/zero/1.0/\">CC0 1.0</a> (no warranty) &middot; built with Gemini and <a href=\"https://www.anthropic.com/product/claude-code\">Claude Code</a></p>"
        "<p><a href=\"index.html\">Explorer</a> &middot; <a href=\"about.html\">About</a> &middot; Last updated: " + build_date + " &middot; " + str(n_langs) + " languages</p></footer>\n"
        "</div>\n"
        "<!-- GoatCounter: private, cookieless visitor analytics (invisible to visitors) -->\n"
        "<script data-goatcounter=\"https://aiwordexplorer.goatcounter.com/count\" async src=\"//gc.zgo.at/count.js\"></script>\n"
        "</body>\n</html>\n"
    )

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print("📝 Generated words.html (" + str(n_langs) + " languages, top " + str(WORDS_TOP_N) + " by LPR)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build JSON datasets for LexA-Index website.")
    p.add_argument("--input-root", default=DEFAULT_INPUT_ROOT, help="Root directory containing csv_files/ outputs.")
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for website JSON files.")
    p.add_argument(
        "--min-ai-count-for-impact",
        type=int,
        default=DEFAULT_MIN_AI_COUNT_FOR_IMPACT,
        help="Minimum AI count (c_M) for a word to get a non-zero impact (LPR).",
    )
    p.add_argument(
        "--mode",
        choices=["full", "compact"],
        default="full",
        help="full = write all rows; compact = drop rows with c_M == 0 to save space.",
    )
    p.add_argument(
        "--ratio-smooth",
        type=float,
        default=DEFAULT_RATIO_SMOOTH,
        help="Additive smoothing constant for ratio=(c_M+smooth)/(c_H+smooth). Default: 0.5 (Jeffreys).",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process_directory(
        input_root=args.input_root,
        output_dir=args.output_dir,
        min_ai_count_for_impact=args.min_ai_count_for_impact,
        mode=args.mode,
        ratio_smooth=args.ratio_smooth,
    )
    build_words_page(output_dir=args.output_dir)

