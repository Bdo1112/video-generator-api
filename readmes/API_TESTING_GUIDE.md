# Video Generator API - Testing Guide

This guide provides step-by-step instructions for testing each API endpoint.

## Prerequisites

1. **Start the server:**
   ```bash
   cd /Users/brianoh/Dev/01_Personal/01_Youtube/02_prompt_builder/video_generator
   python3 -m uvicorn api.main:app --reload --port 8000
   ```

2. **Check server is running:**
   ```
   GET http://localhost:8000/
   ```
   Should return: `{"service": "Video Generator API", "version": "1.0.0", "status": "running"}`

---

## Directory Structure

After running the pipeline, files are organized as:

```
jobs/
└── {job_id}/              # e.g., Tesla_Battery_News
    ├── prompts/           # Prompts JSON and metadata
    ├── videos/            # Individual shots + concatenated video
    ├── audio/             # Voiceover audio
    └── final/             # Final merged video
```

---

## Testing Workflow

There are two ways to use the API:

### Option A: Full Pipeline (Recommended for Testing)
Use one endpoint that does everything automatically.

### Option B: Step-by-Step
Test each step individually for debugging and control.

---

## Option A: Full Pipeline Testing

### Endpoint: Generate Full Video
**POST** `http://localhost:8000/api/generate_full_video`

**Request Body:**
```json
{
  "article_text": "Tesla announces breakthrough in battery technology. The new 4680 cells promise 50% more range and faster charging times for all future vehicles.",
  "title": "Tesla Battery News",
  "num_shots": 2,
  "clip_duration": 10
}
```

**What it does:**
- Generates prompts from article
- Generates 2 videos (10 seconds each)
- Concatenates videos into 20-second video
- Creates voiceover audio
- Merges video with audio
- **Total time:** 5-15 minutes (depending on video generation)

**Response:**
```json
{
  "job_id": "Tesla_Battery_News",
  "status": "pending",
  "message": "Full pipeline started. Check status at /api/jobs/Tesla_Battery_News",
  "status_url": "/api/jobs/Tesla_Battery_News"
}
```

**Check Progress:**
```
GET http://localhost:8000/api/jobs/Tesla_Battery_News
```

**Important Notes:**
- ✅ **Retry-safe:** If it fails, run the same request again - it will skip completed steps
- ✅ **Deterministic job_id:** Same title = same job_id = same folder
- ✅ Uses smart retry logic at every stage

---

## Option B: Step-by-Step Testing

Use this approach when you want fine-grained control over each step.

### Step 1: Generate Prompts

**POST** `http://localhost:8000/api/prompts/sync`

**Request Body:**
```json
{
  "article_text": "SpaceX successfully launches 50th Starship test flight. The massive rocket lifted off from Boca Chica, Texas this morning, marking a milestone in the company's rapid iteration approach.",
  "title": "SpaceX Test 50",
  "num_shots": 2,
  "clip_duration": 10
}
```

**What it does:**
- Analyzes article with Claude API
- Generates video prompts for each shot
- Creates voiceover script (~120 words for 60 seconds)
- Saves to: `jobs/SpaceX_Test_50/prompts/`

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "completed",
  "prompts_file": "jobs/SpaceX_Test_50/prompts/SpaceX_Test_50_..._prompts.json",
  "title": "SpaceX Starship Reaches Historic 50th Test Flight",
  "num_shots": 2,
  "total_duration": 20,
  "voice_reader_text": "SpaceX successfully launches..."
}
```

**Time:** ~30-60 seconds

---

### Step 2: Generate Videos

**POST** `http://localhost:8000/api/create_video`

**Request Body:**
```json
{
  "job_id": "SpaceX_Test_50"
}
```

**What it does:**
- Reads prompts from `jobs/SpaceX_Test_50/prompts/`
- Generates videos via Sora-2 API
- Saves to: `jobs/SpaceX_Test_50/videos/`
- **Retry logic:** Skips videos that already exist

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "pending",
  "message": "Video generation started. This takes 2-5 minutes per video.",
  "status_url": "/api/jobs/SpaceX_Test_50"
}
```

**Check Progress:**
```
GET http://localhost:8000/api/jobs/SpaceX_Test_50
```

**Progress Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "processing",
  "message": "Generated 1/2 videos",
  "progress": {
    "videos_completed": 1,
    "videos_total": 2
  }
}
```

**Time:** ~2-5 minutes per video (4-10 minutes for 2 videos)

**Generated Files:**
- `jobs/SpaceX_Test_50/videos/01_rocket_launch.mp4`
- `jobs/SpaceX_Test_50/videos/02_starship_flight.mp4`

---

### Step 3: Combine Videos

**POST** `http://localhost:8000/api/combine_videos`

**Request Body:**
```json
{
  "job_id": "SpaceX_Test_50"
}
```

**What it does:**
- Concatenates all individual videos using FFmpeg
- Saves to: `jobs/SpaceX_Test_50/videos/concatenated.mp4`
- **Retry logic:** Skips if concatenated video already exists

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "completed",
  "concatenated_video_path": "jobs/SpaceX_Test_50/videos/concatenated.mp4",
  "message": "Videos concatenated successfully"
}
```

**Time:** ~5-10 seconds

---

### Step 4: Create Voiceover

**POST** `http://localhost:8000/api/create_voice`

**Request Body (auto-load text from prompts):**
```json
{
  "job_id": "SpaceX_Test_50",
  "voice": "Bill"
}
```

**OR provide text manually:**
```json
{
  "job_id": "SpaceX_Test_50",
  "text": "Custom voiceover text goes here...",
  "voice": "Bill"
}
```

**What it does:**
- Auto-loads voice_reader text from prompts.json (if text not provided)
- Generates audio via KIE TTS API
- Saves to: `jobs/SpaceX_Test_50/audio/voiceover.mp3`
- **Retry logic:** Skips if audio already exists

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "pending",
  "message": "Voiceover generation started",
  "status_url": "/api/jobs/SpaceX_Test_50"
}
```

**Time:** ~30-60 seconds

**Available Voices:**
- Bill
- Nova
- Alloy
- Echo
- Fable
- Onyx
- Shimmer

---

### Step 5: Merge Final Video

**POST** `http://localhost:8000/api/merge_final`

**Request Body:**
```json
{
  "job_id": "SpaceX_Test_50"
}
```

**What it does:**
- Auto-detects concatenated video and voiceover audio
- Merges them using FFmpeg
- Saves to: `jobs/SpaceX_Test_50/final/final.mp4`
- **Retry logic:** Skips if final video already exists

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "completed",
  "final_video_path": "jobs/SpaceX_Test_50/final/final.mp4"
}
```

**Time:** ~5-10 seconds

---

## Download Videos

### Download Final Video

**GET** `http://localhost:8000/api/download/SpaceX_Test_50?video_type=final`

Downloads: `jobs/SpaceX_Test_50/final/final.mp4`

### Download Concatenated Video (no audio)

**GET** `http://localhost:8000/api/download/SpaceX_Test_50?video_type=concatenated`

Downloads: `jobs/SpaceX_Test_50/videos/concatenated.mp4`

### Download Individual Shots

**GET** `http://localhost:8000/api/download/SpaceX_Test_50?video_type=shot_1`

**GET** `http://localhost:8000/api/download/SpaceX_Test_50?video_type=shot_2`

Downloads individual video clips.

---

## Check Job Status

**GET** `http://localhost:8000/api/jobs/{job_id}`

**Example:**
```
GET http://localhost:8000/api/jobs/SpaceX_Test_50
```

**Response:**
```json
{
  "job_id": "SpaceX_Test_50",
  "status": "completed",
  "message": "Final video created",
  "progress": null,
  "result": {...},
  "error": null
}
```

**Status Values:**
- `pending` - Job queued
- `processing` - Currently running
- `completed` - Successfully finished
- `failed` - Error occurred (check `error` field)

---

## Cleanup Old Jobs

**POST** `http://localhost:8000/api/cleanup?days_old=7`

**What it does:**
- Deletes jobs older than 7 days
- Frees up disk space
- Deletes entire job folder (all stages)

**Response:**
```json
{
  "message": "Cleaned up 3 job(s) older than 7 days",
  "deleted_count": 3
}
```

---

## Retry Logic & Idempotency

All endpoints are **retry-safe**! If any step fails, you can re-run it without starting over.

### How Retry Works:

1. **Prompts:** Only `/api/generate_full_video` checks if prompts exist
   - `/api/prompts` always regenerates

2. **Videos:** Checks if each video file exists before generating
   - Skips existing videos
   - Only generates missing ones

3. **Audio:** Checks if voiceover.mp3 exists
   - Skips if already generated

4. **Concatenation:** Checks if concatenated.mp4 exists
   - Skips if already created

5. **Final Merge:** Checks if final.mp4 exists
   - Skips if already merged

### Example Retry Scenario:

```
1. Start full pipeline for "Tesla_Battery_News"
2. Prompts ✅ generated
3. Video 1 ✅ generated
4. Video 2 ❌ failed (API timeout)
5. Re-run same request
6. Prompts ✅ skipped (already exist)
7. Video 1 ✅ skipped (already exists)
8. Video 2 ✅ regenerated (was missing)
9. Continue with concatenation, audio, merge
```

---

## Common Issues & Solutions

### Issue: "Prompts file not found"
**Solution:** Run Step 1 (Generate Prompts) first, or use `/api/generate_full_video`

### Issue: "No videos found for job"
**Solution:** Run Step 2 (Generate Videos) first

### Issue: "Video not found" or "Audio not found"
**Solution:** Ensure previous steps completed successfully. Check job status.

### Issue: "Address already in use" (port 8000)
**Solution:**
```bash
lsof -ti:8000 | xargs kill -9
# Then restart server
```

### Issue: Videos generating slowly
**Expected:** Sora-2 API takes 2-5 minutes per video. This is normal.

### Issue: Server paths showing "/api/jobs" error
**Solution:** Server must be started from the `video_generator` directory:
```bash
cd /Users/brianoh/Dev/01_Personal/01_Youtube/02_prompt_builder/video_generator
python3 -m uvicorn api.main:app --reload --port 8000
```

---

## Configuration

Edit `video_generator/config.env` to change:

- Video model: `VIDEO_API_MODEL=sora-2-text-to-video`
- Video aspect ratio: `VIDEO_ASPECT_RATIO=portrait`
- TTS voice: `TTS_VOICE=Bill`
- Number of shots: `DEFAULT_NUM_SHOTS=6`
- Clip duration: `DEFAULT_CLIP_DURATION=10`

---

## API Documentation

FastAPI automatically generates interactive API docs:

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

---

## Testing Checklist

### Quick Test (Step-by-Step):
- [ ] Generate prompts for 2 shots
- [ ] Generate 2 videos
- [ ] Combine videos
- [ ] Create voiceover
- [ ] Merge final video
- [ ] Download final video

### Full Pipeline Test:
- [ ] Run `/api/generate_full_video` with 2 shots
- [ ] Poll status until completed
- [ ] Download final video
- [ ] Verify video has audio

### Retry Test:
- [ ] Start full pipeline
- [ ] Kill server mid-process
- [ ] Restart server
- [ ] Re-run same request
- [ ] Verify it skips completed steps

### Cleanup Test:
- [ ] Create test job
- [ ] Run cleanup endpoint
- [ ] Verify old jobs deleted

---

## Performance Expectations

| Step | Time | Notes |
|------|------|-------|
| Prompts | 30-60s | Claude API call |
| Videos (per video) | 2-5 min | Sora-2 API (slowest step) |
| Concatenate | 5-10s | FFmpeg |
| Voiceover | 30-60s | KIE TTS API |
| Final Merge | 5-10s | FFmpeg |
| **Total (2 videos)** | **5-15 min** | Mostly video generation |
| **Total (6 videos)** | **15-35 min** | Mostly video generation |

---

## Tips

1. **Use short titles** - They become job_id folder names
2. **Start with 2 shots** - Faster for testing (20 seconds total)
3. **Use `/api/generate_full_video`** - Easiest way to test end-to-end
4. **Check logs** - Server prints detailed progress messages
5. **Poll job status** - Don't wait blindly, check `/api/jobs/{job_id}`
6. **Test retry logic** - Stop mid-process and restart to verify idempotency

---

## Support

For issues or questions, check:
- Server logs in terminal
- Job metadata: `jobs/{job_id}/prompts/metadata.json`
- Generated files in `jobs/{job_id}/` directory
