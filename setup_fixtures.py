#!/usr/bin/env python3
"""
Setup test fixtures by copying sample videos from jobs folder
"""

import shutil
from pathlib import Path


def setup_fixtures():
    """Copy sample videos from jobs to fixtures for testing"""
    
    # Paths
    jobs_dir = Path("./jobs")
    fixtures_dir = Path("./tests/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    print("Setting up test fixtures...")
    print(f"Source: {jobs_dir.absolute()}")
    print(f"Destination: {fixtures_dir.absolute()}\n")
    
    # Find some sample videos
    videos_copied = 0
    max_videos = 3  # Copy 3 test videos
    
    for job_dir in sorted(jobs_dir.iterdir()):
        if not job_dir.is_dir() or videos_copied >= max_videos:
            continue
        
        # Look for video files (not concatenated or final)
        for video_file in sorted(job_dir.glob("*.mp4")):
            if video_file.name in ["concatenated.mp4", "final.mp4"]:
                continue
            
            # Copy to fixtures with a simpler name
            dest_name = f"test_video_{videos_copied + 1:02d}.mp4"
            dest_path = fixtures_dir / dest_name
            
            if dest_path.exists():
                print(f"  ✓ Already exists: {dest_name}")
            else:
                print(f"  Copying: {video_file.name}")
                print(f"      → {dest_name}")
                shutil.copy2(video_file, dest_path)
                file_size = dest_path.stat().st_size / (1024 * 1024)  # MB
                print(f"      Size: {file_size:.2f} MB")
            
            videos_copied += 1
            
            if videos_copied >= max_videos:
                break
    
    if videos_copied == 0:
        print("❌ No videos found in ./jobs/")
        print("   Please generate some videos first using the API")
        return False
    
    print(f"\n✅ Successfully set up {videos_copied} test videos in fixtures/")
    print(f"\nFixtures location: {fixtures_dir.absolute()}")
    print("\nTest videos:")
    for video in sorted(fixtures_dir.glob("*.mp4")):
        size_mb = video.stat().st_size / (1024 * 1024)
        print(f"  - {video.name} ({size_mb:.2f} MB)")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Test Fixtures Setup")
    print("=" * 60)
    print()
    
    success = setup_fixtures()
    
    if success:
        print("\n" + "=" * 60)
        print("Next step:")
        print("  Run: python tests/test_frame_extraction.py")
        print("=" * 60)
