# Golf Drill Database — Project Spec
**Status:** Planning  
**Created:** 2026-02-28  
**Channel:** #app-golf

---

## Concept
Scrape TikTok (and YouTube Shorts) for golf drill content → transcribe → AI-extract structured drill data → searchable database. Personal tool first, potential product later.

---

## The Pipeline

```
[TikTok URL or Search Term]
        ↓
[Apify TikTok Scraper / yt-dlp]  ← pulls video + metadata
        ↓
[Whisper]  ← transcribes audio
        ↓
[Claude API]  ← extracts structured drill data from transcript
        ↓
[Supabase]  ← stores structured data
        ↓
[Search UI / baappv1 page]  ← browse + filter drills
```

---

## Phase 1 — Manual Pipeline (Week 1)

Build the core extraction workflow with manual URL input.

### Stack
- **yt-dlp** — download TikTok/YouTube Shorts video (audio only)
- **Whisper (local)** — transcribe audio → text
- **Claude API** — extract structured drill from transcript
- **Supabase** — store drills
- **n8n** — orchestrate the pipeline

### n8n Workflow
1. Webhook receives `{ url: "tiktok.com/..." }`
2. Shell node: `yt-dlp --extract-audio --audio-format mp3 <url>`
3. Whisper node: transcribe mp3 → text
4. HTTP Request → Claude API with extraction prompt
5. Supabase insert → `golf_drills` table

---

## Phase 2 — Auto-Discovery (Week 2)

Search TikTok by hashtag and auto-process new content.

### Discovery Sources
- `#golftips` `#golfdrills` `#golfswing` `#golflesson` `#golfinstruction`
- Key creators: @meandmygolf, @rotaryswing, @chrisryanGolf, @dan_whitttaker

### Tools
- **Apify TikTok Scraper** — search by hashtag, returns video list + metadata
- n8n cron: run daily, deduplicate by video ID, process new ones

---

## Phase 3 — Frontend (Week 3)

Simple search/browse UI. Could be a page in baappv1 or standalone.

### Features
- Search by problem (e.g., "over-the-top", "fat shots", "putting alignment")
- Filter by category, skill level, equipment needed
- Save favorites
- "Drill of the Day" feature
- Link back to original TikTok

---

## Supabase Schema

### `golf_drills` table

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK |
| drill_name | text | e.g., "Towel Drill" |
| problem_fixed | text[] | ["over-the-top", "swing path"] |
| category | text | swing / short_game / putting / mental |
| skill_level | text | beginner / intermediate / advanced |
| steps | jsonb | [{step: 1, instruction: "..."}, ...] |
| equipment_needed | text[] | ["towel", "alignment stick"] |
| key_feel | text | The "feel" cue from the drill |
| duration_minutes | int | Estimated practice time |
| source_platform | text | tiktok / youtube |
| source_url | text | Original video URL |
| creator_handle | text | @meandmygolf |
| creator_name | text | Full name if known |
| transcript | text | Raw Whisper output |
| video_id | text | UNIQUE — for deduplication |
| processed_at | timestamptz | When we extracted it |
| quality_score | int | 1-5 (manual rating later) |
| tags | text[] | searchable tags |

---

## Claude Extraction Prompt

```
You are a golf instruction analyst. Given a transcript from a golf instruction video, extract the following in JSON:

{
  "drill_name": "Short name for the drill",
  "problem_fixed": ["what swing issues this addresses"],
  "category": "swing | short_game | putting | mental | fitness",
  "skill_level": "beginner | intermediate | advanced",
  "steps": [{"step": 1, "instruction": "..."}],
  "equipment_needed": ["any props/tools needed"],
  "key_feel": "The main feel/sensation the golfer should feel",
  "duration_minutes": estimated practice time as integer,
  "tags": ["searchable tags"]
}

If the video is not a golf drill/instruction, return {"not_a_drill": true}.

Transcript:
{transcript}
```

---

## Product Angle (Future)

If this works well for personal use:
- **GolfDrillDB.com** — searchable public database
- Creator attribution baked in (drives traffic back to them, avoids IP issues)
- Monetize: premium filters, personalized drill plans, AI swing coach integration
- Niche: No one has done this at scale for golf yet

---

## Immediate Next Steps

1. [ ] Install yt-dlp locally or on VPS
2. [ ] Create Supabase `golf_drills` table
3. [ ] Build n8n workflow (URL in → drill out → DB insert)
4. [ ] Test with 10 manual URLs
5. [ ] If extraction quality is good → build auto-discovery

---

## Notes
- yt-dlp for personal use is generally fine; don't distribute the videos themselves
- Store transcripts + structured data only — not the actual video files
- Creator attribution on every record (important for product legitimacy)
