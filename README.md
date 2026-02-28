# Golf Drill DB 🏌️

Automatically extract structured golf drills from TikTok and YouTube Shorts.

**Pipeline:** TikTok URL → yt-dlp (audio) → Whisper (transcription) → Claude (extraction) → Supabase (storage)

---

## Setup

### 1. Install system dependencies
```bash
brew install yt-dlp
brew install whisper  # or: pip install openai-whisper
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Create Supabase table
- Go to your Supabase project → SQL Editor
- Paste and run the contents of `schema.sql`

---

## Usage

### Process a single URL
```bash
python process_drill.py https://www.tiktok.com/@meandmygolf/video/7123456789
```

### Process a batch of URLs
```bash
python batch_process.py test_urls.txt
```

### Dry run (preview without processing)
```bash
python batch_process.py test_urls.txt --dry-run
```

### Control delay between requests
```bash
python batch_process.py urls.txt --delay 5
```

---

## Output Example

```
============================================================
Processing: https://www.tiktok.com/@meandmygolf/video/7291657200840272170
============================================================
  Platform: tiktok | Video ID: 7291657200840272170
  ↓ Downloading audio from: ...
  🎙  Transcribing with Whisper (base)...
  ✓ Transcript (842 chars)
  🤖 Extracting drill data via Claude...

  ✅ Saved: 'Towel Under Arm Drill'
     Category: swing | Level: beginner
     Problems: chicken-wing, impact, follow-through
     Tags: driver, iron, impact, connection, towel
```

---

## Database Schema

| Column | Description |
|---|---|
| `drill_name` | Short memorable name |
| `problem_fixed` | Array of swing issues addressed |
| `category` | swing / short_game / putting / mental / fitness |
| `skill_level` | beginner / intermediate / advanced |
| `steps` | JSON array of step-by-step instructions |
| `equipment_needed` | Props required (towel, alignment stick, etc.) |
| `key_feel` | The main feel/sensation cue |
| `duration_minutes` | Estimated practice time |
| `source_url` | Original video link |
| `creator_handle` | Creator's handle (for attribution) |
| `transcript` | Raw Whisper transcript |
| `tags` | Searchable tags |

---

## Whisper Model Quality

| Model | Speed | Quality |
|---|---|---|
| `tiny` | Fastest | Low |
| `base` | Fast | Good (default) |
| `small` | Medium | Better |
| `medium` | Slow | Great |
| `large` | Slowest | Best |

Set `WHISPER_MODEL=small` in `.env` for better accuracy on technical golf terminology.

---

## Phase Roadmap

- **Phase 1** ✅ — Manual pipeline (single URL, batch)
- **Phase 2** — Auto-discovery (Apify TikTok hashtag scraper, daily cron)
- **Phase 3** — Search UI (Next.js frontend or baappv1 page)

---

## Notes

- Videos are NOT stored — only audio is downloaded temporarily for transcription
- Each video_id is unique — running the same URL twice skips the second
- Creator handles are recorded for attribution
- `quality_score` column is for manual rating (1-5) after review
