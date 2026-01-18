#!/usr/bin/env python3
"""
FastAPI Application
===================
Main FastAPI app with all endpoints
"""

import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.config import config
from src.storage import StorageManager
from src.services.prompt_service import PromptService
from src.services.video_service import VideoService
from src.services.tts_service import TTSService
from src.services.merge_service import MergeService
from src.services.kie_client import KieClient
from src.models import (
    PromptGenerationRequest,
    PromptGenerationResponse,
    VideoGenerationRequest,
    VideoBatchRequest,
    VideoBatchResponse,
    VoiceoverRequest,
    VoiceoverResponse,
    CombineVideosRequest,
    MergeRequest,
    MergeResponse,
    TaskSubmissionResponse,
    JobStatusResponse,
    JobStatus
)

# Initialize storage (shared across all requests)
# Get the base directory (video_generator folder)
import pathlib
import os

# Debug: print what __file__ resolves to
print(f"[startup] __file__ = {__file__}")
print(f"[startup] __file__ resolved = {pathlib.Path(__file__).resolve()}")

# Get absolute path to video_generator directory
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

# Fallback: if BASE_DIR ends up being root or weird path, use hardcoded path
if str(BASE_DIR).startswith('/api') or str(BASE_DIR) == '/':
    # Hardcoded fallback path
    BASE_DIR = pathlib.Path('/Users/brianoh/Dev/01_Personal/01_Youtube/02_prompt_builder/video_generator')
    print(f"[startup] WARNING: Using fallback BASE_DIR")

print(f"[startup] BASE_DIR: {BASE_DIR}")
print(f"[startup] Storage will use: {BASE_DIR}/jobs")

storage = StorageManager(base_dir=str(BASE_DIR))

# Dictionary to track background jobs
# In production, use Redis or a database
jobs = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    print(f"[startup] Video Generator API starting...")
    print(f"[startup] Storage: {storage.jobs_dir}")
    yield
    # Shutdown
    print(f"[shutdown] Video Generator API shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Video Generator API",
    description="Generate short-form videos from news articles using AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allow frontend to call API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# DEPENDENCY INJECTION
# ==============================================================================

def get_kie_client() -> KieClient:
    """Get KieClient instance"""
    return KieClient(api_key=config.KIE_API_KEY)

def get_prompt_service() -> PromptService:
    """Get PromptService instance"""
    return PromptService(storage=storage, anthropic_api_key=config.ANTHROPIC_API_KEY)

def get_video_service() -> VideoService:
    """Get VideoService instance"""
    kie_client = get_kie_client()
    return VideoService(kie_client=kie_client, storage=storage)

def get_tts_service() -> TTSService:
    """Get TTSService instance"""
    kie_client = get_kie_client()
    return TTSService(kie_client=kie_client, storage=storage)

def get_merge_service() -> MergeService:
    """Get MergeService instance"""
    return MergeService(storage=storage)


# ==============================================================================
# BACKGROUND TASK HELPERS
# ==============================================================================

async def generate_prompts_task(job_id: str, request: PromptGenerationRequest):
    """Background task to generate prompts"""
    try:
        # Update status to processing
        jobs[job_id] = {
            "status": JobStatus.PROCESSING,
            "message": "Analyzing article with Claude API..."
        }
        storage.update_job_status(job_id, JobStatus.PROCESSING)

        # Generate prompts
        prompt_service = get_prompt_service()
        result = await prompt_service.generate_prompts(
            article_text=request.article_text,
            title=request.title,
            num_shots=request.num_shots,
            clip_duration=request.clip_duration,
            verbose=True
        )

        # Update status to completed
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "message": "Prompts generated successfully",
            "result": result.model_dump()
        }
        storage.update_job_status(job_id, JobStatus.COMPLETED, result=result.model_dump())

    except Exception as e:
        # Update status to failed
        error_msg = str(e)
        jobs[job_id] = {
            "status": JobStatus.FAILED,
            "message": "Failed to generate prompts",
            "error": error_msg
        }
        storage.update_job_status(job_id, JobStatus.FAILED, error=error_msg)


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Video Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/api/prompts", response_model=TaskSubmissionResponse)
async def create_prompts(
    request: PromptGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate video prompts from article (background task)

    This endpoint returns immediately with a job_id.
    Poll GET /api/jobs/{job_id} to check status.

    To regenerate prompts for an existing job, pass the existing job_id:
    {
        "job_id": "20260111_143022_a3f8d9c2",
        "article_text": "...",
        "num_shots": 6,
        "clip_duration": 10
    }
    The old prompts file will be automatically overwritten.

    Example (new job):
        POST /api/prompts
        {
            "article_text": "Iran faces protests...",
            "num_shots": 6,
            "clip_duration": 10
        }

        Returns:
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "status": "pending",
            "message": "Prompt generation started",
            "status_url": "/api/jobs/20260111_143022_a3f8d9c2"
        }
    """
    # Generate job_id from title (deterministic for retries)
    job_id = storage.generate_job_id(title=request.title)

    # Initialize job status
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "message": "Prompt generation queued"
    }
    storage.update_job_status(job_id, JobStatus.PENDING)

    # Start background task
    background_tasks.add_task(generate_prompts_task, job_id, request)

    return TaskSubmissionResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Prompt generation started. This will take 30-60 seconds.",
        status_url=f"/api/jobs/{job_id}"
    )


@app.post("/api/prompts/sync", response_model=PromptGenerationResponse)
async def create_prompts_sync(request: PromptGenerationRequest):
    """
    Generate video prompts from article (synchronous - waits for completion)

    This endpoint waits for Claude API to finish before returning.
    Takes 30-60 seconds.

    Use this for testing or if you don't want to poll for status.
    Use /api/prompts (background version) for production.
    """
    try:
        prompt_service = get_prompt_service()
        result = await prompt_service.generate_prompts(
            article_text=request.article_text,
            title=request.title,
            num_shots=request.num_shots,
            clip_duration=request.clip_duration,
            verbose=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of a background job

    Poll this endpoint to check if your prompts/videos are ready.

    Example:
        GET /api/jobs/20260111_143022_a3f8d9c2

        Returns:
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "status": "completed",
            "message": "Prompts generated successfully",
            "result": {
                "prompts_file": "...",
                "title": "..."
            }
        }
    """
    # Check in-memory cache first
    if job_id in jobs:
        job_data = jobs[job_id]
        return JobStatusResponse(
            job_id=job_id,
            status=job_data["status"],
            message=job_data.get("message"),
            result=job_data.get("result"),
            error=job_data.get("error")
        )

    # Check storage
    if not storage.job_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    metadata = storage.load_job_metadata(job_id)
    return JobStatusResponse(
        job_id=job_id,
        status=metadata.get("status", JobStatus.PENDING),
        message=metadata.get("message"),
        result=metadata.get("result"),
        error=metadata.get("error")
    )


@app.get("/api/jobs")
async def list_jobs():
    """
    List all jobs

    Returns list of job IDs and their statuses
    """
    import os
    job_dirs = [d for d in os.listdir(storage.jobs_dir) if os.path.isdir(storage.jobs_dir / d)]

    jobs_list = []
    for job_id in job_dirs:
        try:
            metadata = storage.load_job_metadata(job_id)
            jobs_list.append({
                "job_id": job_id,
                "status": metadata.get("status", "unknown"),
                "title": metadata.get("title"),
                "created_at": metadata.get("updated_at")
            })
        except:
            pass

    # Sort by creation time (newest first)
    jobs_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return {"jobs": jobs_list, "count": len(jobs_list)}


@app.post("/api/create_videos", response_model=TaskSubmissionResponse)
async def create_videos(request: VideoBatchRequest, background_tasks: BackgroundTasks):
    """
    Step 2: Generate all 10-second video clips from prompts

    Takes a job_id from /api/prompts and generates all video clips.
    This takes 2-5 minutes per video (so 12-30 minutes for 6 videos).

    Example:
        POST /api/create_videos
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "prompts_file": "./jobs/20260111_143022_a3f8d9c2/prompts.json"
        }
    """
    # Auto-find prompts file if not provided or if it doesn't exist
    if request.prompts_file:
        prompts_path = request.prompts_file
        if not os.path.isabs(prompts_path):
            prompts_path = os.path.join(storage.base_dir, prompts_path)
    else:
        # Auto-detect prompts file from job directory
        prompts_dir = storage.get_job_dir(request.job_id, stage="prompts")
        prompts_files = list(prompts_dir.glob("*_prompts.json"))
        if not prompts_files:
            raise HTTPException(status_code=404, detail=f"No prompts file found for job: {request.job_id}")
        prompts_path = str(prompts_files[0])

    # Verify the resolved path exists
    if not os.path.exists(prompts_path):
        raise HTTPException(status_code=404, detail=f"Prompts file not found: {prompts_path}")

    # Initialize job status
    jobs[request.job_id] = {
        "status": JobStatus.PENDING,
        "message": "Video generation queued"
    }

    # Background task
    async def generate_videos_task(job_id: str, prompts_file: str):
        try:
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Generating videos..."}
            storage.update_job_status(job_id, JobStatus.PROCESSING)

            video_service = get_video_service()
            results = await video_service.generate_videos_from_prompts(
                job_id=job_id,
                prompts_file=prompts_file,
                verbose=True
            )

            jobs[job_id] = {
                "status": JobStatus.COMPLETED,
                "message": f"Generated {len(results)} videos",
                "result": {"videos": [r.model_dump() for r in results]}
            }
            storage.update_job_status(job_id, JobStatus.COMPLETED, videos_generated=len(results))

        except Exception as e:
            jobs[job_id] = {"status": JobStatus.FAILED, "error": str(e)}
            storage.update_job_status(job_id, JobStatus.FAILED, error=str(e))

    background_tasks.add_task(generate_videos_task, request.job_id, prompts_path)

    return TaskSubmissionResponse(
        job_id=request.job_id,
        status=JobStatus.PENDING,
        message="Video generation started. This takes 2-5 minutes per video.",
        status_url=f"/api/jobs/{request.job_id}"
    )


@app.post("/api/combine_videos")
async def combine_videos(request: CombineVideosRequest):
    """
    Step 3: Concatenate all 10-second clips into 1 minute video

    Takes all the individual video clips and combines them into one video.

    Example:
        POST /api/combine_videos
        {
            "job_id": "SpaceX-Test-50"
        }
    """
    try:
        merge_service = get_merge_service()
        concat_path = await merge_service.combine_videos(job_id=request.job_id, verbose=True)

        return {
            "job_id": request.job_id,
            "status": "completed",
            "concatenated_video_path": concat_path,
            "message": "Videos concatenated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create_voice", response_model=TaskSubmissionResponse)
async def create_voiceover(request: VoiceoverRequest, background_tasks: BackgroundTasks):
    """
    Step 4: Generate voiceover audio from text

    Two modes:
    1. Provide text directly: {"job_id": "...", "text": "...", "voice": "Bill"}
    2. Auto-load from prompts.json: {"job_id": "...", "voice": "Bill"}

    If text is not provided, it will automatically load the voice_reader text
    from the job's prompts.json file.

    Example 1 (with text):
        POST /api/create_voice
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "text": "Iran faces its largest protests...",
            "voice": "Bill"
        }

    Example 2 (auto-load from prompts.json):
        POST /api/create_voice
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "voice": "Bill"
        }
    """
    job_id = request.job_id

    # If text not provided, load from prompts.json
    if not request.text:
        # Find prompts.json file for this job in the prompts directory
        job_dir = storage.get_job_dir(job_id, stage="prompts")
        prompts_files = list(job_dir.glob("*_prompts.json"))

        if not prompts_files:
            raise HTTPException(
                status_code=404,
                detail=f"No prompts.json found for job {job_id}. Either provide text or generate prompts first."
            )

        # Load the first prompts file
        prompts_data = storage.load_prompts_json(str(prompts_files[0]))
        text_to_use = prompts_data.get("metadata", {}).get("voice_reader")

        if not text_to_use:
            raise HTTPException(
                status_code=400,
                detail=f"No voice_reader text found in prompts.json for job {job_id}"
            )
    else:
        text_to_use = request.text

    # Initialize job status
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "message": "Voiceover generation queued"
    }

    # Background task
    async def generate_voiceover_task(job_id: str, text: str, voice: str):
        try:
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Generating voiceover..."}

            tts_service = get_tts_service()
            result = await tts_service.generate_voiceover(
                job_id=job_id,
                text=text,
                voice=voice,
                verbose=True
            )

            jobs[job_id] = {
                "status": JobStatus.COMPLETED,
                "message": "Voiceover generated",
                "result": result.model_dump()
            }

        except Exception as e:
            jobs[job_id] = {"status": JobStatus.FAILED, "error": str(e)}

    background_tasks.add_task(generate_voiceover_task, job_id, text_to_use, request.voice or config.TTS_VOICE)

    return TaskSubmissionResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Voiceover generation started. This takes 30-60 seconds.",
        status_url=f"/api/jobs/{job_id}"
    )


@app.post("/api/merge_final", response_model=MergeResponse)
async def merge_final_video(request: MergeRequest):
    """
    Step 5: Merge voiceover audio with concatenated video

    Final step - combines the 1-minute video with the voiceover audio.

    Example:
        POST /api/merge_final
        {
            "job_id": "20260111_143022_a3f8d9c2",
            "video_path": "./jobs/.../concatenated.mp4",
            "audio_path": "./jobs/.../voiceover.mp3"
        }
    """
    try:
        merge_service = get_merge_service()
        result = await merge_service.merge_final_video(
            job_id=request.job_id,
            video_path=request.video_path,
            audio_path=request.audio_path,
            verbose=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate_full_video", response_model=TaskSubmissionResponse)
async def generate_full_video(
    request: PromptGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Complete Pipeline: Article text → Final video with voiceover

    This endpoint handles all 5 steps automatically:
    1. Generate prompts from article
    2. Generate all video clips (2-5 min each)
    3. Concatenate videos into one
    4. Generate voiceover
    5. Merge audio + video

    This takes 15-35 minutes total. Poll /api/jobs/{job_id} for status.

    Example:
        POST /api/generate_full_video
        {
            "article_text": "Iran faces protests...",
            "num_shots": 6,
            "clip_duration": 10
        }

        Returns immediately with job_id to poll for status.
    """
    # Generate deterministic job ID from title
    job_id = storage.generate_job_id(title=request.title)

    # Initialize job status
    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "message": "Full pipeline queued"
    }
    storage.update_job_status(job_id, JobStatus.PENDING)

    # Background task for complete pipeline
    async def full_pipeline_task(job_id: str, request: PromptGenerationRequest):
        try:
            # Step 1: Generate prompts (skip if already exists)
            prompts_dir = storage.get_job_dir(job_id, stage="prompts")
            prompts_files = list(prompts_dir.glob("*_prompts.json"))

            if prompts_files:
                # Prompts already exist, load them
                print(f"[pipeline] Prompts already exist for {job_id}, skipping generation")
                prompts_data = storage.load_prompts_json(str(prompts_files[0]))
                prompts_file = str(prompts_files[0])
                voice_text = prompts_data.get("metadata", {}).get("voice_reader")
            else:
                # Generate new prompts
                jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Step 1/5: Generating prompts..."}
                storage.update_job_status(job_id, JobStatus.PROCESSING, message="Generating prompts")

                prompt_service = get_prompt_service()
                prompts_result = await prompt_service.generate_prompts(
                    article_text=request.article_text,
                    title=request.title,
                    num_shots=request.num_shots,
                    clip_duration=request.clip_duration,
                    verbose=True
                )

                prompts_file = prompts_result.prompts_file
                voice_text = prompts_result.voice_reader_text

            # Step 2: Generate videos
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Step 2/5: Generating videos (this takes 12-30 min)..."}
            storage.update_job_status(job_id, JobStatus.PROCESSING, message="Generating videos")

            video_service = get_video_service()
            video_results = await video_service.generate_videos_from_prompts(
                job_id=job_id,
                prompts_file=prompts_file,
                verbose=True
            )

            # Step 3: Concatenate videos
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Step 3/5: Concatenating videos..."}
            storage.update_job_status(job_id, JobStatus.PROCESSING, message="Concatenating videos")

            merge_service = get_merge_service()
            concatenated_path = await merge_service.combine_videos(job_id=job_id, verbose=True)

            # Step 4: Generate voiceover
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Step 4/5: Generating voiceover..."}
            storage.update_job_status(job_id, JobStatus.PROCESSING, message="Generating voiceover")

            tts_service = get_tts_service()
            voiceover_result = await tts_service.generate_voiceover(
                job_id=job_id,
                text=voice_text,
                voice=request.voice or config.TTS_VOICE,
                verbose=True
            )

            # Step 5: Merge final video
            jobs[job_id] = {"status": JobStatus.PROCESSING, "message": "Step 5/5: Merging audio and video..."}
            storage.update_job_status(job_id, JobStatus.PROCESSING, message="Merging final video")

            final_result = await merge_service.merge_final_video(
                job_id=job_id,
                video_path=concatenated_path,
                audio_path=voiceover_result.audio_path,
                verbose=True
            )

            # Complete!
            jobs[job_id] = {
                "status": JobStatus.COMPLETED,
                "message": "Complete pipeline finished successfully",
                "result": {
                    "final_video_path": final_result.final_video_path,
                    "concatenated_video_path": concatenated_path,
                    "audio_path": voiceover_result.audio_path,
                    "prompts_file": prompts_file,
                    "num_videos": len(video_results)
                }
            }
            storage.update_job_status(job_id, JobStatus.COMPLETED, result=final_result.model_dump())

        except Exception as e:
            error_msg = str(e)
            jobs[job_id] = {
                "status": JobStatus.FAILED,
                "message": "Pipeline failed",
                "error": error_msg
            }
            storage.update_job_status(job_id, JobStatus.FAILED, error=error_msg)

    # Start background task
    background_tasks.add_task(full_pipeline_task, job_id, request)

    return TaskSubmissionResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Full video generation pipeline started. This will take 15-35 minutes. Poll /api/jobs/{job_id} for progress.",
        status_url=f"/api/jobs/{job_id}"
    )


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a specific job and all its files

    Example:
        DELETE /api/jobs/20260111_143022_a3f8d9c2
    """
    if storage.delete_job(job_id):
        return {"message": f"Job {job_id} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@app.post("/api/cleanup")
async def cleanup_old_jobs(days_old: int = 7):
    """
    Delete jobs older than specified days

    Example:
        POST /api/cleanup?days_old=7

    Returns number of jobs deleted
    """
    deleted_count = storage.cleanup_old_jobs(days_old=days_old)
    return {
        "message": f"Cleaned up {deleted_count} job(s) older than {days_old} days",
        "deleted_count": deleted_count
    }


@app.get("/api/download/{job_id}")
async def download_video(job_id: str, video_type: str = "final"):
    """
    Download a video file for a job

    Args:
        job_id: Job ID
        video_type: Type of video to download - "final", "concatenated", or specific shot number (e.g. "1", "2")

    Examples:
        GET /api/download/20260111_143022_a3f8d9c2?video_type=final
        GET /api/download/20260111_143022_a3f8d9c2?video_type=concatenated
        GET /api/download/20260111_143022_a3f8d9c2?video_type=1  (shot 1)
    """
    job_dir = storage.get_job_dir(job_id)

    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Determine which file to serve
    if video_type == "final":
        video_path = storage.get_final_video_path(job_id)
        filename = f"{job_id}_final.mp4"
    elif video_type == "concatenated":
        video_path = storage.get_concat_video_path(job_id)
        filename = f"{job_id}_concatenated.mp4"
    else:
        # Assume it's a shot number
        videos = list(job_dir.glob(f"{video_type.zfill(2)}_*.mp4"))
        if not videos:
            raise HTTPException(status_code=404, detail=f"Shot {video_type} not found for job {job_id}")
        video_path = str(videos[0])
        filename = videos[0].name

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail=f"Video file not found: {video_path}")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename
    )


# ==============================================================================
# ERROR HANDLERS
# ==============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
