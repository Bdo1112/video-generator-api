#!/usr/bin/env python3
"""
Video Merge Service
===================
Why this file exists:
- Handles FFmpeg operations for video concatenation and audio merging
- Combines multiple 10s clips into 1 minute video
- Adds voiceover audio to final video
"""

import os
import subprocess
import tempfile
from typing import List
from src.storage import StorageManager
from src.models import MergeResponse, JobStatus


class MergeService:
    """Service for merging videos and audio using FFmpeg"""

    def __init__(self, storage: StorageManager):
        self.storage = storage

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str,
        verbose: bool = True
    ) -> str:
        """
        Concatenate multiple videos into one

        Args:
            video_paths: List of video file paths (in order)
            output_path: Output path for concatenated video
            verbose: Print progress

        Returns:
            Path to concatenated video
        """
        if verbose:
            print(f"[merge] Concatenating {len(video_paths)} videos...")

        # Create concat list file for FFmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = f.name
            for video_path in video_paths:
                abs_path = os.path.abspath(video_path)
                f.write(f"file '{abs_path}'\n")

        try:
            # Run FFmpeg concat
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",  # Copy streams without re-encoding
                output_path,
            ]

            if verbose:
                print(f"[merge] Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            if verbose:
                print(f"[merge] Concatenated video saved: {output_path}")

        finally:
            # Clean up concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)

        return output_path

    def merge_audio_video(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        verbose: bool = True
    ) -> str:
        """
        Merge audio track with video

        Args:
            video_path: Path to video file
            audio_path: Path to audio file
            output_path: Output path for final video
            verbose: Print progress

        Returns:
            Path to final merged video
        """
        if verbose:
            print(f"[merge] Merging audio with video...")
            print(f"[merge] Video: {video_path}")
            print(f"[merge] Audio: {audio_path}")

        # FFmpeg command to merge audio and video
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i", video_path,  # Input video
            "-i", audio_path,  # Input audio
            "-c:v", "copy",  # Copy video stream without re-encoding
            "-c:a", "aac",  # Encode audio as AAC
            "-map", "0:v:0",  # Map video from first input
            "-map", "1:a:0",  # Map audio from second input
            "-shortest",  # End when shortest stream ends
            output_path,
        ]

        if verbose:
            print(f"[merge] Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )

        if verbose:
            print(f"[merge] Final video saved: {output_path}")

        return output_path

    async def combine_videos(
        self,
        job_id: str,
        verbose: bool = True
    ) -> str:
        """
        Concatenate all videos for a job

        Args:
            job_id: Job ID
            verbose: Print progress

        Returns:
            Path to concatenated video
        """
        # Get output path
        output_path = self.storage.get_concat_video_path(job_id)

        # Check if concatenated video already exists (for retry logic)
        if os.path.exists(output_path):
            if verbose:
                print(f"[merge] Concatenated video already exists, skipping: {output_path}")
            return output_path

        # Get all video files for this job
        video_paths = self.storage.list_videos_for_job(job_id)

        if not video_paths:
            raise ValueError(f"No videos found for job {job_id}")

        if verbose:
            print(f"[merge] Found {len(video_paths)} videos to concatenate")

        # Concatenate
        self.concatenate_videos(video_paths, output_path, verbose=verbose)

        return output_path

    async def merge_final_video(
        self,
        job_id: str,
        video_path: str = None,
        audio_path: str = None,
        verbose: bool = True
    ) -> MergeResponse:
        """
        Merge audio and video for final output

        Args:
            job_id: Job ID
            video_path: Path to concatenated video (optional, will use default if not provided)
            audio_path: Path to voiceover audio (optional, will use default if not provided)
            verbose: Print progress

        Returns:
            MergeResponse with final video path
        """
        # Use default paths if not provided
        video_path = video_path or self.storage.get_concat_video_path(job_id)
        audio_path = audio_path or self.storage.get_audio_path(job_id)

        # Get output path
        output_path = self.storage.get_final_video_path(job_id)

        # Check if final video already exists (for retry logic)
        if os.path.exists(output_path):
            if verbose:
                print(f"[merge] Final video already exists, skipping: {output_path}")
            return MergeResponse(
                job_id=job_id,
                final_video_path=output_path,
                status=JobStatus.COMPLETED
            )

        # Check files exist
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        # Merge
        self.merge_audio_video(video_path, audio_path, output_path, verbose=verbose)

        # Update job status
        self.storage.update_job_status(
            job_id,
            "completed",
            message="Final video created",
            final_video_path=output_path
        )

        return MergeResponse(
            job_id=job_id,
            final_video_path=output_path,
            status=JobStatus.COMPLETED
        )
