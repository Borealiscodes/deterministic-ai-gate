#!/usr/bin/env python3
"""Stage 3: Deterministic CPU Audit Gate (Zero External Dependencies)."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path


def calculate_exact_total(base: str | int, multipliers: list[str | int]) -> Fraction:
    """Multiply exact rational numbers without IEEE-754 floating-point drift."""
    total = Fraction(base)
    for m in multipliers:
        total *= Fraction(m)
    return total


def check_timeline_consistency(events: list[tuple[str, str] | list[str]]) -> list[str]:
    """Validate chronological edges (before -> after) using Kahn's topological sort."""
    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()

    for edge in events:
        if len(edge) != 2:
            raise ValueError(f"Invalid timeline edge (expected 2 items): {edge!r}")
        before, after = str(edge[0]), str(edge[1])
        graph[before].append(after)
        in_degree[after] += 1
        nodes.update([before, after])

    # Deterministic lexicographic tie-breaking
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


def verify_quote(ai_quote: str, manifest: dict) -> bool:
    """Verify an extracted quote matches a verbatim chunk SHA-256 hash in the manifest."""
    normalized = ai_quote.strip()
    if not normalized:
        raise ValueError("Provenance Error: Quote cannot be empty.")

    quote_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    valid_hashes = {chunk["sha256"] for chunk in manifest.get("chunks", [])}

    if quote_hash not in valid_hashes:
        raise ValueError("Provenance Error: AI altered the quote or cited an unverified source!")

    return True


def verify_extraction(manifest: dict, extracted: dict) -> dict:
    """Run all Stage 3 deterministic checks on structured Stage 2 JSON output."""
    summary: dict = {"verified": True}

    if "math" in extracted and extracted["math"] is not None:
        m = extracted["math"]
        exact = calculate_exact_total(m["base"], m.get("multipliers", []))
        summary["exact_rational"] = f"{exact.numerator}/{exact.denominator}"
        summary["decimal_approx"] = float(exact)

    if "timeline_edges" in extracted and extracted["timeline_edges"] is not None:
        summary["topological_order"] = check_timeline_consistency(extracted["timeline_edges"])

    quotes = extracted.get("quotes", [])
    for q in quotes:
        verify_quote(q, manifest)
    summary["verified_quote_count"] = len(quotes)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Stage 2 AI JSON output against Stage 1 manifest.")
    parser.add_argument("--manifest", required=True, help="Path to Stage 1 manifest.json")
    parser.add_argument("--extracted", required=True, help="Path to Stage 2 AI JSON output")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    extracted = json.loads(Path(args.extracted).read_text(encoding="utf-8"))

    result = verify_extraction(manifest, extracted)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
