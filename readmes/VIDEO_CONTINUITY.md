# Video Continuity Implementation Guide

## 🎯 Overview

This project now supports **video-to-video continuity** by extracting the last frame from each video and using it to generate the next video, creating smooth visual transitions across the entire sequence.

---

## ✅ What's Implemented

### 1. **Frame Extraction Service**
- **File:** `src/services/frame_extractor_service.py`
- Extracts last frame using FFmpeg's reverse filter
- Saves frames as PNG in `jobs/{job_id}/frames/`

### 2. **Two Video Generation Methods**
- **File:** `src/services/video_service.py`

**Method 1: Text-to-Video** (Shot 1 only)
```python
generate_video_from_text(job_id, shot_number, prompt, duration, subject)
# Uses: sora-2-text-to-video model
```

**Method 2: Image-to-Video** (Shots 2-6)
```python
generate_video_from_image(job_id, shot_number, prompt, duration, subject, image_path)
# Uses: sora-2-image-to-video model
```

### 3. **Automatic Continuity**
The `generate_videos_from_prompts()` method automatically:
1. Generates Shot 1 from text
2. Extracts last frame from Shot 1
3. Generates Shot 2 from that frame
4. Extracts last frame from Shot 2
5. Continues for all shots...

---

## ⚠️ **IMPORTANT: KIE API Fix Needed**

**Current Error:**
```
'image_url is required'
```

**The Issue:**
KIE API expects `image_url` (URL to an image), not `image` (base64 data).

**Fix Required:**
We need to either:
1. Upload the image first and get a URL
2. Host the image somewhere accessible
3. Use a different parameter format

**Location to fix:** `src/services/video_service.py` line ~150

---

## 📊 Current Workflow

```
Shot 1: TEXT-TO-VIDEO ✅
  • Generate from prompt only
  • Extract last frame → shot_01_last.png
  
Shot 2: IMAGE-TO-VIDEO ❌ (API error - needs fix)
  • Load shot_01_last.png
  • Convert to base64
  • Send to KIE API → ERROR: "image_url is required"
  • Falls back to TEXT-TO-VIDEO ✅
```

---

## 🔧 Testing

Your recent test showed:
- ✅ Shot 1: TEXT-TO-VIDEO worked perfectly
- ✅ Frame extraction worked (shot_01_last.png created)
- ❌ Shot 2: IMAGE-TO-VIDEO failed (wrong parameter)
- ✅ Fallback to TEXT-TO-VIDEO worked

---

## 📁 File Structure

```
jobs/{job_id}/
├── videos/
│   ├── 01_Subject.mp4
│   ├── 02_Subject.mp4
│   └── concatenated.mp4
├── frames/              # NEW!
│   ├── shot_01_last.png
│   └── shot_02_last.png
├── audio/
└── final/
```

---

## 🚀 Next Steps

1. **Fix KIE API Integration**
   - Research KIE's image-to-video documentation
   - Determine if we need to upload images first
   - Update `generate_video_from_image()` method

2. **Test Full Continuity**
   - Once fixed, test with 2-3 clips
   - Verify visual continuity
   - Check API costs

---

## 📝 API Endpoints

- `/api/prompts` - Generate prompts
- `/api/create_videos` - Generate ALL videos with continuity
- `/api/combine_videos` - Concatenate clips
- `/api/create_voice` - Generate voiceover
- `/api/merge_final` - Merge audio + video

---

## 🎬 Files Modified

- `src/services/frame_extractor_service.py` - NEW
- `src/services/video_service.py` - Refactored
- `src/services/kie_client.py` - Added image_to_base64()
- `src/storage.py` - Added frame management
- `api/main.py` - Renamed endpoint to /api/create_videos

**Everything is ready except for the KIE API parameter fix!**
