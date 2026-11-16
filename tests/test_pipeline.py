#!/usr/bin/env python3
"""Standard-library unit tests for deterministic-ai-gate."""

from __future__ import annotations

import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

# Allow importing from src/ without installing a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fingerprint import create_manifest
from verify import (
    calculate_exact_total,
    check_timeline_consistency,
    verify_extraction,
    verify_quote,
)


class TestDeterministicAIGate(unittest.TestCase):
    def test_exact_rational_math_avoids_float_drift(self) -> None:
        # 100 * (1/3) * (3/1) must equal exact 100/1
        result = calculate_exact_total("100", ["1/3", "3/1"])
        self.assertEqual(result, Fraction(100, 1))

        # Chained thirds and sevenths stay irreducible
        chained = calculate_exact_total("1", ["1/3", "1/7", "21/1"])
        self.assertEqual(chained, Fraction(1, 1))

    def test_timeline_dag_valid_order_and_cycle_rejection(self) -> None:
        order = check_timeline_consistency([("Draft", "Review"), ("Review", "Publish")])
        self.assertEqual(order, ["Draft", "Review", "Publish"])

        with self.assertRaisesRegex(ValueError, "Timeline Paradox Detected"):
            check_timeline_consistency([("EventA", "EventB"), ("EventB", "EventA")])

    def test_fingerprint_and_verbatim_quote_verification(self) -> None:
        sample_text = (
            "Clause 1: Payment is due within 30 days of invoice receipt.\n\n"
            "Clause 2: Late balances accrue a 1/20 administrative fee."
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "contract.txt"
            manifest_path = Path(tmpdir) / "manifest.json"
            doc_path.write_text(sample_text, encoding="utf-8")

            manifest = create_manifest(doc_path, author="Alice", out_path=manifest_path)
            self.assertEqual(manifest["chunk_count"], 2)

            # Verbatim quote passes
            self.assertTrue(
                verify_quote("Clause 1: Payment is due within 30 days of invoice receipt.", manifest)
            )

            # Even a single altered character fails closed
            with self.assertRaisesRegex(ValueError, "Provenance Error"):
                verify_quote("Clause 1: Payment is due within 31 days of invoice receipt.", manifest)

    def test_end_to_end_verification_gate(self) -> None:
        sample_text = "Section A: Base allocation is 250 units subject to a 3/5 adjustment."
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "memo.txt"
            doc_path.write_text(sample_text, encoding="utf-8")
            manifest = create_manifest(doc_path, author="Bob")

            ai_output = {
                "entities": ["Section A"],
                "math": {"base": "250", "multipliers": ["3/5"]},
                "timeline_edges": [["Ingest", "Extract"], ["Extract", "Verify"]],
                "quotes": [sample_text],
            }
            summary = verify_extraction(manifest, ai_output)
            self.assertTrue(summary["verified"])
            self.assertEqual(summary["exact_rational"], "150/1")
            self.assertEqual(summary["verified_quote_count"], 1)


if __name__ == "__main__":
    unittest.main()
