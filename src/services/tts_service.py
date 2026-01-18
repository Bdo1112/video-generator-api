#!/usr/bin/env python3
"""
Text-to-Speech Service
======================
Why this file exists:
- Wraps TTS logic from text_to_speech.py
- Uses KieClient (no code duplication)
- Generates voiceover audio via KIE/ElevenLabs
"""

import os
import tempfile
from src.services.kie_client import KieClient
from src.storage import StorageManager
from src.config import config
from src.models import VoiceoverResponse, JobStatus


class TTSService:
    """Service for generating voiceovers via KIE/ElevenLabs API"""

    def __init__(self, kie_client: KieClient, storage: StorageManager):
        self.kie = kie_client
        self.storage = storage
        self.model = config.TTS_MODEL
        self.default_voice = config.TTS_VOICE
        self.format = config.TTS_FORMAT

    async def generate_voiceover(
        self,
        job_id: str,
        text: str,
        voice: str = None,
        verbose: bool = True
    ) -> VoiceoverResponse:
        """
        Generate voiceover audio from text

        Args:
            job_id: Job ID for organizing outputs
            text: Text to convert to speech
            voice: Voice name (default: from config)
            verbose: Print progress

        Returns:
            VoiceoverResponse with audio path
        """
        voice = voice or self.default_voice

        # Check if voiceover already exists (for retry logic)
        audio_path = self.storage.get_audio_path(job_id)
        if os.path.exists(audio_path):
            if verbose:
                print(f"[tts] Voiceover already exists, skipping: {audio_path}")
            return VoiceoverResponse(
                job_id=job_id,
                audio_path=audio_path,
                status=JobStatus.COMPLETED
            )

        if verbose:
            print(f"[tts] Generating voiceover...")
            print(f"[tts] Voice: {voice}")
            print(f"[tts] Text length: {len(text)} chars")

        # Create KIE TTS task payload
        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": voice,
                "format": self.format,
            },
        }

        if verbose:
            print(f"[tts] Creating task...")

        # Create task
        task_id = await self.kie.create_task(payload)

        if verbose:
            print(f"[tts] Task created: {task_id}")
            print(f"[tts] Polling for completion...")

        # Poll until complete
        detail = await self.kie.poll_task(task_id, verbose=verbose)

        # Extract audio URL
        audio_url = self.kie.extract_result_url(detail)

        if verbose:
            print(f"[tts] Audio ready: {audio_url}")
            print(f"[tts] Downloading...")

        # Download to temporary location
        temp_path = os.path.join(tempfile.gettempdir(), f"audio_{task_id}.mp3")
        await self.kie.download_file(audio_url, temp_path)

        # Move to organized storage
        final_path = self.storage.save_audio(temp_path, job_id)

        if verbose:
            print(f"[tts] Saved: {final_path}")

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return VoiceoverResponse(
            job_id=job_id,
            audio_path=final_path,
            status=JobStatus.COMPLETED
        )

    async def generate_voiceover_from_prompts(
        self,
        job_id: str,
        prompts_file: str,
        voice: str = None,
        verbose: bool = True
    ) -> VoiceoverResponse:
        """
        Generate voiceover from voice_reader text in prompts JSON

        Args:
            job_id: Job ID
            prompts_file: Path to prompts JSON file
            voice: Voice name (default: from config)
            verbose: Print progress

        Returns:
            VoiceoverResponse with audio path
        """
        # Load prompts JSON
        data = self.storage.load_prompts_json(prompts_file)

        # Extract voice_reader text
        voice_reader_text = data.get("metadata", {}).get("voice_reader")

        if not voice_reader_text:
            raise ValueError("No voice_reader text found in prompts JSON")

        if verbose:
            print(f"[tts] Found voice_reader text: {len(voice_reader_text)} chars")

        # Generate voiceover
        return await self.generate_voiceover(
            job_id=job_id,
            text=voice_reader_text,
            voice=voice,
            verbose=verbose
        )
