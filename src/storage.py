#!/usr/bin/env python3
"""
Storage Manager
===============
Why this file exists:
- Centralized file management (no more scattered os.path logic)
- Easy to switch to S3/database later
- Consistent file naming and organization
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class StorageManager:
    """Manages file storage for jobs, videos, audio, and JSON outputs"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir).resolve()
        self.jobs_dir = self.base_dir / "jobs"

        print(f"[StorageManager] Initialized with base_dir: {self.base_dir}")
        print(f"[StorageManager] Jobs dir: {self.jobs_dir}")

        # Legacy directories (keep for backwards compatibility)
        self.output_dir = self.base_dir / "output"
        self.downloads_dir = self.base_dir / "downloads"

        # Create base directories
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def generate_job_id(self, title: str = None) -> str:
        """
        Generate job ID (deterministic if title provided)

        Args:
            title: Optional article title for deterministic job_id (enables retries)

        Returns:
            job_id string
        """
        if title:
            # Create deterministic job_id from title
            # Replace spaces and special chars with underscores
            safe_title = "".join(c if c.isalnum() or c in "_-" else "_" for c in title)
            safe_title = safe_title.strip("_")[:50]  # Limit length
            return safe_title
        else:
            # Generate unique job_id with timestamp
            return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def get_job_dir(self, job_id: str, stage: str = None) -> Path:
        """
        Get directory for a specific job and optional stage

        Args:
            job_id: Job identifier
            stage: Optional stage subdirectory: 'prompts', 'videos', 'audio', 'final'
                   If None, returns the job root directory

        Returns:
            Path to job directory (and stage subdirectory if specified)
        """
        job_root = self.jobs_dir / job_id

        if stage:
            job_dir = job_root / stage
        else:
            job_dir = job_root

        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def save_prompts_json(self, data: Dict[str, Any], job_id: str) -> str:
        """Save prompts JSON to job directory (overwrites if exists)"""
        job_dir = self.get_job_dir(job_id, stage="prompts")

        # Delete any existing prompts files first
        for old_prompts in job_dir.glob("*_prompts.json"):
            old_prompts.unlink()
            print(f"[storage] Deleted old prompts file: {old_prompts.name}")

        # Generate filename
        title = data.get("metadata", {}).get("title", "video")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
        filename = f"{job_id}_{safe_title}_prompts.json"

        filepath = job_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return str(filepath)

    def load_prompts_json(self, filepath: str) -> Dict[str, Any]:
        """Load prompts JSON from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_video(self, video_path: str, job_id: str, shot_number: int, subject: str) -> str:
        """Copy/move video to job directory with standardized naming"""
        job_dir = self.get_job_dir(job_id, stage="videos")

        # Sanitize subject for filename
        safe_subject = "".join(c if c.isalnum() or c in "_-" else "_" for c in subject)[:50]
        filename = f"{shot_number:02d}_{safe_subject}.mp4"

        dest_path = job_dir / filename

        # If video_path is different from dest_path, copy it
        if os.path.abspath(video_path) != os.path.abspath(dest_path):
            import shutil
            shutil.copy2(video_path, dest_path)

        return str(dest_path)

    def save_audio(self, audio_path: str, job_id: str) -> str:
        """Copy/move audio to job directory"""
        job_dir = self.get_job_dir(job_id, stage="audio")
        dest_path = job_dir / "voiceover.mp3"

        if os.path.abspath(audio_path) != os.path.abspath(dest_path):
            import shutil
            shutil.copy2(audio_path, dest_path)

        return str(dest_path)

    def get_video_path(self, job_id: str, shot_number: int, subject: str) -> str:
        """Get expected path for a video file"""
        job_dir = self.get_job_dir(job_id, stage="videos")
        safe_subject = "".join(c if c.isalnum() or c in "_-" else "_" for c in subject)[:50]
        filename = f"{shot_number:02d}_{safe_subject}.mp4"
        return str(job_dir / filename)

    def get_audio_path(self, job_id: str) -> str:
        """Get expected path for voiceover audio"""
        return str(self.get_job_dir(job_id, stage="audio") / "voiceover.mp3")

    def get_concat_video_path(self, job_id: str) -> str:
        """Get path for concatenated video (before audio merge)"""
        return str(self.get_job_dir(job_id, stage="videos") / "concatenated.mp4")

    def get_final_video_path(self, job_id: str) -> str:
        """Get path for final merged video"""
        return str(self.get_job_dir(job_id, stage="final") / "final.mp4")

    def get_frame_path(self, job_id: str, shot_number: int, frame_type: str = "last") -> str:
        """
        Get path for an extracted frame
        
        Args:
            job_id: Job identifier
            shot_number: Shot number the frame was extracted from
            frame_type: Type of frame ('last', 'first', or timestamp like '5.0s')
        
        Returns:
            Path to frame file
        """
        frame_dir = self.get_job_dir(job_id, stage="frames")
        filename = f"shot_{shot_number:02d}_{frame_type}.jpg"
        return str(frame_dir / filename)

    def save_frame(self, frame_path: str, job_id: str, shot_number: int, frame_type: str = "last") -> str:
        """
        Save/move extracted frame to job directory with standardized naming
        
        Args:
            frame_path: Current path to frame file
            job_id: Job identifier
            shot_number: Shot number the frame was extracted from
            frame_type: Type of frame ('last', 'first', or timestamp)
        
        Returns:
            New path to saved frame
        """
        dest_path = self.get_frame_path(job_id, shot_number, frame_type)
        
        # If paths are different, copy the file
        if os.path.abspath(frame_path) != os.path.abspath(dest_path):
            import shutil
            shutil.copy2(frame_path, dest_path)
        
        return dest_path

    def list_videos_for_job(self, job_id: str) -> List[str]:
        """List all video files for a job, sorted by shot number"""
        job_dir = self.get_job_dir(job_id, stage="videos")
        videos = sorted([
            str(f) for f in job_dir.glob("*.mp4")
            if f.name not in ["concatenated.mp4", "final.mp4"]
        ])
        return videos

    def list_frames_for_job(self, job_id: str) -> List[str]:
        """List all extracted frames for a job, sorted by shot number"""
        frame_dir = self.get_job_dir(job_id, stage="frames")
        if not frame_dir.exists():
            return []
        
        frames = sorted([str(f) for f in frame_dir.glob("*.jpg")])
        return frames

    def save_job_metadata(self, job_id: str, metadata: Dict[str, Any]) -> str:
        """Save job metadata for status tracking (stored in prompts directory)"""
        job_dir = self.get_job_dir(job_id, stage="prompts")
        metadata_path = job_dir / "metadata.json"

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        return str(metadata_path)

    def load_job_metadata(self, job_id: str) -> Dict[str, Any]:
        """Load job metadata (from prompts directory)"""
        job_dir = self.get_job_dir(job_id, stage="prompts")
        metadata_path = job_dir / "metadata.json"

        if not metadata_path.exists():
            return {}

        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_job_status(self, job_id: str, status: str, **kwargs) -> None:
        """Update job status"""
        metadata = self.load_job_metadata(job_id)
        metadata["status"] = status
        metadata["updated_at"] = datetime.now().isoformat()
        metadata.update(kwargs)
        self.save_job_metadata(job_id, metadata)

    def job_exists(self, job_id: str) -> bool:
        """Check if job directory exists (check prompts stage)"""
        return self.get_job_dir(job_id, stage="prompts").exists()

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and all its files"""
        import shutil

        # Delete the entire job root directory (contains all stages)
        job_root = self.jobs_dir / job_id

        if job_root.exists():
            shutil.rmtree(job_root)
            print(f"[storage] Deleted job: {job_id}")
            return True

        return False

    def cleanup_old_jobs(self, days_old: int = 7) -> int:
        """
        Delete jobs older than specified days

        Args:
            days_old: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        import shutil
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=days_old)
        deleted_count = 0

        # Iterate through jobs directory to find all jobs
        for job_dir in self.jobs_dir.iterdir():
            if not job_dir.is_dir():
                continue

            job_id = job_dir.name

            # Check job creation time from metadata (stored in prompts subfolder)
            metadata_path = job_dir / "prompts" / "metadata.json"

            if metadata_path.exists():
                metadata = self.load_job_metadata(job_id)
                created_at_str = metadata.get("updated_at", metadata.get("created_at"))

                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str)
                        if created_at < cutoff_time:
                            # Delete from all stages
                            self.delete_job(job_id)
                            deleted_count += 1
                            print(f"[storage] Deleted old job: {job_id} (created {created_at.date()})")
                    except (ValueError, TypeError):
                        pass
            else:
                # Use directory modification time as fallback
                mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
                if mtime < cutoff_time:
                    self.delete_job(job_id)
                    deleted_count += 1
                    print(f"[storage] Deleted old job: {job_id} (modified {mtime.date()})")

        return deleted_count
