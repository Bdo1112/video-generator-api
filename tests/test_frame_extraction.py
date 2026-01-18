#!/usr/bin/env python3
"""
Test script for frame extraction service

Run this to verify frame extraction is working:
    cd /Users/brianoh/Dev/01_Personal/01_Youtube/03_video_gen/01_video_generator
    python tests/test_frame_extraction.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path so we can import src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.frame_extractor_service import FrameExtractorService
from src.storage import StorageManager


async def test_frame_extraction():
    """Test extracting frames from fixture videos and compare with expected frames"""
    
    print("=" * 70)
    print("Frame Extraction Service - Test Suite")
    print("=" * 70)
    print()
    
    # Initialize services
    storage = StorageManager()
    frame_service = FrameExtractorService(storage)
    
    # Check FFmpeg is available
    print("🔍 Checking FFmpeg availability...")
    if not frame_service.check_ffmpeg_available():
        print("❌ FFmpeg is not installed!")
        print("   Install with: brew install ffmpeg")
        return
    
    print("✅ FFmpeg is available\n")
    
    # Find test videos and expected frames in fixtures
    fixtures_dir = project_root / "tests" / "fixtures"
    videos_dir = fixtures_dir / "videos"
    expected_frames_dir = fixtures_dir / "frames"
    
    if not videos_dir.exists():
        print(f"❌ Videos directory not found: {videos_dir}")
        print("   Please create tests/fixtures/videos/ and add test videos")
        return
    
    test_videos = list(videos_dir.glob("*.mp4"))
    
    if not test_videos:
        print(f"❌ No test videos found in {videos_dir}")
        print("   Please add some .mp4 files to tests/fixtures/videos/")
        return
    
    print(f"📁 Found {len(test_videos)} test video(s) in fixtures/videos/")
    for vid in test_videos:
        size_mb = vid.stat().st_size / (1024 * 1024)
        print(f"   - {vid.name} ({size_mb:.2f} MB)")
    
    # Check if expected frames exist
    has_expected_frames = expected_frames_dir.exists() and list(expected_frames_dir.glob("*.png"))
    if has_expected_frames:
        expected_frames = list(expected_frames_dir.glob("*.png"))
        print(f"\n📸 Found {len(expected_frames)} expected frame(s) in fixtures/frames/")
        for frame in expected_frames:
            size_kb = frame.stat().st_size / 1024
            print(f"   - {frame.name} ({size_kb:.1f} KB)")
    else:
        print(f"\nℹ️  No expected frames found in fixtures/frames/")
        print(f"   Extracted frames will be saved for manual verification")
    
    print()
    
    # Use the first video for testing
    test_video = str(test_videos[0])
    print(f"🎬 Using test video: {test_videos[0].name}\n")
    
    # Test 1: Extract last frame
    print("-" * 70)
    print("Test 1: Extracting LAST FRAME")
    print("-" * 70)
    try:
        frame_path = await frame_service.extract_last_frame(
            video_path=test_video,
            job_id="test_extraction",
            shot_number=1,
            verbose=True
        )
        
        if os.path.exists(frame_path):
            file_size = os.path.getsize(frame_path) / 1024  # KB
            print(f"✅ Last frame extracted successfully!")
            print(f"   Path: {frame_path}")
            print(f"   Size: {file_size:.1f} KB")
            
            # Compare with expected frame if it exists
            expected_frame = expected_frames_dir / "expected_last_frame.png"
            if expected_frame.exists():
                expected_size = expected_frame.stat().st_size / 1024
                actual_size = file_size
                size_diff = abs(expected_size - actual_size)
                
                print(f"\n   📊 Comparison with expected frame:")
                print(f"      Expected: {expected_size:.1f} KB")
                print(f"      Actual:   {actual_size:.1f} KB")
                print(f"      Diff:     {size_diff:.1f} KB")
                
                # File sizes should be similar (within 10%)
                if size_diff / expected_size < 0.1:
                    print(f"      ✅ Frames are similar in size")
                else:
                    print(f"      ⚠️  Frame sizes differ significantly")
            print()
        else:
            print(f"❌ Frame file not created\n")
    
    except Exception as e:
        print(f"❌ Extraction failed: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Test 2: Extract frame at specific time (5 seconds)
    print("-" * 70)
    print("Test 2: Extracting FRAME AT 5 SECONDS")
    print("-" * 70)
    try:
        frame_path = await frame_service.extract_frame_at_time(
            video_path=test_video,
            job_id="test_extraction",
            timestamp=5.0,
            shot_number=1,
            verbose=True
        )
        
        if os.path.exists(frame_path):
            file_size = os.path.getsize(frame_path) / 1024
            print(f"✅ Frame at 5s extracted successfully!")
            print(f"   Path: {frame_path}")
            print(f"   Size: {file_size:.1f} KB\n")
        else:
            print(f"❌ Frame file not created\n")
    
    except Exception as e:
        print(f"❌ Extraction failed: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test multiple videos (continuity simulation)
    if len(test_videos) > 1:
        print("-" * 70)
        print(f"Test 3: Testing VIDEO CONTINUITY (using {min(3, len(test_videos))} videos)")
        print("-" * 70)
        
        continuity_results = []
        for idx, video in enumerate(test_videos[:3], 1):
            print(f"\n📹 Video {idx}: {video.name}")
            try:
                frame_path = await frame_service.extract_last_frame(
                    video_path=str(video),
                    job_id="test_continuity",
                    shot_number=idx,
                    verbose=True
                )
                print(f"   ✅ Frame extracted: {Path(frame_path).name}")
                continuity_results.append(frame_path)
                
                # Check if expected frame exists for this shot
                expected_frame = expected_frames_dir / f"expected_shot_{idx:02d}_last.png"
                if expected_frame.exists():
                    expected_size = expected_frame.stat().st_size / 1024
                    actual_size = Path(frame_path).stat().st_size / 1024
                    print(f"   📊 Expected: {expected_size:.1f} KB | Actual: {actual_size:.1f} KB")
                    
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        print(f"\n   Summary: {len(continuity_results)}/{min(3, len(test_videos))} frames extracted")
        print()
    
    # Summary
    print("=" * 70)
    print("✅ Frame extraction tests complete!")
    print("=" * 70)
    print(f"\n📂 Extracted frames location:")
    print(f"   ./jobs/test_extraction/frames/")
    print(f"   ./jobs/test_continuity/frames/")
    
    if has_expected_frames:
        print(f"\n📸 Expected frames location:")
        print(f"   ./tests/fixtures/frames/")
    
    print(f"\n💡 To view extracted frames:")
    print(f"   open ./jobs/test_extraction/frames/")
    
    if has_expected_frames:
        print(f"\n💡 To compare frames visually:")
        print(f"   open ./jobs/test_extraction/frames/ ./tests/fixtures/frames/")


if __name__ == "__main__":
    asyncio.run(test_frame_extraction())
