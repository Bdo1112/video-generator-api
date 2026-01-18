# Image-to-Video Integration - Current Status

## 🎯 Goal
Enable video continuity by using the last frame of each video as the starting point for the next video.

---

## ✅ What's Working

### 1. Frame Extraction ✅
- Using FFmpeg reverse filter to get last frame
- Saves as PNG in `jobs/{job_id}/frames/`
- Tested and working perfectly

### 2. Two Separate Methods ✅
**Text-to-Video** (Shot 1):
```python
generate_video_from_text(...)
# Model: sora-2-text-to-video
# Input: prompt only
```

**Image-to-Video** (Shots 2+):
```python
generate_video_from_image(..., image_path)
# Model: sora-2-image-to-video  
# Input: image + prompt
```

### 3. Automatic Loop Logic ✅
- Shot 1: Text-to-video → extract frame
- Shot 2+: Use previous frame → image-to-video
- Graceful fallback if extraction fails

---

## ❌ **BLOCKER: KIE API Parameter Issue**

### Error from Test:
```
'image_url is required'
```

### What We're Sending:
```python
payload = {
    "model": "sora-2-image-to-video",
    "input": {
        "image": "data:image/png;base64,iVBORw0KGgo...",  # ❌ Wrong!
        "prompt": "...",
        ...
    }
}
```

### What KIE Expects:
```python
payload = {
    "model": "sora-2-image-to-video",
    "input": {
        "image_url": "https://...",  # ✅ Needs a URL, not base64!
        "prompt": "...",
        ...
    }
}
```

---

## 🔧 **TODO: Fix Required**

### Option 1: Upload Image First (Recommended)
1. Check if KIE has an image upload endpoint
2. Upload `shot_01_last.png` → get URL
3. Use that URL in video generation payload

### Option 2: Use External Hosting
1. Upload images to S3/Cloudinary/etc
2. Generate public URL
3. Use that URL in payload

### Option 3: Check KIE Docs Again
- Maybe there's a different parameter for base64
- Or different endpoint for image-to-video

---

## 📝 Test Results (2026-01-17)

```
✅ Shot 1: TEXT-TO-VIDEO worked
   Model: sora-2-text-to-video
   Generated: 01_Canadian_Prime_Minister...mp4
   
✅ Frame extraction worked
   Created: shot_01_last.png (1.2MB base64)
   
❌ Shot 2: IMAGE-TO-VIDEO failed
   Error: "image_url is required"
   
✅ Fallback worked
   Generated Shot 2 using text-to-video instead
```

---

## 🎯 Next Session Action Items

1. **Research KIE API docs** for image upload
2. **Find image upload endpoint** (if it exists)
3. **Update `generate_video_from_image()`** to:
   - Upload image first
   - Get URL
   - Use URL in payload
4. **Test with 2 clips** to verify continuity

---

## 📍 Code Location

**File to fix:** `src/services/video_service.py`  
**Method:** `generate_video_from_image()`  
**Line:** ~150

**Current code:**
```python
payload["input"]["image"] = f"data:image/png;base64,{image_base64}"
```

**Needs to be:**
```python
image_url = await upload_image_to_kie(image_path)  # Need to implement
payload["input"]["image_url"] = image_url
```

---

## 🚀 Everything Else is Ready!

- ✅ Frame extraction works perfectly
- ✅ Loop logic handles continuity
- ✅ Graceful fallback implemented
- ✅ Storage organized with frames/ directory
- ✅ API endpoint renamed to /api/create_videos

**Just need to fix the image upload part!**
