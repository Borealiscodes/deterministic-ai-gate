# 🛡️ deterministic-ai-gate

A low-power, zero-dependency verification pipeline that treats AI strictly as a natural-language parser while letting deterministic CPU scripts handle all cryptography, math, logic, and quote auditing.

> ### 🚧 Project Status: Untested Reference Implementation
> **Transparency Note:** The scripts, schemas, examples, and unit tests in this repository were drafted as a clean-room architectural baseline and **have not yet been executed or verified end-to-end**. Please run the `unittest` suite locally to verify behavior before using this in any real workflow.

---

## 💡 Why This Tool Exists

When people use AI to process important documents—like contracts, invoices, medical notes, or research papers—two things go wrong:

1. **AI Models Are Bad Calculators and Fact-Checkers:** Large language models predict the next likely word. Because of how they work, they silently round off fractions, lose track of chronological timelines, and slightly paraphrase direct quotes while claiming they are exact.
2. **Throwing a Massive Model at Everything Wastes Power and Money:** You do not need a giant cloud data center to extract a few numbers and sentences from a text file.

**`deterministic-ai-gate`** solves both problems by giving each tool the exact job it is built for:
* **Use a small, local AI** only to read messy human text and turn it into clean JSON fields.
* **Use fast, zero-dependency Python code** on your CPU to lock down the original text with a fingerprint, do exact fraction math, catch impossible timelines, and verify that every quote matches the original document word-for-word.

If the AI hallucinates a number, scrambles a timeline, or changes a single character in a quote, the gate **fails closed** and blocks the output immediately.

---

## 🎯 How the 3-Stage Pipeline Works

1. **Stage 1 — Anchor & Fingerprint (`Zero AI`):** Hash the raw source document and individual paragraphs (`SHA-256`) into a tamper-evident `manifest.json` ledger *before* an AI ever touches the file.
2. **Stage 2 — Bounded Extraction (`Small / Local AI`):** Pass the raw text to a small model (e.g., via Ollama or `llama.cpp`) with a strict JSON schema prompt. The AI is forbidden from calculating totals, inferring missing dates, or paraphrasing quotes.
3. **Stage 3 — Deterministic Audit Gate (`Zero AI`):** Shut the AI off and run standard-library CPU scripts to verify exact fractions, detect timeline loops, and check every extracted quote against Stage 1 hashes—raising an error if anything is off.

---

## 📂 Repository Structure

```text
deterministic-ai-gate/
├── README.md                    # Plain-English overview, architecture & quickstart guide
├── schemas/
│   └── extraction.schema.json   # Strict JSON contract for Stage 2 LLM output
├── src/
│   ├── fingerprint.py           # Stage 1: SHA-256 document & paragraph ledger
│   └── verify.py                # Stage 3: Exact Fraction math, Kahn DAG, & quote audit
├── examples/
│   ├── sample_contract.txt      # Sample raw text document for Stage 1
│   ├── sample_ai_output.json    # Valid Stage 2 JSON extraction (passes Stage 3)
│   └── sample_tampered_output.json # Hallucinated Stage 2 JSON (fails closed in Stage 3)
├── hooks/
│   └── pre-commit               # Optional Git hook to auto-fingerprint saved docs
└── tests/
    └── test_pipeline.py         # Standard-library unittest suite (zero dependencies)
```

---

## 🚀 Quickstart (Using the Included Examples)

### Requirements
* **Python 3.10+** (uses only `hashlib`, `json`, `fractions`, `collections`, `pathlib`, `argparse`, and `unittest`—zero `pip install` packages required).

### 1. Fingerprint the Sample Document (Stage 1)
```bash
python3 src/fingerprint.py examples/sample_contract.txt --author "Demo User" --out examples/manifest.json
```
Creates `examples/manifest.json` containing the full-file `SHA-256` digest and individual paragraph chunk hashes.

### 2. Run Your AI Extraction Prompt (Stage 2)
When running your own documents through a local or cloud model, enforce the JSON layout in `schemas/extraction.schema.json`:
> *"Extract entities, dates, and numeric ratios from the text below into valid JSON. Do not calculate totals, infer missing dates, or rewrite direct quotes. Copy quotes verbatim."*

*(To test Stage 3 immediately without running a model, use the pre-built JSON files in `examples/`.)*

### 3. Verify Math, Timelines & Quotes (Stage 3)
```bash
# Test a valid extraction (passes and outputs exact_rational: "900/1")
python3 src/verify.py --manifest examples/manifest.json --extracted examples/sample_ai_output.json

# Test a hallucinated extraction (fails closed with ValueError)
python3 src/verify.py --manifest examples/manifest.json --extracted examples/sample_tampered_output.json
```

The verification gate checks three invariants:
* **Exact Rational Math (`fractions.Fraction`):** Multiplies extracted ratios as exact whole-number fractions (`p/q`) without IEEE-754 floating-point drift, bounded by a 2048-bit precision cap.
* **Timeline Cycle Detector (Kahn's Algorithm):** Deduplicates chronological event edges `[before, after]` and rejects circular dependencies or paradoxes.
* **Provenance Quote Audit (`SHA-256`):** Hashes every extracted quote and confirms it matches a verbatim chunk hash (or verified substring) in `manifest.json`. Use `--strict-chunks` to require full-paragraph hash matches only.

---

## 🧪 Run the Unit Test Suite

```bash
python3 -m unittest discover -s tests -v
```

---

## 🔒 Automation & Git Hooks

To automatically generate a cryptographic ledger whenever `.txt` or `.md` source documents are committed:

```bash
cp hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## 📄 License

MIT
