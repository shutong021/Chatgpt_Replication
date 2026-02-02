# ChatGPT Replication — Detecting Non-Answers in Earnings Conference Call Q&A (2013–2022)

This repository contains our team replication package for a study on strategic non-answers in earnings call Q&A.  
A “non-answer” is defined as a managerial statement that signals **unwillingness or inability** to answer an analyst’s question (rather than simply a low-quality or vague answer).

We replicate the **sample construction logic** and implement several **automated non-answer detection methods**, including a rule-based baseline and LLM-based classifiers, and summarize results in the provided tables and report.

---

## Repository structure

- `code/`
  - `sample construction code.do` — sample construction & cleaning (Stata)
  - `Gow et al 2021.py` — rule-based baseline detection
  - `Spark Pro(or Max).py` — LLM-based classification (Spark)
  - `Keyword+Spark Max.py` — two-stage pipeline: keyword prefilter + Spark Max
  - `Table+generator.py` — generate excel
- `output/`
  - `TABLES (CUHK REPLICATION).xlsx` — final result tables for presentation/report
- `report/`
  - `Replication Report.pdf` — replication write-up
- `slides/`
  - `chatgpt_replication_slides_revised.pdf`
- `data/`
  - `README.md` — data sources, local folder convention, and reproduction instructions
- `technical blog.md/` — Replication Notes & Pipeline

---

## What we replicate

### 1) Sample construction (Table 1)
We follow the sample construction logic described in our report (CapitalIQ universe 2013–2022, industry exclusions, call/Q&A availability screens, and minimum-length filters for meaningful Q&A pairs).  
See `report/Replication Report.pdf` and `data/README.md`.

### 2) Method comparisons (Table 2 / Table 3)
We compare multiple non-answer detection approaches, including:
- **Gow et al. (2021) baseline** (rule/regex)
- **Spark Pro / Spark Max** (LLM-based classifier)
- **Keyword + Spark Max** (keyword prefilter + LLM)

Results are summarized in `output/TABLES (CUHK REPLICATION).xlsx`.

---

## Data availability

Raw transcripts and firm-level datasets originate from **licensed sources** (e.g., CapitalIQ and WRDS/CRSP) and typically **cannot be redistributed publicly**.  
Therefore, we do **not** upload raw/full cleaned datasets or any transcript text to this public repository.

Instructions for local data setup are provided in `data/README.md`.

---

## How to reproduce

1. Prepare local raw exports following `data/README.md`
2. Run Stata sample construction:
   - `code/sample construction code.do`
3. Run Python scripts under `code/` to generate method outputs and summary tables
4. Compare outputs with:
   - `output/TABLES (CUHK REPLICATION).xlsx`

---

## Notes on deviations from the original paper

Due to data access constraints (API quotas/licensing), our replication may differ from the original study in data source and sample universe.  
We document these deviations in the report and slides.

---

## Contact / Team
If you have licensed access to the data and want to reproduce the full pipeline, follow `data/README.md`.
