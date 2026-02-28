#!/usr/bin/env python3
"""
batch_process.py — Process a list of URLs through the drill pipeline.

Usage:
  python batch_process.py urls.txt
  python batch_process.py test_urls.txt --dry-run
"""

import sys
import os
import time
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from process_drill import process_url


def main():
    parser = argparse.ArgumentParser(description="Batch process golf drill URLs")
    parser.add_argument("url_file", help="Text file with one URL per line")
    parser.add_argument("--dry-run", action="store_true", help="Show URLs without processing")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between requests (default: 3)")
    args = parser.parse_args()

    url_file = Path(args.url_file)
    if not url_file.exists():
        print(f"Error: File not found: {url_file}")
        sys.exit(1)

    urls = [
        line.strip()
        for line in url_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        print("No URLs found in file")
        sys.exit(0)

    print(f"Found {len(urls)} URLs to process")
    if args.dry_run:
        print("\n[DRY RUN] Would process:")
        for i, url in enumerate(urls, 1):
            print(f"  {i:3}. {url}")
        return

    results = {"success": 0, "skipped": 0, "failed": 0}
    failed_urls = []

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] ", end="")
        try:
            success = process_url(url)
            if success:
                results["success"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            print(f"  ❌ Unhandled error: {e}")
            results["failed"] += 1
            failed_urls.append(url)

        # Polite delay between requests
        if i < len(urls):
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
