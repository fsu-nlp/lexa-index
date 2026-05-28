# LexA-Index (AI Word Overuse Explorer)

**Paper:** *AI-Associated Lexical Shifts Across 34 Languages: Cross-Lingual Convergence and Diachronic Uptake in News Writing* — [arXiv:2605.25358](https://arxiv.org/abs/2605.25358) · **Live explorer:** [aiwordexplorer.com](https://www.aiwordexplorer.com/)

The Explorer lets you explore words that are systematically overused by AI models compared to human baselines, across multiple languages, registers, and AI models.

This repository contains:
- the website (`index.html`, `about.html`)
- the CSV outputs (as a 7z, unzip in the top level folder)
- a small script to build website-ready json's from the cvs's (`build_data.py`).


## What this is for

With this repo, you can:
- reproduce the website data build locally,
- inspect the underlying csv's,
- and interactively visualise results for all available language/register/model combinations.

Motivation and background are summarised on the About page.


## Quick start

- Clone
- Unpack the .7z
- Generate them from the CSVs with:

```bash
python3 build_data.py
```

- Serve locally

```bash
python3 -m http.server
```

Then open:

* [http://localhost:8000/](http://localhost:8000/)


## Key metrics include:

* LAS Score: Laid out in our paper
* OPM: occurrences per million tokens (AI and human)
* Ratio: AI OPM / human OPM


## Citation

If you use the Explorer or the underlying word lists, please cite:

```bibtex
@misc{juzek2026lexical,
  title         = {AI-Associated Lexical Shifts Across 34 Languages: Cross-Lingual Convergence and Diachronic Uptake in News Writing},
  author        = {Juzek, Thomas Stephan},
  year          = {2026},
  eprint        = {2605.25358},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url           = {https://arxiv.org/abs/2605.25358}
}
```


## Licence

tbd


## Contact

tbd

