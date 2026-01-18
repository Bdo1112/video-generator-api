#!/usr/bin/env python3
"""
Configuration Management
========================
Why this file exists:
- Single source of truth for all settings (no more loading config.env in 5 different files)
- Type-safe using Pydantic (catches config errors early)
- Easy to inject into FastAPI routes and CLI scripts
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from config.env"""

    model_config = SettingsConfigDict(
        env_file='config.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

    # API Keys
    ANTHROPIC_API_KEY: str = ''
    KIE_API_KEY: str = ''

    # Video Structure
    CLIP_DURATION: int = 10
    NUM_SHOTS: int = 6

    @property
    def TOTAL_DURATION(self) -> int:
        return self.CLIP_DURATION * self.NUM_SHOTS

    # Visual Style
    ASPECT_RATIO: str = '9:16'
    DEFAULT_FILM_STOCK: str = 'Kodak Vision3 500T'
    DEFAULT_GRAIN: str = 'moderate'
    DEFAULT_COLOR_TEMP: str = '3200K'

    # Style Presets (optional overrides)
    FORCE_STYLE_PRESET: str = ''
    CUSTOM_COLOR_PALETTE: str = ''
    CUSTOM_ATMOSPHERE: str = ''

    # Narrative
    NARRATIVE_BEATS: str = 'HOOK,CONTEXT,RISING ACTION,ESCALATION,CLIMAX,RESOLUTION'
    TENSION_LEVELS: str = '3,4,6,8,10,5'

    @property
    def narrative_beats_list(self) -> List[str]:
        return self.NARRATIVE_BEATS.split(',')

    @property
    def tension_levels_list(self) -> List[int]:
        return [int(x) for x in self.TENSION_LEVELS.split(',')]

    # Camera
    DEFAULT_LENS: str = '35mm anamorphic'
    DEFAULT_DOF: str = 'shallow f/2.0'

    # Model Settings
    CLAUDE_MODEL: str = 'claude-sonnet-4-20250514'
    MAX_TOKENS: int = 8000
    TEMPERATURE: float = 0.7

    # Video API
    VIDEO_API_MODEL: str = 'kling-2.6/text-to-video'
    VIDEO_ASPECT_RATIO: str = '9:16'
    KIE_CREATE_TASK_URL: str = 'https://api.kie.ai/api/v1/jobs/createTask'
    KIE_GET_TASK_DETAIL_URL: str = 'https://api.kie.ai/api/v1/jobs/recordInfo'

    # TTS
    TTS_VOICE: str = 'Bill'
    TTS_FORMAT: str = 'mp3'
    TTS_MODEL: str = 'elevenlabs/text-to-speech-multilingual-v2'

    # Output
    OUTPUT_DIR: str = './output'
    DOWNLOADS_DIR: str = './downloads'
    JOBS_DIR: str = './jobs'

    # Advanced
    CIRCULAR_NARRATIVE: bool = True
    MIN_CHARACTERS: int = 1
    MAX_CHARACTERS: int = 3
    MIN_LOCATIONS: int = 1
    MAX_LOCATIONS: int = 3
    VERBOSE: bool = False

    # Server Configuration
    SERVER_URL: str = 'http://localhost:8000'


# Singleton instance - import this everywhere
config = Config()
