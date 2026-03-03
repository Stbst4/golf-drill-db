#!/usr/bin/env python3
"""
batch_process.py — Process a list of URLs through the drill pipeline.

Supports two input formats:
  1. Plain text (.txt) — one URL per line, lines starting with # are ignored
  2. JSONL (.jsonl) — one JSON object per line with at least {"url": "..."} 
     Optional fields: pro_golfer, title

Usage:
  python batch_process.py urls.txt
  python batch_process.py pro_videos.jsonl
  python batch_process.py test_urls.txt --dry-run
  python batch_process.py pro_videos.jsonl --pro-only
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Lazy import — avoid requiring API keys for --dry-run
_process_url = None

def get_process_url():
    global _process_url
    if _process_url is None:
        from process_drill import process_url as _pu
        _process_url = _pu
    return _process_url


def load_urls_txt(filepath: Path) -> list[dict]:
    """Load plain text URL file. Returns list of {url, pro_golfer?}."""
    entries = []
    for line in filepath.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append({"url": line})
    return entries


def load_urls_jsonl(filepath: Path) -> list[dict]:
    """Load JSONL file with URL + optional metadata. Returns list of dicts."""
    entries = []
    for i, line in enumerate(filepath.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
            if "url" not in obj:
                print(f"  ⚠ Line {i}: missing 'url' field, skipping")
                continue
            entries.append(obj)
        except json.JSONDecodeError as e:
            print(f"  ⚠ Line {i}: invalid JSON ({e}), skipping")
    return entries


def load_entries(filepath: Path) -> list[dict]:
    """Load URL entries from .txt or .jsonl file."""
    if filepath.suffix == ".jsonl":
        return load_urls_jsonl(filepath)
    else:
        return load_urls_txt(filepath)


def main():
    parser = argparse.ArgumentParser(description="Batch process golf drill URLs")
    parser.add_argument("url_file", help="Text file (.txt) or JSONL file (.jsonl) with URLs")
    parser.add_argument("--dry-run", action="store_true", help="Show URLs without processing")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between requests (default: 3)")
    parser.add_argument("--pro-only", action="store_true", help="Only process entries with pro_golfer set")
    parser.add_argument("--golfer", type=str, help="Only process entries for this specific pro golfer")
    parser.add_argument("--limit", type=int, help="Max number of URLs to process")
    args = parser.parse_args()

    url_file = Path(args.url_file)
    if not url_file.exists():
        print(f"Error: File not found: {url_file}")
        sys.exit(1)

    entries = load_entries(url_file)

    # Filter by pro golfer if requested
    if args.pro_only:
        entries = [e for e in entries if e.get("pro_golfer")]
    if args.golfer:
        entries = [e for e in entries if args.golfer.lower() in e.get("pro_golfer", "").lower()]

    # Apply limit
    if args.limit:
        entries = entries[:args.limit]

    if not entries:
        print("No URLs found to process")
        sys.exit(0)

    # Show pro golfer breakdown
    pros = {}
    for e in entries:
        pro = e.get("pro_golfer", "Unknown/Community")
        pros[pro] = pros.get(pro, 0) + 1
    
    print(f"Found {len(entries)} URLs to process")
    if any(e.get("pro_golfer") for e in entries):
        print(f"\nPro Golfer Breakdown:")
        for pro, count in sorted(pros.items(), key=lambda x: -x[1]):
            print(f"  {pro}: {count} videos")

    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for i, entry in enumerate(entries, 1):
            pro = entry.get("pro_golfer", "")
            title = entry.get("title", "")
            label = f" [{pro}]" if pro else ""
            desc = f" — {title}" if title else ""
            print(f"  {i:3}.{label} {entry['url']}{desc}")
        return

    results = {"success": 0, "skipped": 0, "failed": 0}
    failed_urls = []

    for i, entry in enumerate(entries, 1):
        url = entry["url"]
        pro_golfer = entry.get("pro_golfer")
        print(f"\n[{i}/{len(entries)}] ", end="")
        try:
            success = get_process_url()(url, pro_golfer=pro_golfer)
            if success:
                results["success"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            print(f"  ❌ Unhandled error: {e}")
            results["failed"] += 1
            failed_urls.append(url)

        # Polite delay between requests
        if i < len(entries):
            time.sleep(args.delay)

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  ✅ Success:  {results['success']}")
    print(f"  ⚠  Skipped:  {results['skipped']} (not a drill or duplicate)")
    print(f"  ❌ Failed:   {results['failed']}")

    if failed_urls:
        failed_file = "failed_urls.txt"
        Path(failed_file).write_text("\n".join(failed_urls))
        print(f"\nFailed URLs saved to {failed_file}")


if __name__ == "__main__":
    main()
