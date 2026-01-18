#!/usr/bin/env python3
"""
Video Generation Service
========================
Why this file exists:
- Wraps video generation logic from make_a_request.py
- Uses KieClient (no code duplication)
- Generates 10-second video clips via KIE API
"""

import os
import tempfile
from typing import List, Optional
from src.services.kie_client import KieClient
from src.services.frame_extractor_service import FrameExtractorService
from src.storage import StorageManager
from src.config import config
from src.models import VideoGenerationResponse, JobStatus


class VideoService:
    """Service for generating videos via KIE API"""

    def __init__(self, kie_client: KieClient, storage: StorageManager):
        self.kie = kie_client
        self.storage = storage
        self.frame_extractor = FrameExtractorService(storage)
        self.model = config.VIDEO_API_MODEL
        self.aspect_ratio = config.VIDEO_ASPECT_RATIO

    async def generate_video_from_text(
        self,
        job_id: str,
        shot_number: int,
        prompt: str,
        duration: int,
        subject: str,
        verbose: bool = True
    ) -> VideoGenerationResponse:
        """
        Generate video from text prompt only (text-to-video)

        Args:
            job_id: Job ID for organizing outputs
            shot_number: Shot number (1-6)
            prompt: Video generation prompt
            duration: Duration in seconds (typically 10)
            subject: Subject/title for the shot
            verbose: Print progress

        Returns:
            VideoGenerationResponse with video path
        """
        if verbose:
            print(f"[video] Generating shot {shot_number}: {subject}")
            print(f"[video] Mode: TEXT-TO-VIDEO")
            print(f"[video] Duration: {duration}s")

        # Create KIE task payload for text-to-video
        aspect_ratio_value = "portrait" if self.aspect_ratio == "9:16" else self.aspect_ratio

        payload = {
            "model": "sora-2-text-to-video",
            "input": {
                "aspect_ratio": aspect_ratio_value,
                "n_frames": str(duration),
                "size": "standard",
                "prompt": prompt,
            },
        }

        if verbose:
            print(f"[video] Creating task with model: {payload['model']}...")

        # Create task
        task_id = await self.kie.create_task(payload)

        if verbose:
            print(f"[video] Task created: {task_id}")
            print(f"[video] Polling for completion (this takes 2-5 minutes)...")

        # Poll until complete
        detail = await self.kie.poll_task(task_id, verbose=verbose)

        # Extract video URL
        video_url = self.kie.extract_result_url(detail)

        if verbose:
            print(f"[video] Video ready: {video_url}")
            print(f"[video] Downloading...")

        # Download to temporary location
        temp_path = os.path.join(tempfile.gettempdir(), f"video_{task_id}.mp4")
        await self.kie.download_file(video_url, temp_path)

        # Move to organized storage
        final_path = self.storage.save_video(temp_path, job_id, shot_number, subject)

        if verbose:
            print(f"[video] Saved: {final_path}")

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return VideoGenerationResponse(
            job_id=job_id,
            shot_number=shot_number,
            video_path=final_path,
            status=JobStatus.COMPLETED
        )

    async def generate_video_from_image(
        self,
        job_id: str,
        shot_number: int,
        prompt: str,
        duration: int,
        subject: str,
        image_path: str,
        verbose: bool = True
    ) -> VideoGenerationResponse:
        """
        Generate video from image + prompt (image-to-video)

        Args:
            job_id: Job ID for organizing outputs
            shot_number: Shot number (2-6)
            prompt: Video generation prompt
            duration: Duration in seconds (typically 10)
            subject: Subject/title for the shot
            image_path: Path to reference image (last frame from previous video)
            verbose: Print progress

        Returns:
            VideoGenerationResponse with video path
        """
        if verbose:
            print(f"[video] Generating shot {shot_number}: {subject}")
            print(f"[video] Mode: IMAGE-TO-VIDEO")
            print(f"[video] Duration: {duration}s")
            print(f"[video] Reference image: {image_path}")

        # Create KIE task payload for image-to-video
        aspect_ratio_value = "portrait" if self.aspect_ratio == "9:16" else self.aspect_ratio

        # Upload frame to get HTTPS URL (KIE requires HTTPS)
        from .image_uploader import ImageUploader
        
        uploader = ImageUploader()
        image_url = await uploader.upload_image(image_path, verbose=verbose)
        
        if verbose:
            print(f"[video] Uploaded image URL: {image_url}")


        payload = {
            "model": "sora-2-image-to-video",
            "input": {
                "image_url": image_url,  # ✅ Changed from "image" to "image_url"
                "prompt": prompt,
                "aspect_ratio": aspect_ratio_value,
                "n_frames": str(duration),
                "size": "standard",
            },
        }

        if verbose:
            print(f"[video] Creating task with model: {payload}...")

        # Create task
        task_id = await self.kie.create_task(payload)

        if verbose:
            print(f"[video] Task created: {task_id}")
            print(f"[video] Polling for completion (this takes 2-5 minutes)...")

        # Poll until complete
        detail = await self.kie.poll_task(task_id, verbose=verbose)

        # Extract video URL
        video_url = self.kie.extract_result_url(detail)

        if verbose:
            print(f"[video] Video ready: {video_url}")
            print(f"[video] Downloading...")

        # Download to temporary location
        temp_path = os.path.join(tempfile.gettempdir(), f"video_{task_id}.mp4")
        await self.kie.download_file(video_url, temp_path)

        # Move to organized storage
        final_path = self.storage.save_video(temp_path, job_id, shot_number, subject)

        if verbose:
            print(f"[video] Saved: {final_path}")

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return VideoGenerationResponse(
            job_id=job_id,
            shot_number=shot_number,
            video_path=final_path,
            status=JobStatus.COMPLETED
        )

    async def generate_videos_from_prompts(
        self,
        job_id: str,
        prompts_file: str,
        verbose: bool = True
    ) -> List[VideoGenerationResponse]:
        """
        Generate all videos from a prompts JSON file

        Args:
            job_id: Job ID
            prompts_file: Path to prompts JSON file
            verbose: Print progress

        Returns:
            List of VideoGenerationResponse
        """
        # Load prompts JSON
        data = self.storage.load_prompts_json(prompts_file)
        shots = data.get("prompts", [])

        if verbose:
            print(f"[video] Generating {len(shots)} videos...")

        results = []
        previous_video_path = None  # Track the last generated video for continuity
        
        for idx, shot in enumerate(shots, 1):
            if verbose:
                print(f"\n[video] === Shot {idx}/{len(shots)} ===")

            # Check if video already exists (for retry logic)
            shot_number = shot["shot_number"]
            subject = shot["subject"]
            safe_subject = "".join(c if c.isalnum() or c in "_-" else "_" for c in subject)[:50]
            expected_filename = f"{shot_number:02d}_{safe_subject}.mp4"
            job_dir = self.storage.get_job_dir(job_id)
            expected_path = job_dir / expected_filename

            if expected_path.exists():
                if verbose:
                    print(f"[video] Shot {shot_number} already exists, skipping: {expected_filename}")

                # Return existing video
                result = VideoGenerationResponse(
                    job_id=job_id,
                    shot_number=shot_number,
                    video_path=str(expected_path),
                    status=JobStatus.COMPLETED
                )
                results.append(result)
                previous_video_path = str(expected_path)  # Update for next iteration
            else:
                # Decide whether to use text-to-video or image-to-video
                if previous_video_path and shot_number > 1:
                    # IMAGE-TO-VIDEO: Extract frame from previous video first
                    if verbose:
                        print(f"[video] Extracting last frame from previous video...")
                    
                    init_frame_path = await self.frame_extractor.extract_last_frame(
                        video_path=previous_video_path,
                        job_id=job_id,
                        shot_number=shot_number - 1,  # Frame from previous shot
                        verbose=verbose
                    )
                    
                    if verbose:
                        print(f"[video] Frame extracted: {init_frame_path}")
                    
                    # Generate video from image - will raise exception if it fails
                    result = await self.generate_video_from_image(
                        job_id=job_id,
                        shot_number=shot["shot_number"],
                        prompt=shot["prompt"],
                        duration=shot["duration"],
                        subject=shot["subject"],
                        image_path=init_frame_path,
                        verbose=verbose
                    )
                else:
                    # TEXT-TO-VIDEO: First shot or no previous video
                    result = await self.generate_video_from_text(
                        job_id=job_id,
                        shot_number=shot["shot_number"],
                        prompt=shot["prompt"],
                            duration=shot["duration"],
                        subject=shot["subject"],
                        verbose=verbose
                    )
                
                results.append(result)
                previous_video_path = result.video_path  # Update for next iteration

            # Update job progress
            self.storage.update_job_status(
                job_id,
                "processing",
                message=f"Generated {idx}/{len(shots)} videos",
                progress={"videos_completed": idx, "videos_total": len(shots)}
            )

        if verbose:
            print(f"\n[video] All {len(results)} videos generated!")

        return results
