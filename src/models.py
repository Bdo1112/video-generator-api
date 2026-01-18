#!/usr/bin/env python3
"""
Pydantic Models
===============
Why this file exists:
- Defines data structures for API requests and responses
- FastAPI uses these for auto-validation and auto-documentation
- Type safety throughout the application
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Status of a background job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ==============================================================================
# REQUEST MODELS (what the API receives)
# ==============================================================================

class PromptGenerationRequest(BaseModel):
    """Request to generate video prompts from an article"""
    article_text: str = Field(..., description="The news article text", min_length=100)
    title: str = Field(..., description="Article title (used to create consistent job_id for retries)", min_length=3, max_length=100)
    num_shots: Optional[int] = Field(None, description="Number of shots to generate", ge=1, le=12)
    clip_duration: Optional[int] = Field(None, description="Duration per clip in seconds", ge=5, le=60)
    voice: Optional[str] = Field(None, description="Voice for TTS (used in full pipeline)")

    class Config:
        json_schema_extra = {
            "example": {
                "article_text": "Iran faces its largest protests since 2022...",
                "title": "Iran Protests Update",
                "num_shots": 6,
                "clip_duration": 10
            }
        }


class VideoGenerationRequest(BaseModel):
    """Request to generate a single video clip"""
    job_id: str = Field(..., description="Job ID from prompt generation")
    shot_number: int = Field(..., description="Shot number", ge=1)
    prompt: str = Field(..., description="Video generation prompt")
    duration: int = Field(..., description="Duration in seconds", ge=5, le=60)
    subject: str = Field(..., description="Subject/title for the shot")


class VideoBatchRequest(BaseModel):
    """Request to generate all videos from a prompts file"""
    job_id: str = Field(..., description="Job ID from prompt generation")
    prompts_file: Optional[str] = Field(None, description="Path to prompts JSON file (auto-detected if not provided)")


class VoiceoverRequest(BaseModel):
    """Request to generate voiceover audio"""
    job_id: str = Field(..., description="Job ID")
    text: Optional[str] = Field(None, description="Text to convert to speech (if not provided, reads from job's prompts.json)", min_length=10)
    voice: Optional[str] = Field(None, description="Voice name (default: from config)")


class CombineVideosRequest(BaseModel):
    """Request to combine multiple video clips"""
    job_id: str = Field(..., description="Job ID")


class MergeRequest(BaseModel):
    """Request to merge audio and video"""
    job_id: str = Field(..., description="Job ID")
    video_path: Optional[str] = Field(None, description="Path to concatenated video file (auto-detected if not provided)")
    audio_path: Optional[str] = Field(None, description="Path to voiceover audio file (auto-detected if not provided)")


class ImageToVideoRequest(BaseModel):
    """Request to generate video from an image (for testing image-to-video)"""
    image_path: str = Field(..., description="Path to the source image file")
    prompt: str = Field(..., description="Video generation prompt", min_length=10)
    duration: int = Field(10, description="Duration in seconds", ge=5, le=60)
    job_id: Optional[str] = Field(None, description="Optional job ID (auto-generated if not provided)")

    class Config:
        json_schema_extra = {
            "example": {
                "image_path": "/path/to/image.png",
                "prompt": "A cinematic shot of the scene slowly coming to life with gentle camera movement",
                "duration": 10
            }
        }


class PipelineRequest(BaseModel):
    """Request to run the full pipeline"""
    article_text: str = Field(..., description="The news article text", min_length=100)
    num_shots: Optional[int] = Field(None, description="Number of shots", ge=1, le=12)
    clip_duration: Optional[int] = Field(None, description="Duration per clip in seconds", ge=5, le=60)
    voice: Optional[str] = Field(None, description="Voice for voiceover")
    skip_voiceover: bool = Field(False, description="Skip voiceover generation")


# ==============================================================================
# RESPONSE MODELS (what the API returns)
# ==============================================================================

class PromptGenerationResponse(BaseModel):
    """Response after generating prompts"""
    job_id: str
    status: JobStatus
    prompts_file: str
    title: str
    num_shots: int
    total_duration: int
    voice_reader_text: Optional[str] = None


class VideoGenerationResponse(BaseModel):
    """Response after generating a single video"""
    job_id: str
    shot_number: int
    video_path: str
    status: JobStatus


class VideoBatchResponse(BaseModel):
    """Response after generating multiple videos"""
    job_id: str
    videos: List[VideoGenerationResponse]
    status: JobStatus


class VoiceoverResponse(BaseModel):
    """Response after generating voiceover"""
    job_id: str
    audio_path: str
    status: JobStatus


class MergeResponse(BaseModel):
    """Response after merging audio and video"""
    job_id: str
    final_video_path: str
    status: JobStatus


class ImageToVideoResponse(BaseModel):
    """Response after generating video from image"""
    job_id: str
    video_path: str
    status: JobStatus
    image_url: Optional[str] = None  # The uploaded image URL (for debugging)


class PipelineResponse(BaseModel):
    """Response from full pipeline"""
    job_id: str
    status: JobStatus
    prompts_file: str
    videos: List[str]
    voiceover_path: Optional[str] = None
    concatenated_video_path: str
    final_video_path: str
    title: str
    total_duration: int


class JobStatusResponse(BaseModel):
    """Response for job status queries"""
    job_id: str
    status: JobStatus
    message: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskSubmissionResponse(BaseModel):
    """Response when a long-running task is submitted"""
    job_id: str
    status: JobStatus
    message: str
    status_url: str  # URL to poll for status


# ==============================================================================
# INTERNAL MODELS (used within services)
# ==============================================================================

class ShotPrompt(BaseModel):
    """A single shot prompt from the prompts JSON"""
    shot_number: int
    prompt: str
    duration: int
    subject: str
    narrative_beat: str
    is_image_to_video: bool
