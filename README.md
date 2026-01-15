# LexA-Index | Lexical Alignment for LLMs 📊

AI generated placeholder: 

**LexA-Index** is an interactive web visualization tool designed to identify and analyze words significantly overused by AI compared to human baselines across various languages, registers, and model architectures.

Developed at the **FSU NLP Lab**, this project quantifies the "drift" in machine-generated text, highlighting the emergence of "modelese."

## 🔍 Key Features

* **Interactive Explorer:** Filter data by Model, Register (e.g., News, Science), and Language.
* **Dual Views:** Toggle between visual **Charts** and detailed **Data Tables**.
* **Metric Analysis:** View data sorted by **Lexical Alignment Score (LAS)** and **Occurrences Per Million (OPM)**.
* **POS Filtering:** Isolate Content words vs. Function words.
* **Deep Dive:** Automated insights carousel highlighting the most divergent vocabulary.

## 📐 Methodology

The core metric is the **Lexical Alignment Score (LAS)**, which calculates the difference in windowed prevalence between AI and Human text.



1.  **Input:** Raw experimental data (CSV) and summary statistics (JSON).
2.  **Processing:** A Python pipeline normalizes frequencies using a fixed window size ($K$) to calculate the likelihood of appearance.
3.  **Visualization:** The static web interface renders these divergences using `Chart.js` and `Alpine.js`.

## 🚀 Quick Start

### 1. Data Generation
Place your raw experimental outputs in the `raw_data/` directory and run the processor:

```bash
python process_data.py