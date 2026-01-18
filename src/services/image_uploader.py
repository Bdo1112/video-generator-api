"""
Image uploader to get HTTPS URLs for KIE API

Uses imgbb free API to upload frames and get HTTPS URLs
"""
import base64
import httpx
from pathlib import Path


class ImageUploader:
    """Upload images to get public HTTPS URLs"""
    
    def __init__(self, api_key: str = "d7a35e259ae5ed102e574996d69a5e42"):
        """
        Initialize uploader
        
        Args:
            api_key: ImgBB API key (free tier: 5000 uploads/month)
        """
        self.api_key = api_key
        self.upload_url = "https://api.imgbb.com/1/upload"
    
    async def upload_image(self, image_path: str, verbose: bool = False) -> str:
        """
        Upload image and get HTTPS URL
        
        Args:
            image_path: Local path to image file
            verbose: Print progress
            
        Returns:
            HTTPS URL to uploaded image
            
        Raises:
            RuntimeError: If upload fails
        """
        if verbose:
            print(f"[upload] Uploading {Path(image_path).name}...")
            print(f"[upload] Target: {self.upload_url}")
        
        try:
            # Read and encode image
            if verbose:
                print(f"[upload] Reading image file...")
            
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                image_size_kb = len(image_bytes) / 1024
                if verbose:
                    print(f"[upload] Image size: {image_size_kb:.1f} KB")
                
                image_data = base64.b64encode(image_bytes).decode('utf-8')
            
            # Upload to imgbb
            payload = {
                "key": self.api_key,
                "image": image_data,
            }
            
            if verbose:
                print(f"[upload] Sending HTTP POST request...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.upload_url,
                    data=payload,
                    timeout=30.0
                )
                
                if verbose:
                    print(f"[upload] Response status: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                if verbose:
                    print(f"[upload] Response data: {data}")
                    
        except httpx.TimeoutException as e:
            print(f"[upload] ERROR: Upload timed out after 30 seconds")
            raise RuntimeError(f"Image upload timed out: {e}")
        except httpx.HTTPStatusError as e:
            print(f"[upload] ERROR: HTTP {e.response.status_code}")
            print(f"[upload] ERROR: {e.response.text}")
            raise RuntimeError(f"Image upload HTTP error: {e}")
        except Exception as e:
            print(f"[upload] ERROR: {type(e).__name__}: {e}")
            raise RuntimeError(f"Image upload failed: {e}")
        
        # Check success
        if not data.get('success'):
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            print(f"[upload] ERROR: ImgBB API error: {error_msg}")
            raise RuntimeError(f"ImgBB upload failed: {error_msg}")
        
        # Extract HTTPS URL
        https_url = data['data']['url']
        
        if verbose:
            print(f"[upload] ✅ Uploaded to: {https_url}")
        
        return https_url
