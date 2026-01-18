# Video Generator API

FastAPI-based video generation service that converts news articles into short-form videos.

## Setup

1. **Install dependencies**
```bash
cd video_generator
pip install -r requirements.txt
```

2. **Configure environment**
```bash
cp config.env.example config.env
# Edit config.env and add your API keys
```

Required API keys:
- `ANTHROPIC_API_KEY` - For Claude API (prompt generation)
- `KIE_API_KEY` - For video generation and TTS

3. **Run the API server**
```bash
python -m api.main
```

Or with uvicorn:
```bash
uvicorn api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Generate Prompts (Background Task)

**POST** `/api/prompts`

Returns immediately with a `job_id`. Poll `/api/jobs/{job_id}` for status.

**Request:**
```json
{
  "article_text": "Iran faces its largest protests since 2022...",
  "num_shots": 6,
  "clip_duration": 10
}
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

### 2. Generate Prompts (Synchronous)

**POST** `/api/prompts/sync`

Waits for completion before returning (takes 30-60 seconds).

**Request:** Same as above

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "completed",
  "prompts_file": "./jobs/20260111_143022_a3f8d9c2/prompts.json",
  "title": "Iran Protests Escalate",
  "num_shots": 6,
  "total_duration": 60,
  "voice_reader_text": "Iran faces its largest protests..."
}
```

### 3. Check Job Status

**GET** `/api/jobs/{job_id}`

Check the status of a background task.

**Response:**
```json
{
  "job_id": "20260111_143022_a3f8d9c2",
  "status": "completed",  // pending | processing | completed | failed
  "message": "Prompts generated successfully",
  "result": {
    "prompts_file": "...",
    "title": "...",
    ...
  }
}
```

### 4. List All Jobs

**GET** `/api/jobs`

Get all jobs with their statuses.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "20260111_143022_a3f8d9c2",
      "status": "completed",
      "title": "Iran Protests Escalate",
      "created_at": "2026-01-11T14:30:22"
    }
  ],
  "count": 1
}
```

## Example: Using the API from Frontend

### JavaScript/TypeScript

```javascript
// 1. Submit article for prompt generation
const response = await fetch('http://localhost:8000/api/prompts', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    article_text: 'Your article text here...',
    num_shots: 6,
    clip_duration: 10
  })
});

const { job_id, status_url } = await response.json();
console.log('Job started:', job_id);

// 2. Poll for status
const checkStatus = async () => {
  const statusResponse = await fetch(`http://localhost:8000${status_url}`);
  const status = await statusResponse.json();

  if (status.status === 'completed') {
    console.log('Prompts generated!', status.result);
    return status.result;
  } else if (status.status === 'failed') {
    console.error('Failed:', status.error);
    return null;
  } else {
    // Still processing, check again in 5 seconds
    setTimeout(checkStatus, 5000);
  }
};

checkStatus();
```

### Python

```python
import requests
import time

# 1. Submit article
response = requests.post('http://localhost:8000/api/prompts', json={
    'article_text': 'Your article text here...',
    'num_shots': 6,
    'clip_duration': 10
})

job_id = response.json()['job_id']
print(f'Job started: {job_id}')

# 2. Poll for status
while True:
    status_response = requests.get(f'http://localhost:8000/api/jobs/{job_id}')
    status = status_response.json()

    if status['status'] == 'completed':
        print('Prompts generated!', status['result'])
        break
    elif status['status'] == 'failed':
        print('Failed:', status['error'])
        break
    else:
        print('Processing...')
        time.sleep(5)
```

### cURL

```bash
# Submit article
curl -X POST http://localhost:8000/api/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "article_text": "Your article text...",
    "num_shots": 6,
    "clip_duration": 10
  }'

# Check status
curl http://localhost:8000/api/jobs/20260111_143022_a3f8d9c2
```

## API Documentation

Once the server is running, view the interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
video_generator/
├── api/
│   ├── main.py              # FastAPI app with endpoints
│   └── routes/              # Future: separate route files
├── src/
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── storage.py           # File storage manager
│   └── services/
│       ├── prompt_service.py   # Article → Prompts (Claude API)
│       ├── kie_client.py       # Shared KIE API client
│       └── ...                 # Future: video, TTS, merge services
├── jobs/                    # Job outputs (created automatically)
├── config.env               # Environment variables
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## What's Working Now

✅ **POST /api/prompts** - Generate prompts from article (background task)
✅ **POST /api/prompts/sync** - Generate prompts (synchronous)
✅ **GET /api/jobs/{job_id}** - Check job status
✅ **GET /api/jobs** - List all jobs

## What's Next

🚧 **POST /api/videos** - Generate video clips from prompts
🚧 **POST /api/voiceover** - Generate voiceover audio
🚧 **POST /api/merge** - Merge audio + video
🚧 **POST /api/pipeline** - Run full pipeline (article → final video)

## Development

```bash
# Run with auto-reload
uvicorn api.main:app --reload --port 8000

# Run tests (when added)
pytest

# Format code
black src/ api/
```

## Notes

- Jobs are stored in `./jobs/{job_id}/` directory
- Each job contains JSON prompts, videos, audio, and metadata
- In-memory job tracking (use Redis for production)
- CORS enabled for all origins (restrict in production)
