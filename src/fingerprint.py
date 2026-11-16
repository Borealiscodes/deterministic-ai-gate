#!/usr/bin/env python3
"""Stage 1: Anchor & Fingerprint Inputs (Zero External Dependencies)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_manifest(file_path: str | Path, author: str, out_path: str | Path | None = None) -> dict:
    source = Path(file_path)
    raw_text = source.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    manifest = {
        "schema": "deterministic-ai-gate-manifest-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(source),
        "author": author,
        "full_sha256": sha256_text(raw_text),
        "chunk_count": len(paragraphs),
        "chunks": [
            {
                "index": idx,
                "sha256": sha256_text(paragraph),
                "text": paragraph,
            }
            for idx, paragraph in enumerate(paragraphs)
        ],
    }

    if out_path is not None:
        Path(out_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fingerprint a source document into a SHA-256 manifest.")
    parser.add_argument("file", help="Path to the UTF-8 source text file")
    parser.add_argument("--author", default="unknown", help="Author or custodian name")
    parser.add_argument("--out", default="manifest.json", help="Output JSON manifest path")
    args = parser.parse_args()

    manifest = create_manifest(args.file, author=args.author, out_path=args.out)
    print(f"Anchored {manifest['chunk_count']} chunks -> {args.out} (sha256={manifest['full_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
