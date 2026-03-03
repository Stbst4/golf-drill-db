#!/usr/bin/env python3
"""
process_drill.py — Golf Drill Pipeline
Takes a TikTok or YouTube Shorts URL and:
  1. Downloads audio with yt-dlp
  2. Transcribes with Whisper
  3. Extracts structured drill data via Claude API
  4. Inserts into Supabase golf_drills table

Usage:
  python process_drill.py <url>
  python process_drill.py https://www.tiktok.com/@meandmygolf/video/7123456789
"""

import sys
import os
import json
import subprocess
import tempfile
import re
import glob
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
import anthropic
from supabase import create_client, Client

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
CLAUDE_MODEL = "claude-3-haiku-20240307"  # cheap + fast

EXTRACTION_PROMPT = """You are a golf instruction analyst. Given a transcript from a golf instruction video, extract structured drill data as JSON.

Return ONLY valid JSON matching this exact schema:
{
  "drill_name": "Short memorable name for the drill (3-6 words)",
  "problem_fixed": ["list of swing issues this addresses, e.g. over-the-top, casting, chicken-wing, fat-shots, thin-shots, slice, hook, putting-yips, short-game-inconsistency"],
  "category": "one of: swing | short_game | putting | mental | fitness",
  "skill_level": "one of: beginner | intermediate | advanced",
  "steps": [{"step": 1, "instruction": "Clear, actionable step"}],
  "equipment_needed": ["any props needed, e.g. alignment stick, towel, impact bag, or 'none'"],
  "key_feel": "The main feel or sensation the golfer should focus on during the drill",
  "duration_minutes": 5,
  "tags": ["searchable tags, e.g. driver, iron, putting, impact, tempo, grip, alignment"]
}

If the video is NOT a golf drill or instruction (it's just entertainment, a highlight, a course vlog, etc.), return exactly:
{"not_a_drill": true}

Transcript:
{transcript}"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def extract_video_id(url: str) -> tuple[str, str]:
    """Returns (platform, video_id) from a TikTok or YouTube URL."""
    # TikTok: tiktok.com/@user/video/1234567890
    tiktok_match = re.search(r'tiktok\.com/@[^/]+/video/(\d+)', url)
    if tiktok_match:
        return "tiktok", tiktok_match.group(1)

    # YouTube Shorts: youtube.com/shorts/VIDEO_ID or youtu.be/VIDEO_ID
    yt_match = re.search(r'(?:youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if yt_match:
        return "youtube", yt_match.group(1)

    # Fallback: use URL hash
    import hashlib
    return "unknown", hashlib.md5(url.encode()).hexdigest()[:16]


def check_already_processed(supabase: Client, video_id: str) -> bool:
    """Check if this video_id already exists in the DB."""
    result = supabase.table("golf_drills").select("id").eq("video_id", video_id).execute()
    return len(result.data) > 0


def download_audio(url: str, output_dir: str) -> str:
    """Download audio-only from URL using yt-dlp. Returns path to mp3."""
    print(f"  ↓ Downloading audio from: {url}")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--output", os.path.join(output_dir, "%(id)s.%(ext)s"),
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--cookies-from-browser", "safari",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
    if not mp3_files:
        raise RuntimeError("No mp3 file found after yt-dlp download")
    return mp3_files[0]


def transcribe_audio(audio_path: str, output_dir: str) -> str:
    """Transcribe audio file using Whisper CLI. Returns transcript text."""
    print(f"  🎙  Transcribing with Whisper ({WHISPER_MODEL})...")
    cmd = [
        "whisper",
        audio_path,
        "--model", WHISPER_MODEL,
        "--output_format", "txt",
        "--output_dir", output_dir,
        "--fp16", "False",  # avoid warnings on CPU
        "--language", "en",
        "--verbose", "False"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Whisper failed: {result.stderr}")

    # Find the .txt output file
    base = Path(audio_path).stem
    txt_file = os.path.join(output_dir, base + ".txt")
    if not os.path.exists(txt_file):
        txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
        if not txt_files:
            raise RuntimeError("No transcript file found after Whisper")
        txt_file = txt_files[0]

    with open(txt_file, "r") as f:
        transcript = f.read().strip()

    if not transcript:
        raise RuntimeError("Whisper produced empty transcript")

    print(f"  ✓ Transcript ({len(transcript)} chars)")
    return transcript


def extract_drill_data(transcript: str) -> dict | None:
    """Call Claude to extract structured drill data from transcript."""
    print("  🤖 Extracting drill data via Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.replace("{transcript}", transcript[:8000])  # cap at 8k chars
        }]
    )

    response_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if response_text.startswith("```"):
        response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
        response_text = re.sub(r'\n?```$', '', response_text)

    data = json.loads(response_text)

    if data.get("not_a_drill"):
        print("  ⚠  Not a golf drill — skipping")
        return None

    return data


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug


def insert_to_supabase(supabase: Client, drill_data: dict, url: str, platform: str, video_id: str, transcript: str, pro_golfer: str | None = None) -> dict:
    """Insert drill record into Supabase."""
    record = {
        "drill_name": drill_data.get("drill_name", "Unnamed Drill"),
        "problem_fixed": drill_data.get("problem_fixed", []),
        "category": drill_data.get("category"),
        "skill_level": drill_data.get("skill_level"),
        "steps": drill_data.get("steps", []),
        "equipment_needed": drill_data.get("equipment_needed", []),
        "key_feel": drill_data.get("key_feel"),
        "duration_minutes": drill_data.get("duration_minutes"),
        "source_platform": platform if platform in ("tiktok", "youtube") else None,
        "source_url": url,
        "transcript": transcript,
        "video_id": video_id,
        "tags": drill_data.get("tags", []),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Pro golfer metadata
    if pro_golfer:
        # Store in dedicated columns if they exist (post-migration)
        record["is_professional"] = True
        record["pro_golfer"] = pro_golfer
        record["pro_golfer_slug"] = slugify(pro_golfer)
        # Also store as tag for pre-migration compatibility
        if f"pro:{pro_golfer}" not in record["tags"]:
            record["tags"].append(f"pro:{pro_golfer}")
        record["creator_name"] = pro_golfer

    try:
        result = supabase.table("golf_drills").insert(record).execute()
        return result.data[0]
    except Exception as e:
        # If insert fails due to missing columns (pre-migration), retry without them
        if "is_professional" in str(e) or "pro_golfer" in str(e):
            print("  ⚠ Pro golfer columns not in DB yet — storing in tags only")
            record.pop("is_professional", None)
            record.pop("pro_golfer", None)
            record.pop("pro_golfer_slug", None)
            result = supabase.table("golf_drills").insert(record).execute()
            return result.data[0]
        raise


# ─── Main ─────────────────────────────────────────────────────────────────────

def process_url(url: str, pro_golfer: str | None = None) -> bool:
    """Process a single URL through the full pipeline. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"Processing: {url}")
    if pro_golfer:
        print(f"  Pro Golfer: {pro_golfer}")
    print('='*60)

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    platform, video_id = extract_video_id(url)
    print(f"  Platform: {platform} | Video ID: {video_id}")

    # Deduplication check
    if check_already_processed(supabase, video_id):
        print("  ✓ Already in database — skipping")
        return True

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # 1. Download audio
            audio_path = download_audio(url, tmpdir)

            # 2. Transcribe
            transcript = transcribe_audio(audio_path, tmpdir)

            # 3. Extract drill data
            drill_data = extract_drill_data(transcript)
            if drill_data is None:
                return False  # not a drill

            # 4. Insert to Supabase
            record = insert_to_supabase(supabase, drill_data, url, platform, video_id, transcript, pro_golfer=pro_golfer)
            print(f"\n  ✅ Saved: '{record['drill_name']}'")
            print(f"     Category: {record.get('category')} | Level: {record.get('skill_level')}")
            if pro_golfer:
                print(f"     Pro: {pro_golfer}")
            print(f"     Problems: {', '.join(record.get('problem_fixed', []))}")
            print(f"     Tags: {', '.join(record.get('tags', []))}")
            return True

        except Exception as e:
            print(f"\n  ❌ Error: {e}")
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python process_drill.py <url>")
        print("Example: python process_drill.py https://www.tiktok.com/@meandmygolf/video/7123456789")
        sys.exit(1)

    url = sys.argv[1]
    success = process_url(url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
