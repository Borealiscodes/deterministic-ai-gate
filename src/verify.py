#!/usr/bin/env python3
"""Stage 3: Deterministic CPU Audit Gate (Zero External Dependencies)."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path

MAX_RATIONAL_BITS = 2048


def _parse_bounded_fraction(value: str | int) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"Invalid numeric value type: {type(value).__name__}")
    raw = str(value).strip()
    if not raw:
        raise ValueError("Numeric value cannot be empty.")
    try:
        frac = Fraction(raw)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"Invalid rational number {value!r}: {exc}") from exc

    if frac.numerator.bit_length() > MAX_RATIONAL_BITS or frac.denominator.bit_length() > MAX_RATIONAL_BITS:
        raise ValueError(f"Rational precision exceeds {MAX_RATIONAL_BITS}-bit safety bound.")
    return frac


def calculate_exact_total(base: str | int, multipliers: list[str | int]) -> Fraction:
    """Multiply exact rational numbers without IEEE-754 floating-point drift."""
    total = _parse_bounded_fraction(base)
    for m in multipliers:
        total *= _parse_bounded_fraction(m)
        if total.numerator.bit_length() > MAX_RATIONAL_BITS or total.denominator.bit_length() > MAX_RATIONAL_BITS:
            raise ValueError(f"Accumulated rational exceeds {MAX_RATIONAL_BITS}-bit safety bound.")
    return total


def check_timeline_consistency(events: list[tuple[str, str] | list[str]]) -> list[str]:
    """Validate chronological edges (before -> after) using Kahn's topological sort."""
    if not isinstance(events, list):
        raise ValueError("timeline_edges must be a list of [before, after] pairs.")

    normalized_edges: list[tuple[str, str]] = []
    for edge in events:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError(f"Invalid timeline edge (expected 2 items): {edge!r}")
        before, after = str(edge[0]).strip(), str(edge[1]).strip()
        if not before or not after:
            raise ValueError(f"Timeline event names cannot be empty: {edge!r}")
        normalized_edges.append((before, after))

    # Deduplicate identical edges while preserving deterministic order
    unique_edges = list(dict.fromkeys(normalized_edges))

    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()

    for before, after in unique_edges:
        graph[before].append(after)
        in_degree[after] += 1
        nodes.update([before, after])

    queue = deque(sorted(n for n in nodes if in_degree[n] == 0))
    ordered: list[str] = []

    while queue:
        curr = queue.popleft()
        ordered.append(curr)
        for nxt in sorted(graph[curr]):
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
                queue = deque(sorted(queue))

    if len(ordered) != len(nodes):
        raise ValueError("Timeline Paradox Detected: Circular dependency in events!")

    return ordered


def verify_quote(ai_quote: str, manifest: dict, allow_substrings: bool = True) -> bool:
    """Verify an extracted quote against Stage 1 SHA-256 chunk hashes (and optional verbatim substrings)."""
    if not isinstance(ai_quote, str):
        raise ValueError("Provenance Error: Quote must be a string.")
    normalized = ai_quote.strip()
    if not normalized:
        raise ValueError("Provenance Error: Quote cannot be empty.")

    chunks = manifest.get("chunks", [])
    quote_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    valid_hashes = {chunk["sha256"] for chunk in chunks if "sha256" in chunk}

    if quote_hash in valid_hashes:
        return True

    if allow_substrings:
        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            # Ensure chunk itself hasn't been tampered with since Stage 1
            if hashlib.sha256(chunk_text.encode("utf-8")).hexdigest() != chunk.get("sha256"):
                raise ValueError("Manifest Integrity Error: Chunk text does not match its SHA-256 digest!")
            if normalized in chunk_text:
                return True

    raise ValueError("Provenance Error: AI altered the quote or cited an unverified source!")


def verify_extraction(manifest: dict, extracted: dict, allow_substrings: bool = True) -> dict:
    """Run all Stage 3 deterministic checks on structured Stage 2 JSON output."""
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object.")
    if not isinstance(extracted, dict):
        raise ValueError("Extracted AI payload must be a JSON object.")

    summary: dict = {"verified": True}

    if "math" in extracted and extracted["math"] is not None:
        m = extracted["math"]
        if not isinstance(m, dict) or "base" not in m:
            raise ValueError("Invalid 'math' payload: expected object with 'base'.")
        multipliers = m.get("multipliers", [])
        if not isinstance(multipliers, list):
            raise ValueError("Invalid 'math.multipliers': expected list.")

        exact = calculate_exact_total(m["base"], multipliers)
        summary["exact_rational"] = f"{exact.numerator}/{exact.denominator}"
        try:
            summary["decimal_approx"] = float(exact)
        except OverflowError:
            summary["decimal_approx"] = None

    if "timeline_edges" in extracted and extracted["timeline_edges"] is not None:
        summary["topological_order"] = check_timeline_consistency(extracted["timeline_edges"])

    quotes = extracted.get("quotes", [])
    if not isinstance(quotes, list):
        raise ValueError("Invalid 'quotes' payload: expected list of strings.")
    for q in quotes:
        verify_quote(q, manifest, allow_substrings=allow_substrings)
    summary["verified_quote_count"] = len(quotes)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Stage 2 AI JSON output against Stage 1 manifest.")
    parser.add_argument("--manifest", required=True, help="Path to Stage 1 manifest.json")
    parser.add_argument("--extracted", required=True, help="Path to Stage 2 AI JSON output")
    parser.add_argument("--strict-chunks", action="store_true", help="Require full paragraph hash match only")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    extracted = json.loads(Path(args.extracted).read_text(encoding="utf-8"))

    result = verify_extraction(manifest, extracted, allow_substrings=not args.strict_chunks)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
