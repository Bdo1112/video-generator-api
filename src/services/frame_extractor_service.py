#!/usr/bin/env python3
"""
Frame Extractor Service
========================
Why this file exists:
- Extracts frames from videos for video continuity
- Used to get last frame of video N to start video N+1
- Ensures visual consistency across generated clips
"""

import subprocess
import os
from pathlib import Path
from typing import Optional
from src.storage import StorageManager


class FrameExtractorService:
    """Service for extracting frames from videos using FFmpeg"""

    def __init__(self, storage: StorageManager):
        self.storage = storage

    async def extract_last_frame(
        self,
        video_path: str,
        job_id: str,
        shot_number: int,
        output_filename: Optional[str] = None,
        verbose: bool = True
    ) -> str:
        """
        Extract the last frame from a video

        Args:
            video_path: Path to the source video
            job_id: Job ID for organizing outputs
            shot_number: Shot number (used in default filename)
            output_filename: Optional custom filename (default: "frame_{shot_number}_last.jpg")
            verbose: Print progress messages

        Returns:
            Path to the extracted frame image

        Raises:
            FileNotFoundError: If video_path doesn't exist
            RuntimeError: If FFmpeg extraction fails
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        if verbose:
            print(f"[frame] Extracting last frame from: {video_path}")

        # Use storage manager for consistent path (PNG format for better compatibility)
        frame_path_jpg = self.storage.get_frame_path(job_id, shot_number, frame_type="last")
        output_path = frame_path_jpg.replace('.jpg', '.png')  # Use PNG instead

        if verbose:
            print(f"[frame] Output: {output_path}")

        # Ensure output directory exists (critical!)
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # FFmpeg command to extract last frame using reverse filter
        # This reverses the video and takes the first frame, which gives us the actual last frame
        # This is more reliable than seeking to a specific timestamp
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', 'reverse',        # Reverse the video
            '-frames:v', '1',        # Take first frame (which is the last frame of original)
            '-q:v', '2',             # Quality
            str(output_path),
            '-y'                     # Overwrite
        ]

        if verbose:
            print(f"[frame] Using reverse filter to extract last frame...")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            if verbose:
                print(f"[frame] Frame extracted successfully")

        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg failed to extract frame: {e.stderr}"
            if verbose:
                print(f"[frame] ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        # Verify the file was created
        if not Path(output_path).exists():
            raise RuntimeError(f"Frame extraction failed - output file not created: {output_path}")

        return output_path

    async def extract_frame_at_time(
        self,
        video_path: str,
        job_id: str,
        timestamp: float,
        shot_number: int = 0,
        output_filename: Optional[str] = None,
        verbose: bool = True
    ) -> str:
        """
        Extract a frame at a specific timestamp

        Args:
            video_path: Path to the source video
            job_id: Job ID for organizing outputs
            timestamp: Time in seconds to extract frame from
            shot_number: Shot number (default 0 for non-shot-specific frames)
            output_filename: Optional custom filename
            verbose: Print progress messages

        Returns:
            Path to the extracted frame image
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        if verbose:
            print(f"[frame] Extracting frame at {timestamp}s from: {video_path}")

        # Use storage manager or custom filename (PNG format)
        if output_filename:
            frame_dir = self.storage.get_job_dir(job_id, stage="frames")
            # Ensure PNG extension
            if not output_filename.endswith('.png'):
                output_filename = output_filename.replace('.jpg', '.png')
            output_path = str(frame_dir / output_filename)
        else:
            # Use standard naming: shot_00_5.0s.png
            frame_type = f"{timestamp:.1f}s"
            frame_path_jpg = self.storage.get_frame_path(job_id, shot_number, frame_type)
            output_path = frame_path_jpg.replace('.jpg', '.png')

        if verbose:
            print(f"[frame] Output: {output_path}")

        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-ss', str(timestamp),   # Seek to specific time
            '-i', str(video_path),
            '-frames:v', '1',        # Extract one frame
            '-q:v', '2',             # Quality
            str(output_path),
            '-y'
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if verbose:
                print(f"[frame] Frame extracted successfully")

        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg failed to extract frame: {e.stderr}"
            if verbose:
                print(f"[frame] ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        if not Path(output_path).exists():
            raise RuntimeError(f"Frame extraction failed - output file not created: {output_path}")

        return output_path

    def check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available in the system

        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
