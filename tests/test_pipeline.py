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

    def test_rational_safety_bounds_and_malformed_numbers(self) -> None:
        # Division by zero or invalid strings fail closed
        with self.assertRaisesRegex(ValueError, "Invalid rational number"):
            calculate_exact_total("10", ["1/0"])

        with self.assertRaisesRegex(ValueError, "Invalid numeric value type"):
            calculate_exact_total(True, ["1/2"])  # type: ignore[arg-type]

        # Exceeding 2048-bit precision bound fails closed
        huge_denom = "1/" + ("9" * 700)
        with self.assertRaisesRegex(ValueError, "safety bound"):
            calculate_exact_total("1", [huge_denom])

    def test_float_overflow_handled_gracefully(self) -> None:
        # Large integer within 2048-bit bound (~10^400) exceeds IEEE-754 float (~10^308)
        big_num = str(10**400)
        summary = verify_extraction(
            {"chunks": []},
            {"entities": [], "math": {"base": big_num, "multipliers": []}, "quotes": []},
        )
        self.assertEqual(summary["exact_rational"], f"{big_num}/1")
        self.assertIsNone(summary["decimal_approx"])

    def test_timeline_dag_valid_order_deduplication_and_cycle_rejection(self) -> None:
        # Handles duplicate edges and whitespace padding cleanly
        order = check_timeline_consistency(
            [
                (" Draft ", "Review"),
                ("Draft", " Review "),
                ("Review", "Publish"),
            ]
        )
        self.assertEqual(order, ["Draft", "Review", "Publish"])

        with self.assertRaisesRegex(ValueError, "Timeline Paradox Detected"):
            check_timeline_consistency([("EventA", "EventB"), ("EventB", "EventA")])

        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            check_timeline_consistency([("Draft", "   ")])

    def test_fingerprint_substring_and_tamper_detection(self) -> None:
        sample_text = (
            "Clause 1: Payment is due within 30 days of invoice receipt. Late fees apply.\n\n"
            "Clause 2: Late balances accrue a 1/20 administrative fee."
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "contract.txt"
            manifest_path = Path(tmpdir) / "manifest.json"
            doc_path.write_text(sample_text, encoding="utf-8")

            manifest = create_manifest(doc_path, author="Alice", out_path=manifest_path)
            self.assertEqual(manifest["chunk_count"], 2)

            # Full paragraph hash passes
            self.assertTrue(
                verify_quote(
                    "Clause 1: Payment is due within 30 days of invoice receipt. Late fees apply.",
                    manifest,
                )
            )

            # Verbatim sentence substring passes by default
            self.assertTrue(
                verify_quote("Payment is due within 30 days of invoice receipt.", manifest)
            )

            # Substring fails when strict chunk matching is enforced
            with self.assertRaisesRegex(ValueError, "Provenance Error"):
                verify_quote(
                    "Payment is due within 30 days of invoice receipt.",
                    manifest,
                    allow_substrings=False,
                )

            # Altered word fails closed
            with self.assertRaisesRegex(ValueError, "Provenance Error"):
                verify_quote("Payment is due within 31 days of invoice receipt.", manifest)

            # Tampering with chunk text in manifest.json fails closed
            tampered_manifest = {
                "chunks": [
                    {
                        "index": 0,
                        "sha256": manifest["chunks"][0]["sha256"],
                        "text": "Clause 1: Payment is due within 99 days of invoice receipt.",
                    }
                ]
            }
            with self.assertRaisesRegex(ValueError, "Manifest Integrity Error"):
                verify_quote("within 99 days", tampered_manifest)

    def test_end_to_end_verification_and_payload_guards(self) -> None:
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

            # Non-object AI output fails closed
            with self.assertRaisesRegex(ValueError, "must be a JSON object"):
                verify_extraction(manifest, [ai_output])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
