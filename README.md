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

## Citation

If you use this code or data, a citation is appreciated (though not required; see the licence).

```bibtex
@article{juzek-2026-ai-34-languages,
  title   = {AI-Associated Lexical Shifts Across 34 Languages: Cross-Lingual Convergence and Diachronic Uptake in News Writing},
  author  = {Juzek, Thomas Stephan},
  journal = {arXiv preprint arXiv:2605.25358},
  year    = {2026},
  doi     = {10.48550/arXiv.2605.25358},
  url     = {https://arxiv.org/abs/2605.25358}
}
```

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

## Licence

- **Code:** MIT No Attribution (MIT-0). See [`LICENSE`](LICENSE). Use it freely, no attribution required.
- **Data and word lists:** CC0 1.0 Universal (public domain dedication). See [`LICENSE-DATA`](LICENSE-DATA).

A citation is not required but is appreciated; see the Citation section.

## AI Assistance

Repository polished with Claude Code.

## Contact

Thomas Stephan Juzek — [FSU profile](https://ai.fsu.edu/research/thomas-stephan-juzek)
