# 🛡️ deterministic-ai-gate

A low-power, zero-dependency verification pipeline that treats AI strictly as a natural-language parser while letting deterministic CPU scripts handle all cryptography, math, logic, and quote auditing.

---

## 🎯 Core Philosophy: AI Translates, CPU Verifies

Large language models are great at converting messy human text into structured fields—and terrible at exact arithmetic, strict chronological ordering, and verbatim quote fidelity. Instead of asking a massive model to "reason" over your entire problem, **`deterministic-ai-gate`** enforces a strict **3-stage boundary**:

1. **Stage 1 — Anchor & Fingerprint (`Zero AI`):** Hash the raw source document and individual chunks (`SHA-256`) into a tamper-evident `manifest.json` ledger *before* an AI ever touches the file.
2. **Stage 2 — Bounded Extraction (`Small / Local AI`):** Pass the raw text to a small model (e.g., via Ollama or `llama.cpp`) with a strict JSON schema prompt. The AI is forbidden from calculating totals, inferring missing dates, or paraphrasing quotes.
3. **Stage 3 — Deterministic Audit Gate (`Zero AI`):** Shut the AI off and run standard-library CPU scripts to verify exact fractions, detect timeline loops, and check every extracted quote against Stage 1 hashes—failing closed on any discrepancy.

---

## 📂 Repository Structure

```text
deterministic-ai-gate/
├── README.md                  # 3-stage architecture & quickstart guide
├── schemas/
│   └── extraction.schema.json # Strict JSON contract for Stage 2 LLM output
├── src/
│   ├── fingerprint.py         # Stage 1: SHA-256 document & paragraph ledger
│   └── verify.py              # Stage 3: Exact Fraction math, Kahn DAG, & quote audit
├── hooks/
│   └── pre-commit             # Optional Git hook to auto-fingerprint saved docs
└── tests/
    └── test_pipeline.py       # Standard-library unittest suite (zero dependencies)
```

---

## 🚀 Quickstart

### Requirements
* **Python 3.10+** (uses only `hashlib`, `json`, `fractions`, `collections`, `pathlib`, and `unittest`—zero `pip install` packages required).

### 1. Fingerprint a Source Document (Stage 1)
```bash
python3 src/fingerprint.py contract.txt --author "Jane Doe" --out manifest.json
```
Creates a `manifest.json` file containing the full-file `SHA-256` digest and individual paragraph chunk hashes.

### 2. Extract Structured JSON with a Small LLM (Stage 2)
Feed `contract.txt` into your local or cloud model using the prompt contract in `schemas/extraction.schema.json`:
> *"Extract entities, dates, and numeric ratios from the text below into valid JSON. Do not calculate totals, infer missing dates, or rewrite direct quotes. Copy quotes verbatim."*

### 3. Verify Math, Timelines & Quotes (Stage 3)
```bash
python3 src/verify.py --manifest manifest.json --extracted ai_output.json
```
The verification gate checks three invariants and raises a `ValueError` (failing closed) if any check fails:
* **Exact Rational Math (`fractions.Fraction`):** Multiplies extracted ratios as exact whole-number fractions (`p/q`) without IEEE-754 floating-point drift.
* **Timeline Cycle Detector (Kahn's Algorithm):** Validates chronological event edges `(before, after)` and rejects circular dependencies or paradoxes.
* **Provenance Quote Audit (`SHA-256`):** Hashes every extracted quote and confirms it matches a verbatim chunk hash in `manifest.json`.

---

## 🧪 Run the Verification Test Suite

```bash
python3 -m unittest discover -s tests -v
```

---

## 🔒 Automation & Git Hooks

To automatically generate a cryptographic ledger whenever source documents are committed:

```bash
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## 📄 License

MIT
