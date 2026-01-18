# Video Generation Workflow

## Complete Pipeline - 5 Step Process

Your FastAPI now has **5 separate endpoints** for each stage of video generation:

```
Article Text
    ↓
1. POST /api/prompts              → Generate prompts (30-60s)
    ↓
2. POST /api/create_video         → Generate 10s videos (12-30 min for 6 clips)
    ↓
3. POST /api/combine_videos       → Concatenate into 1 min video (instant)
    ↓
4. POST /api/create_voice         → Generate voiceover (30-60s)
    ↓
5. POST /api/merge_final          → Merge audio + video (instant)
    ↓
Final Video with Voiceover!
```

## Setup

1. **Install dependencies:**
```bash
cd video_generator
pip install -r requirements.txt
```

2. **Configure API keys:**
```bash
cp config.env.example config.env
# Edit config.env and add:
# ANTHROPIC_API_KEY=your_key
# KIE_API_KEY=your_key
```

3. **Start the server:**
```bash
python -m api.main
# Or: uvicorn api.main:app --reload --port 8000
```

Server runs at: `http://localhost:8000`

**View API docs:** `http://localhost:8000/docs`

---

## Step-by-Step API Usage

### Step 1: Generate Prompts

**POST** `/api/prompts`

Submit your article text to generate video prompts.

**Request:**
```bash
curl -X POST http://localhost:8000/api/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Iran faces its largest protests since 2022...",
    "num_shots": 6,
    "clip_duration": 10
  }'
```

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "pending",
  "message": "Prompt generation started. This will take 30-60 seconds.",
  "status_url": "/api/jobs/20260111_143022_a3f8d9c2"
}
```

**Poll for completion:**
```bash
curl http://localhost:8000/api/jobs/20260111_143022_a3f8d9c2
```

**When complete, you'll get:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "completed",
  "result": {
    "prompts_file": "./jobs/20260111_143022_a3f8d9c2/prompts.json",
    "title": "Iran Protests Escalate",
    "num_shots": 6,
    "total_duration": 60,
    "voice_reader_text": "Iran faces its largest protests..."
  }
}
```

**Save the `prompts_file` path for next step!**

---

### Step 2: Generate Videos

**POST** `/api/create_video`

Generate all 10-second video clips (takes ~12-30 minutes total).

**Request:**
```bash
curl -X POST http://localhost:8000/api/create_video \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "20260111_143022_a3f8d9c2",
    "prompts_file": "./jobs/20260111_143022_a3f8d9c2/prompts.json"
  }'
```

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "pending",
  "message": "Video generation started. This takes 2-5 minutes per video.",
  "status_url": "/api/jobs/20260111_143022_a3f8d9c2"
}
```

**Poll for progress:**
```bash
# Check every 30 seconds
curl http://localhost:8000/api/jobs/20260111_143022_a3f8d9c2
```

**Progress updates:**
```json
{
  "status": "processing",
  "message": "Generated 3/6 videos",
  "progress": {
    "videos_completed": 3,
    "videos_total": 6
  }
}
```

**When complete:**
```json
{
  "status": "completed",
  "message": "Generated 6 videos",
  "result": {
    "videos": [
      {
        "job_id": "20260111_143022_a3f8d9c2",
        "shot_number": 1,
        "video_path": "./jobs/.../01_opening_shot.mp4"
      },
      ...
    ]
  }
}
```

---

### Step 3: Combine Videos

**POST** `/api/combine_videos`

Concatenate all 10s clips into a single 1-minute video.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/combine_videos?job_id=20260111_143022_a3f8d9c2"
```

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "completed",
  "concatenated_video_path": "./jobs/20260111_143022_a3f8d9c2/concatenated.mp4",
  "message": "Videos concatenated successfully"
}
```

**Save the `concatenated_video_path` for the final step!**

---

### Step 4: Generate Voiceover

**POST** `/api/create_voice`

Generate voiceover audio from the article summary.

**Request:**
```bash
curl -X POST http://localhost:8000/api/create_voice \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "20260111_143022_a3f8d9c2",
    "text": "Iran faces its largest protests since 2022...",
    "voice": "Bill"
  }'
```

**Note:** The `text` field should be the `voice_reader_text` from Step 1.

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "pending",
  "message": "Voiceover generation started. This takes 30-60 seconds.",
  "status_url": "/api/jobs/20260111_143022_a3f8d9c2"
}
```

**When complete:**
```json
{
  "status": "completed",
  "result": {
    "job_id": "20260111_143022_a3f8d9c2",
    "audio_path": "./jobs/20260111_143022_a3f8d9c2/voiceover.mp3"
  }
}
```

**Save the `audio_path` for the final step!**

---

### Step 5: Merge Final Video

**POST** `/api/merge_final`

Merge voiceover audio with the concatenated video.

**Request:**
```bash
curl -X POST http://localhost:8000/api/merge_final \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "20260111_143022_a3f8d9c2",
    "video_path": "./jobs/20260111_143022_a3f8d9c2/concatenated.mp4",
    "audio_path": "./jobs/20260111_143022_a3f8d9c2/voiceover.mp3"
  }'
```

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "final_video_path": "./jobs/20260111_143022_a3f8d9c2/final.mp4",
  "status": "completed"
}
```

**🎉 Done! Your final video is ready!**

---

## Frontend Integration Example

### JavaScript/React

```javascript
const API_BASE = 'http://localhost:8000';

async function generateVideo(articleText) {
  // Step 1: Generate prompts
  const step1 = await fetch(`${API_BASE}/api/prompts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      article_text: articleText,
      num_shots: 6,
      clip_duration: 10
    })
  });

  const { job_id, status_url } = await step1.json();
  console.log('Job started:', job_id);

  // Poll for prompts completion
  const promptsResult = await pollUntilComplete(job_id);
  const { prompts_file, voice_reader_text } = promptsResult.result;

  // Step 2: Generate videos
  await fetch(`${API_BASE}/api/create_video`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id, prompts_file })
  });

  await pollUntilComplete(job_id); // Wait for videos

  // Step 3: Combine videos
  const step3 = await fetch(`${API_BASE}/api/combine_videos?job_id=${job_id}`, {
    method: 'POST'
  });
  const { concatenated_video_path } = await step3.json();

  // Step 4: Generate voiceover
  await fetch(`${API_BASE}/api/create_voice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id,
      text: voice_reader_text,
      voice: 'Bill'
    })
  });

  const voiceoverResult = await pollUntilComplete(job_id);
  const { audio_path } = voiceoverResult.result;

  // Step 5: Merge final
  const step5 = await fetch(`${API_BASE}/api/merge_final`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id,
      video_path: concatenated_video_path,
      audio_path
    })
  });

  const { final_video_path } = await step5.json();
  console.log('✅ Final video:', final_video_path);

  return final_video_path;
}

async function pollUntilComplete(jobId) {
  while (true) {
    const response = await fetch(`${API_BASE}/api/jobs/${jobId}`);
    const data = await response.json();

    if (data.status === 'completed') return data;
    if (data.status === 'failed') throw new Error(data.error);

    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5s
  }
}
```

---

## Debugging Tips

### Check Job Status
```bash
curl http://localhost:8000/api/jobs/YOUR_JOB_ID
```

### List All Jobs
```bash
curl http://localhost:8000/api/jobs
```

### Check Output Files
```bash
ls -la jobs/YOUR_JOB_ID/
# You should see:
# - prompts.json
# - 01_shot_name.mp4, 02_shot_name.mp4, etc.
# - concatenated.mp4
# - voiceover.mp3
# - final.mp4
```

### Common Issues

**"ANTHROPIC_API_KEY not set"**
→ Add your key to `config.env`

**"KIE_API_KEY not set"**
→ Add your key to `config.env`

**"FFmpeg not found"**
→ Install FFmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)

**"Prompts file not found"**
→ Use the exact `prompts_file` path from Step 1 response

**Videos taking too long**
→ Each 10s video takes 2-5 minutes. For 6 videos, expect 12-30 minutes total.

---

## API Endpoints Summary

| Endpoint | Method | Purpose | Time |
|----------|--------|---------|------|
| `/api/prompts` | POST | Generate video prompts | 30-60s |
| `/api/create_video` | POST | Generate all video clips | 12-30 min |
| `/api/combine_videos` | POST | Concatenate videos | <5s |
| `/api/create_voice` | POST | Generate voiceover | 30-60s |
| `/api/merge_final` | POST | Merge audio + video | <5s |
| `/api/jobs/{job_id}` | GET | Check job status | instant |
| `/api/jobs` | GET | List all jobs | instant |

**Total time:** ~15-35 minutes for complete pipeline

---

## What's Working

✅ All 5 pipeline steps as separate endpoints
✅ Background task processing
✅ Job status tracking
✅ File-based storage in `./jobs/`
✅ CORS enabled for frontend
✅ Auto-generated API docs at `/docs`

## Architecture

```
video_generator/
├── api/
│   └── main.py              # FastAPI app with all endpoints
├── src/
│   ├── config.py            # Configuration
│   ├── models.py            # Request/response models
│   ├── storage.py           # File management
│   └── services/
│       ├── prompt_service.py    # Step 1: Article → Prompts
│       ├── video_service.py     # Step 2: Prompts → Videos
│       ├── tts_service.py       # Step 4: Text → Audio
│       ├── merge_service.py     # Steps 3 & 5: Merge operations
│       └── kie_client.py        # Shared KIE API client
├── jobs/                    # Output files (auto-created)
├── config.env               # Your API keys
└── requirements.txt         # Dependencies
```

Each step is **independent** - perfect for debugging! 🎯
