#!/usr/bin/env python3
"""
KIE API Client
==============
Why this file exists:
- Your old code duplicated API logic in make_a_request.py AND text_to_speech.py
- This client handles BOTH video generation and TTS using the same KIE API
- Async-ready for FastAPI background tasks
"""

import time
import random
import json
from typing import Dict, Any, Optional
import httpx


class KieClient:
    """Async client for KIE API (video generation and TTS)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.create_task_url = "https://api.kie.ai/api/v1/jobs/createTask"
        self.get_task_detail_url = "https://api.kie.ai/api/v1/jobs/recordInfo"

        # Polling configuration
        self.initial_delay = 2.0
        self.max_delay = 15.0
        self.timeout = 20 * 60  # 20 minutes

    def _headers(self) -> Dict[str, str]:
        """Generate request headers with auth"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _safe_get(self, d: Any, path: str) -> Optional[Any]:
        """Safely get nested dict value by dot-separated path"""
        cur = d
        for k in path.split("."):
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return None
        return cur

    async def create_task(self, payload: Dict[str, Any]) -> str:
        """
        Create a task on KIE API (video or TTS)

        Args:
            payload: Request payload with model and input

        Returns:
            task_id: Task ID to poll for results

        Raises:
            httpx.HTTPStatusError: If API request fails
            RuntimeError: If no task ID in response
        """
        print(f"[kie] Sending POST to: {self.create_task_url}")
        print(f"[kie] Payload model: {payload.get('model')}")
        
        try:
            async with httpx.AsyncClient() as client:
                print(f"[kie] Making HTTP request...")
                response = await client.post(
                    self.create_task_url,
                    headers=self._headers(),
                    json=payload,
                    timeout=60.0
                )
                print(f"[kie] Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                print(f"[kie] Response data: {data}")
        except httpx.TimeoutException as e:
            print(f"[kie] ERROR: Request timed out after 60s")
            raise
        except httpx.HTTPStatusError as e:
            print(f"[kie] ERROR: HTTP {e.response.status_code}")
            print(f"[kie] ERROR: Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"[kie] ERROR: {type(e).__name__}: {e}")
            raise

        # Check for KIE API error format (code: 500 in body even with HTTP 200)
        if isinstance(data, dict) and data.get('code') == 500:
            error_msg = data.get('msg', 'Unknown error')
            print(f"[kie] ERROR: KIE API returned error: {error_msg}")
            print(f"[kie] ERROR: Full response: {data}")
            raise RuntimeError(f"KIE API error: {error_msg} - Response: {data}")

        # Try multiple possible locations for task ID
        task_id = (
            self._safe_get(data, "data.taskId")
            or self._safe_get(data, "taskId")
            or self._safe_get(data, "data.id")
        )

        if not task_id:
            print(f"[kie] ERROR: No taskId found in response")
            raise RuntimeError(f"No taskId in API response: {data}")

        print(f"[kie] Task created successfully: {task_id}")
        return str(task_id)

    async def poll_task(self, task_id: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Poll task until completion

        Args:
            task_id: Task ID from create_task
            verbose: Print polling status

        Returns:
            Task detail dict with result

        Raises:
            RuntimeError: If task fails
            TimeoutError: If polling exceeds timeout
        """
        start_time = time.time()
        delay = self.initial_delay

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    self.get_task_detail_url,
                    headers=self._headers(),
                    params={"taskId": task_id},
                    timeout=30.0
                )
                response.raise_for_status()
                detail = response.json()

                state = self._safe_get(detail, "data.state")

                if verbose:
                    print(f"[poll] task={task_id} state={state}")

                if state == "success":
                    return detail

                if state == "fail":
                    fail_code = self._safe_get(detail, "data.failCode")
                    fail_msg = self._safe_get(detail, "data.failMsg")
                    raise RuntimeError(f"Task failed: code={fail_code}, msg={fail_msg}")

                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    raise TimeoutError(f"Polling timeout after {elapsed:.0f}s")

                # Exponential backoff with jitter
                await self._async_sleep(delay + random.uniform(0, 0.5))
                delay = min(self.max_delay, delay * 1.3)

    async def _async_sleep(self, seconds: float):
        """Async sleep helper"""
        import asyncio
        await asyncio.sleep(seconds)

    def extract_result_url(self, detail: Dict[str, Any]) -> str:
        """
        Extract result URL from task detail

        Args:
            detail: Task detail response from poll_task

        Returns:
            URL to download result file

        Raises:
            RuntimeError: If no result URL found
        """
        raw = self._safe_get(detail, "data.resultJson")
        if not raw:
            raise RuntimeError(f"Missing data.resultJson in detail: {detail}")

        parsed = json.loads(raw)
        urls = parsed.get("resultUrls") or []

        if not urls:
            raise RuntimeError(f"Missing resultUrls in parsed resultJson: {parsed}")

        return urls[0]

    async def download_file(self, url: str, path: str) -> None:
        """
        Download file from URL to local path

        Args:
            url: URL to download from
            path: Local path to save to
        """
        import os

        # Ensure directory exists
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, headers=self._headers(), timeout=300.0) as response:
                response.raise_for_status()

                with open(path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

    def image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to base64 string for API upload
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64-encoded string of the image
            
        Raises:
            FileNotFoundError: If image doesn't exist
        """
        import base64
        import os
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
        
        return encoded
