# technical_blog.md — Replication Log & Reproducibility Notes
*(Team replication package: Strategic Non-Answers in Earnings Call Q&A, 2013–2022)*

This technical blog serves as a “lab notebook” for our replication project:
- documenting the full pipeline (data → sample construction → methods → tables),
- recording practical implementation details and debugging notes,
- clarifying deviations from the original paper due to data access constraints,
- ensuring future readers (and our future selves) can reproduce the workflow.

> **Data redistribution notice**
> Our underlying transcript and firm datasets come from licensed sources (e.g., CapitalIQ and WRDS/CRSP-Compustat).
> We do **not** redistribute raw transcripts, cleaned full datasets, or any Q&A text samples in this public repository.
> See `data/README.md` for local setup.

---

## 1) Project goal and research question

### 1.1 Why “non-answers” matter
In earnings call Q&A, management sometimes “sounds responsive” but does not actually address the analyst’s question.
This is meaningful because Q&A is the part of the call where analysts directly probe for clarifications, guidance, and details.
Systematic non-answers can therefore reflect information asymmetry and strategic disclosure behavior.

### 1.2 Definition used in our replication
We follow the paper’s conceptual definition: a “non-answer” is **not** merely a vague or unsatisfactory response.
Instead, it requires a clear indication of:
- **unwillingness** to answer (refusal / cannot comment / do not disclose), or
- **inability** to answer (do not have the information / not available / cannot quantify).

We also note common “confusable” cases (to avoid over-labeling):
- generic forward-looking uncertainty *without* refusal,
- situations where a short disclaimer is followed by a substantive answer.

---

## 2) Data overview (what we have vs. what the original paper has)

### 2.1 Original paper data (target benchmark)
The original paper retrieves earnings call transcripts via an API source, applies call-level filters
(e.g., presentation section present; minimum Q&A counts), and scales to a very large corpus.
The paper then constructs Q&A pairs, applies length filters, and draws a manually labeled evaluation sample
for benchmarking methods.

### 2.2 Our replication data (licensed sources; access constraints)
Our replication uses licensed datasets downloaded from:
- **Capital IQ** (earnings call transcripts and identifiers), 2013–2022 calendar years
- **Speaker/component-level “speaker details”** tables (Question/Answer tags, speaker type, component order)
- **Corporate information** (industry classification; identifiers)

Because we cannot redistribute transcripts publicly and because API-based full-corpus collection is constrained,
we focus on **faithfully reproducing the pipeline and table logic** on the data available to us.

> Full details on file placement and local folder structure are in `data/README.md`.

---

## 3) Sample construction (Table 1 logic)

### 3.1 Sample construction objective
We construct a firm-level sample and a Q&A-level sample consistent with the report’s Table 1 logic:
1) Start with all unique firms (CIKs) in the CapitalIQ universe (2013–2022).
2) Exclude firms lacking industry information and exclude Finance/Utilities (GICS 40 & 55).
3) Exclude firms without earnings call Q&A transcripts and those with consistently too few Q&A exchanges.
4) Apply minimum-length filters for meaningful Q&A:
   - question length ≥ 30
   - answer length ≥ 10
   - combined length ≥ 75

### 3.2 Implementation (Stata)
- Script: `code/sample construction code.do`
- Output: `Final.dta` (local-only), plus intermediate datasets (local-only)

### 3.3 Practical notes
- Keep intermediate `.dta` saves during cleaning so we can debug encoding and merge issues.
- Prefer stable keys (e.g., transcriptid + componentorder) when reconstructing Q&A pairs from component tables.
- Record exact exclusions and counts so Table 1 can be audited line-by-line.

---

## 4) Transcript parsing & Q&A reconstruction (team pipeline)

Our team’s cleaning pipeline reconstructs Q&A pairs from component-level transcript structures:

### 4.1 Component → Q&A pairing concept
Given a transcript represented as an ordered list of components (e.g., Presentation, Question, Answer, …):
- identify sequences of Question components (analysts)
- pair them with the subsequent Answer components (executives)
- preserve the chain order (`pair_i`, `componentorder`, etc.)

### 4.2 Common cleaning steps
- remove duplicated component rows when transcript components were repeated in exports
- enforce a minimum number of Q&A pairs per call (to exclude low-information calls)
- enforce minimum-length filters (to remove “meaningless” short pairs)

### 4.3 Debugging lessons learned
- **Duplicate keys** can break Python `.to_dict(orient="index")` and any “index-as-key” logic.
  Fix: enforce uniqueness with a deterministic key and drop duplicates before building maps.
- **Empty transcript edge case**: some transcript IDs may have metadata but missing components after filtering.
  Fix: guard against empty lists before indexing (`if len(transcript)==0: skip`).
- **Encoding issues**: exporting from Stata / reading into Python may produce Unicode errors.
  Fix: use `encoding="utf-8-sig"` when possible; fall back to `latin1` only for legacy exports; avoid mixed encodings.

---

## 5) Methods: non-answer detection approaches (Table 2 / Table 3)

We implement and compare three families of approaches:

### 5.1 Rule-based baseline (Gow et al. 2021)
- Script: `code/Gow et al 2021.py`
- Idea: use a curated set of rules/regex patterns to detect refusal/inability language.
- Strength: fast, interpretable.
- Weakness: brittle to context (misses subtle semantics; may confuse forward-looking uncertainty vs refusal).

### 5.2 LLM classifier (Spark Pro / Spark Max)
- Script: `code/Spark Pro(or Max).py`
- Idea: treat the LLM as a semantic classifier that outputs a binary label:
  whether the response includes a statement indicating unwillingness/inability.

### 5.3 Two-stage pipeline (Keyword + Spark Max)
- Script: `code/Keyword+Spark Max.py`
- Stage A (keyword prefilter):
  - If no keyword hit → classify as 0 (non non-answer), no LLM call.
  - If keyword hit → proceed to Stage B.
- Stage B (LLM classifier):
  - run Spark Max classification and output the final label.
- Why this matters:
  - reduces cost and latency by limiting LLM calls,
  - reduces false positives compared to keyword-only approaches,
  - makes the pipeline scalable to larger corpora.
  - 
### 5.4 Generate final tables workbook
- Input: data/samples/Q&A.xlsx (local-only)
- Run: python code/table_generator.py
- Output: output/replication_table2_table3_results.xlsx
Notes: script auto-detects prediction columns; uses Manual as ground truth; outputs Table2_eval / Confusion_eval / Table3_pair_level sheets

## 6) What we replicate vs. what we add (differences from the original paper)

### 6.1 Differences (due to data source / access)
- **Data source**: We rely on licensed CapitalIQ/WRDS exports rather than the original API-based transcript retrieval pipeline.
- **Sample universe**: Our firm/call universe and filters may differ depending on which identifiers and transcript coverage are available.
- **Public reproducibility**: We do not provide Q&A text samples or full datasets, only code + outputs.

These deviations can contribute to quantitative differences in reported rates and classification performance.

### 6.2 What we add (beyond the original scope)
In addition to replicating table logic and method comparisons, our team emphasizes:
- a clean and modularized pipeline (Stata cleaning + Python evaluation scripts),
- a two-stage “keyword + LLM” approach that is straightforward to explain in class,
- unified table formatting for presentation consistency.


---

## 7) Outputs: where results live

### 7.1 Primary deliverable
- `output/TABLES (CUHK REPLICATION).xlsx`
  - contains the summarized tables used in the report and slides
  - includes method comparisons (confusion matrices; Type I / Type II; Accuracy) for evaluation subsets
  - includes larger-sample summaries when applicable

### 7.2 Report and slides
- `report/Replication Report.pdf`
- `slides/chatgpt_replication_slides_revised.pdf

---

## 8) How to reproduce

> Prerequisite: licensed access to CapitalIQ/WRDS data and local exports.

### Step 1 — Local data placement
Follow `data/README.md` and place raw exports under `data/raw/` locally.

### Step 2 — Run sample construction (Stata)
Run:
- `code/sample construction code.do`

This produces `Final.dta` (local-only).

### Step 3 — Run method scripts (Python)
Run:
- `code/Gow et al 2021.py`
- `code/Spark Pro(or Max).py`
- `code/Keyword+Spark Max.py`

These scripts will generate outputs and tables under `output/`.

### Step 4 — Verify tables
Check:
- row counts / exclusion counts align with report’s Table 1 logic
- evaluation performance tables match the numbers reported in `output/TABLES...xlsx`

---
