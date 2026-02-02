# Data Guide (2013–2022) — Replication Package

This folder documents the datasets used in our replication project and explains
(1) where each dataset comes from,
(2) how the cleaned/final datasets are generated,
(3) what is (not) included in the public GitHub repo due to licensing restrictions.

> **Important note on redistribution**
> Our raw transcripts and many firm-level datasets originate from licensed databases
> (e.g., CapitalIQ and WRDS/CRSP-Compustat). These materials are typically **not allowed**
> to be redistributed publicly. Therefore, this repository **does not** include full raw data
> or full cleaned datasets that contain proprietary transcript text.

---

## 1) Data sources

Our replication focuses on earnings call Q&A during calendar years 2013–2022.

We work with four categories of data:

1. **Transcript text (earnings calls)**  
   - Earnings call transcript content used to extract Q&A pairs.

2. **Speaker details (component-level metadata)**  
   - Structured fields for each transcript component (Question/Answer tag, speaker type, order, timestamps).

3. **Corporate fundamentals (firm-level)**  
   - CRSP–Compustat linking keys and quarterly fundamentals for downstream analysis.

---

## 2) Local folder structure 

We keep full datasets locally (NOT pushed to GitHub). Suggested layout:

data/
  raw/                      # raw downloads (not tracked)
  intermediate/             # intermediate outputs (not tracked)
  final/                    # final full datasets (not tracked)
  samples/                  # small, shareable samples (tracked if permitted)
  README.md                 # this guide

---

## 3) File inventory 

Below are the main data files used/produced in our pipeline.

### (A) Raw / intermediate / final datasets (local-only; do NOT upload publicly)

- **Speaker Details.dta**  
  Component-level “speaker details” table used to reconstruct Q&A pairs.
  Key columns typically include:
  - transcriptid, companyid, cik
  - componentorder
  - transcriptcomponenttypename (Question/Answer)
  - speakertypename (Analysts/Executives)
  This file is very large and should remain local.

- **TranscriptDetails.dta**  
  Transcript-level metadata table (one row per transcript/call or per firm-call),
  used for call-level filtering and linking.

- **corporate information.dta**  
  Firm-level information (e.g., industry/GICS, identifiers).
  Used for sample selection screens (e.g., excluding missing industry info; excluding Finance/Utilities).

- **Final.dta**  
  The final cleaned dataset was used as the base for analysis and sampling.
  In our workflow, the 1,000 Q&A evaluation/analysis sample is drawn from this final dataset.

- **Clean_1.dta**  and **Clean_Q&A.dta**
  These are intermediate saved steps during cleaning; kept for debugging/reproducibility.
  Not required for final replication unless debugging.

> Note: The exact column names may differ slightly depending on your export settings,

---

### (B) Small derived samples (optional to upload if allowed)

- **Q&A.xlsx** 
  A derived sample of Q&A pairs (e.g., N=1,000) used for method comparisons (Table 2/3),
  typically including:
  - question / answer text (if available)
  - keyword matches
  - model predictions
  - manual labels for a subset (e.g., N=100)

**Caution:**  
`Q&A.xlsx` contains transcript text (question/answer), we will not upload it.


---

## 4) Sample construction logic (Table 1)

Our sample construction follows the steps reported in the replication report:

1. Start from the CapitalIQ universe (2013–2022), 12,614 unique firms (CIKs)
2. Exclude missing industry information and exclude Finance/Utilities (GICS 40 & 55)
3. Exclude firms without earnings call Q&A transcripts and firms with consistently <5 Q&A exchanges per call
4. Apply minimum-length criteria for meaningful Q&A:
   - question length ≥ 30
   - answer length ≥ 10
   - question + answer length ≥ 75
5. Final sample: 5,471 firms and 166,848 Q&A pairs (see Table 1 in our output and report)

---

## 5) How to reproduce (data pipeline)

### Step 0 — Put raw files in `data/raw/`
Place your raw exports (Speaker Details, TranscriptDetails, corporate information.)
into `data/raw/`.

### Step 1 — Clean the data and run stata sample construction script
Run:
- `code/sample construction code.do`

This script creates intermediate datasets and outputs:
- `Final.dta` (the finalized Q&A-level dataset for sampling/analysis)
- intermediate files like `Clean_Q&A.dta`, `Clean_1.dta`

### Step 2 — Draw evaluation/analysis samples
From `Final.dta`, draw:
- N=100 for manual labeling and evaluation
- N=1,000 for larger-sample analysis (Table 3)

### Step 3 — Run Python method scripts (Table 2/3)
Run Python scripts in `code/`:
- `Gow et al 2021.py`
- `Spark Pro(or Max).py`
- `Keyword+Spark Max.py`

They read the sample file (e.g., `Q&A.xlsx`) and generate the final tables in `output/`.

---

## 6) Public repo policy: what we upload vs keep local

### Keep local (not uploaded)
- raw transcript datasets
- full cleaned datasets containing proprietary transcript text
- large `.dta` / `.parquet` files

### Upload to GitHub
- all code (`code/`)
- report (`report/`)
- slides (`slides/`)
- table outputs (`output/TABLES...)

---

## 7) Contact / Notes
If you have licensed access to Capital IQ/WRDS and need guidance to reproduce the full pipeline, please follow the structure above and run the scripts in order.

