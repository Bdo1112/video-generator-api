#!/usr/bin/env python3
"""
Prompt Generation Service
==========================
Why this file exists:
- Migrates all the logic from article_to_prompts.py into a reusable service
- Can be called from CLI or FastAPI
- Handles Claude API interaction to generate video prompts from articles

This is the MOST IMPORTANT service - it generates the sophisticated prompts
needed for consistent character/location rendering across video clips.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any, Optional
import anthropic

from src.config import config
from src.storage import StorageManager
from src.models import PromptGenerationResponse, JobStatus


class PromptService:
    """Service for generating video prompts from news articles using Claude API"""

    def __init__(self, storage: StorageManager, anthropic_api_key: Optional[str] = None):
        """
        Initialize the prompt service

        Args:
            storage: StorageManager instance for saving outputs
            anthropic_api_key: Optional API key (defaults to config)
        """
        self.storage = storage
        self.api_key = anthropic_api_key or config.ANTHROPIC_API_KEY

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required. Set in config.env or pass to constructor")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _get_system_prompt(self, num_shots: int, clip_duration: int) -> str:
        """Generate system prompt for Claude"""
        total_duration = num_shots * clip_duration
        beats = config.narrative_beats_list

        return f"""You are a cinematic video director who converts news articles into visual storytelling.

Your job: Analyze a news article and generate {num_shots} video prompts ({clip_duration} seconds each = {total_duration} second total video) with:
1. Consistent visual style throughout
2. Frame-to-frame continuity between shots
3. Proper narrative arc ({' → '.join(beats)})

You must output valid JSON only. No other text."""

    def _get_analysis_prompt(self, article_text: str, num_shots: int, clip_duration: int) -> str:
        """Generate analysis prompt for Claude with full instructions"""

        total_duration = num_shots * clip_duration
        beats = config.narrative_beats_list
        tension_levels = config.tension_levels_list

        # Build narrative beats description
        beats_description = "\n".join([
            f"- {beat} (Shot {i+1}): Tension level {tension_levels[i]}/10"
            for i, beat in enumerate(beats[:num_shots])
        ])

        # Build prompts array template
        prompts_template = []
        for i in range(num_shots):
            beat = beats[i] if i < len(beats) else f"SHOT_{i+1}"
            is_first = i == 0

            prompt_obj = {
                "shot_number": i + 1,
                "narrative_beat": beat,
                "duration": clip_duration,
                "is_image_to_video": not is_first,
                "shot_type": "ECU / CU / MS / WS / EWS / POV / OTS",
                "subject": "what the camera is focused on",
                "action": "what happens during this shot",
                "characters_in_shot": ["character_id"],
                "locations_in_shot": ["location_id"],
                "camera_movement": "specific movement type",
                "camera_start": "MUST match previous shot's ends_with" if not is_first else "where camera begins",
                "camera_end": "where camera ends",
                "emotion": "the feeling of this moment",
                "starts_with": "MUST match previous shot's ends_with exactly" if not is_first else "describe opening image",
                "ends_with": "CRITICAL: exactly how this shot ends"
            }
            prompts_template.append(prompt_obj)

        # Style overrides
        style_override = ""
        if config.FORCE_STYLE_PRESET:
            style_override = f"\nFORCED STYLE PRESET: Use the '{config.FORCE_STYLE_PRESET}' visual style."
        if config.CUSTOM_COLOR_PALETTE:
            style_override += f"\nFORCED COLOR PALETTE: {config.CUSTOM_COLOR_PALETTE}"
        if config.CUSTOM_ATMOSPHERE:
            style_override += f"\nFORCED ATMOSPHERE: {config.CUSTOM_ATMOSPHERE}"

        circular_note = ""
        if config.CIRCULAR_NARRATIVE:
            circular_note = f"\n10. Shot {num_shots} should visually callback to Shot 1 (circular narrative)"

        return f"""Analyze this news article and generate video prompts.

<article>
{article_text}
</article>

<configuration>
- Number of shots: {num_shots}
- Duration per shot: {clip_duration} seconds
- Total duration: {total_duration} seconds
- Aspect ratio: {config.ASPECT_RATIO}
- Default film stock: {config.DEFAULT_FILM_STOCK}
- Default lens: {config.DEFAULT_LENS}
- Default depth of field: {config.DEFAULT_DOF}
- Grain level: {config.DEFAULT_GRAIN}
- Color temperature: {config.DEFAULT_COLOR_TEMP}
- Characters: {config.MIN_CHARACTERS}-{config.MAX_CHARACTERS}
- Locations: {config.MIN_LOCATIONS}-{config.MAX_LOCATIONS}
</configuration>
{style_override}

Generate a complete JSON response with this exact structure:

{{
  "metadata": {{
    "title": "A cinematic title for this video",
    "total_duration": {total_duration},
    "clip_duration": {clip_duration},
    "num_shots": {num_shots},
    "voice_reader": "VOICEOVER SCRIPT HERE - See requirements below"
  }},

  "analysis": {{
    "category": "one of: economic_crisis, natural_disaster, protest, conflict, human_interest, technology, politics, crime, health, sports, other",
    "primary_emotion": "dominant feeling: desperate, hopeful, tragic, triumphant, tense, chaotic, intimate, inspiring, somber, urgent",
    "secondary_emotion": "supporting emotion",
    "location": "specific place",
    "time_period": "when this takes place",
    "weather_mood": "atmospheric conditions"
  }},

  "style_bible": {{
    "aspect_ratio": "{config.ASPECT_RATIO}",
    "color_palette": "describe colors + mood",
    "film_stock": "film stock choice",
    "color_temperature": "color temp",
    "lens_style": "lens choice",
    "depth_of_field": "DOF setting",
    "camera_movement": "overall movement style",
    "lighting_style": "lighting approach",
    "atmosphere": "atmospheric elements",
    "grain_texture": "grain level"
  }},

  "characters": [
    {{
      "id": "unique_id",
      "archetype": "government_official / protester / civilian / authority_figure / victim / witness",
      "role": "protagonist / antagonist / witness / crowd",
      "age_range": "age range",
      "gender": "gender presentation",
      "ethnicity_region": "ethnic/regional appearance relevant to story location",
      "physical_description": "DETAILED: face shape, hair, skin tone, build, height, facial features - MUST be vivid enough for AI to generate consistently",
      "clothing": "HIGHLY SPECIFIC: exact garments, colors, materials, condition, accessories",
      "distinguishing_features": "unique visual identifiers that make this character recognizable across shots",
      "emotional_state": "demeanor and expression",
      "character_consistency_note": "Key visual anchors for AI: [most distinctive features to maintain across shots]"
    }}
  ],

  "locations": [
    {{
      "id": "unique_id",
      "name": "Location Name",
      "description": "overall feel",
      "key_elements": "visual anchors",
      "color_notes": "dominant colors",
      "lighting_notes": "light behavior"
    }}
  ],

  "prompts": {json.dumps(prompts_template, indent=4)}
}}

CRITICAL RULES:
1. Each shot's "starts_with" MUST exactly match the previous shot's "ends_with"
2. Shot 1 is text-to-video (is_image_to_video: false), shots 2-{num_shots} are image-to-video (is_image_to_video: true)
3. DO NOT generate the "prompt" field - it will be auto-generated from the data you provide
4. Create {config.MIN_CHARACTERS}-{config.MAX_CHARACTERS} characters based on the article
5. Create {config.MIN_LOCATIONS}-{config.MAX_LOCATIONS} locations based on the article
6. Visual style must match emotional tone
7. Each shot is exactly {clip_duration} seconds{circular_note}
8. Whole article must be covered across the shots
9. Whole summary of the article in the VOICE_READER field

VOICE_READER REQUIREMENTS (CRITICAL):
1) Write a single voiceover script that summarizes the entire article for a short-form video.
2) Target length: exactly 60 seconds when read aloud at a natural news pace (about 120 words).
   - Hard limit: 110 words maximum.
   - Minimum: 90 words.
3) Style: clear, neutral, "breaking news" tone. No hype, no jokes.
4) Must cover: who/what happened, where, when (if available), key numbers/facts (if present), what is known vs unknown, and what happens next.
5) Must not use real people's names. Use generic roles (e.g., "a senior official", "witnesses", "authorities", "economists").
6) No quotes. No bullet points. No emojis. No headings. One paragraph only.
7) Present tense for the hook (first sentence), then past tense for details.
8) End with a tight closing line that signals the video is ending (e.g., "That's the latest so far.").

CHARACTER GENERATION RULES - CRITICAL FOR AI VIDEO:
❌ NEVER use real people's names (no "President Masoud Pezeshkian", "Joe Biden", etc.)
✅ ALWAYS use generic archetypes with ultra-detailed physical descriptions
✅ Example: "A distinguished Middle Eastern man in his early 60s, salt-and-pepper beard neatly trimmed, deep-set brown eyes, prominent cheekbones, olive skin, wearing a dark navy suit with white dress shirt"
✅ Include EVERY visual detail: exact hair style, facial hair, skin tone, body type, clothing colors/materials
✅ Make descriptions SO detailed that the AI can generate the same face across multiple shots
✅ Focus on visual features, not names or titles

NARRATIVE BEATS:
{beats_description}

Output only valid JSON. No markdown, no explanation, just the JSON object."""

    def _compose_comprehensive_prompt(
        self,
        shot: dict,
        characters: list,
        locations: list,
        style_bible: dict
    ) -> str:
        """
        Compose a comprehensive prompt from shot data, characters, locations, and style bible.
        This is CRITICAL for AI video quality - creates structured, detailed prompts.
        """
        is_image_to_video = shot.get('is_image_to_video', False)
        prompt_parts = []

        # 1. IMAGE-TO-VIDEO PREFIX (for shots 2+)
        if is_image_to_video:
            prompt_parts.append("[IMAGE-TO-VIDEO: Starting from previous frame]")
            prompt_parts.append("")

        # 2. OPENING FRAME DESCRIPTION
        prompt_parts.append(f"OPENING: {shot['starts_with']}")
        prompt_parts.append("")

        # 3. CHARACTER DETAILS
        if shot.get('characters_in_shot'):
            prompt_parts.append("CHARACTERS:")
            for char_id in shot['characters_in_shot']:
                char = next((c for c in characters if c['id'] == char_id), None)
                if char:
                    prompt_parts.append(f"- {char['physical_description']}")
                    prompt_parts.append(f"  Wearing: {char['clothing']}")
                    prompt_parts.append(f"  Distinctive: {char['distinguishing_features']}")
                    prompt_parts.append(f"  Emotion: {char['emotional_state']}")
                    prompt_parts.append(f"  Key anchors: {char['character_consistency_note']}")
            prompt_parts.append("")

        # 4. LOCATION DETAILS
        if shot.get('locations_in_shot'):
            prompt_parts.append("LOCATION:")
            for loc_id in shot['locations_in_shot']:
                loc = next((l for l in locations if l['id'] == loc_id), None)
                if loc:
                    prompt_parts.append(f"- {loc['name']}: {loc['description']}")
                    prompt_parts.append(f"  Key elements: {loc['key_elements']}")
                    prompt_parts.append(f"  Colors: {loc['color_notes']}")
                    prompt_parts.append(f"  Lighting: {loc['lighting_notes']}")
            prompt_parts.append("")

        # 5. ACTION & CAMERA MOVEMENT
        prompt_parts.append("ACTION:")
        prompt_parts.append(f"- {shot['action']}")
        prompt_parts.append(f"- Camera: {shot['camera_movement']}")
        prompt_parts.append(f"- Shot type: {shot['shot_type']}")
        prompt_parts.append(f"- From: {shot['camera_start']}")
        prompt_parts.append(f"- To: {shot['camera_end']}")
        prompt_parts.append("")

        # 6. EMOTION & ATMOSPHERE
        prompt_parts.append("MOOD:")
        prompt_parts.append(f"- Primary emotion: {shot['emotion']}")
        prompt_parts.append(f"- Atmosphere: {style_bible['atmosphere']}")
        prompt_parts.append(f"- Color palette: {style_bible['color_palette']}")
        prompt_parts.append("")

        # 7. TECHNICAL SPECIFICATIONS
        prompt_parts.append("TECHNICAL:")
        prompt_parts.append(f"- Film stock: {style_bible['film_stock']}")
        prompt_parts.append(f"- Lens: {style_bible['lens_style']}")
        prompt_parts.append(f"- Depth of field: {style_bible['depth_of_field']}")
        prompt_parts.append(f"- Color temperature: {style_bible['color_temperature']}")
        prompt_parts.append(f"- Grain: {style_bible['grain_texture']}")
        prompt_parts.append(f"- Lighting: {style_bible['lighting_style']}")
        prompt_parts.append("")

        # 8. ENDING FRAME DESCRIPTION
        prompt_parts.append(f"CLOSING: {shot['ends_with']}")
        prompt_parts.append("")

        # 9. END FRAME REQUIREMENT TAG
        prompt_parts.append("[END FRAME REQUIREMENT]")

        return "\n".join(prompt_parts)

    def _add_comprehensive_prompts(self, result: dict) -> dict:
        """Add comprehensive prompts to each shot"""
        characters = result.get('characters', [])
        locations = result.get('locations', [])
        style_bible = result.get('style_bible', {})

        for shot in result.get('prompts', []):
            shot['prompt'] = self._compose_comprehensive_prompt(
                shot, characters, locations, style_bible
            )

        return result

    async def generate_prompts(
        self,
        article_text: str,
        title: str,
        num_shots: Optional[int] = None,
        clip_duration: Optional[int] = None,
        verbose: bool = True
    ) -> PromptGenerationResponse:
        """
        Generate video prompts from an article

        Args:
            article_text: The news article text
            num_shots: Number of shots (defaults to config)
            clip_duration: Duration per shot in seconds (defaults to config)
            verbose: Print progress messages

        Returns:
            PromptGenerationResponse with job_id and prompts file path
        """
        # Use defaults from config if not provided
        num_shots = num_shots or config.NUM_SHOTS
        clip_duration = clip_duration or config.CLIP_DURATION

        if verbose:
            print(f"[prompts] Analyzing article ({len(article_text)} chars)...")
            print(f"[prompts] Generating {num_shots} shots × {clip_duration}s = {num_shots * clip_duration}s video")
            print(f"[prompts] Using model: {config.CLAUDE_MODEL}")

        # Call Claude API
        message = self.client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.MAX_TOKENS,
            temperature=config.TEMPERATURE,
            system=self._get_system_prompt(num_shots, clip_duration),
            messages=[
                {
                    "role": "user",
                    "content": self._get_analysis_prompt(article_text, num_shots, clip_duration)
                }
            ]
        )

        # Extract and parse JSON
        response_text = message.content[0].text

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                raise ValueError(f"Failed to parse JSON from Claude response: {response_text[:500]}...")

        # Add metadata
        result["metadata"]["created_at"] = datetime.now().isoformat()
        result["metadata"]["model"] = config.CLAUDE_MODEL
        result["metadata"]["video_provider"] = "kling"

        # Add config snapshot
        result["config"] = {
            "clip_duration": clip_duration,
            "num_shots": num_shots,
            "aspect_ratio": config.ASPECT_RATIO,
        }

        if verbose:
            print(f"[prompts] Composing comprehensive prompts for each shot...")

        # Add comprehensive prompts
        result = self._add_comprehensive_prompts(result)

        # Generate job ID from title (deterministic for retries)
        job_id = self.storage.generate_job_id(title=title)
        prompts_file = self.storage.save_prompts_json(result, job_id)

        if verbose:
            print(f"[prompts] Saved: {prompts_file}")
            print(f"[prompts] Title: {result['metadata']['title']}")
            print(f"[prompts] Characters: {len(result['characters'])}")
            print(f"[prompts] Locations: {len(result['locations'])}")

        # Extract voice_reader text
        voice_reader_text = result.get("metadata", {}).get("voice_reader")

        # Update job metadata
        self.storage.update_job_status(
            job_id,
            "prompts_generated",
            title=result['metadata']['title'],
            num_shots=num_shots,
            total_duration=num_shots * clip_duration,
            voice_reader_text=voice_reader_text
        )

        return PromptGenerationResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            prompts_file=prompts_file,
            title=result['metadata']['title'],
            num_shots=num_shots,
            total_duration=num_shots * clip_duration,
            voice_reader_text=voice_reader_text
        )
