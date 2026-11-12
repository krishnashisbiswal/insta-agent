import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import errors, types

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    GEMINI_API_KEY,
    DEFAULT_GEMINI_MODEL,
    GEMINI_FALLBACK_MODELS,
    GEMINI_TEMPERATURE,
    GEMINI_MAX_RETRIES,
)

logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing! Please configure it in your .env file."
    )

# Initialize the official Google GenAI Client
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=20000),
        )
    return _client


def clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks from JSON response."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON text, handling markdown fences and minor trailing syntax."""
    cleaned = clean_json_text(response_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback regex extraction of first {...} or [...]
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse valid JSON from response: {cleaned[:200]}...")


def generate_text(
    prompt: str,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
) -> str:
    """
    Generate text using Gemini with multi-model fallback and retry logic.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    client = get_client()

    raw_models = []
    if model:
        raw_models.append(model)
    if DEFAULT_GEMINI_MODEL not in raw_models:
        raw_models.append(DEFAULT_GEMINI_MODEL)
    for fb in GEMINI_FALLBACK_MODELS:
        if fb not in raw_models:
            raw_models.append(fb)

    models_to_try = []
    for m in raw_models:
        norm = m if m.startswith("models/") else f"models/{m}"
        if norm not in models_to_try:
            models_to_try.append(norm)

    last_error = None

    for target_model in models_to_try:
        for attempt in range(GEMINI_MAX_RETRIES):
            try:
                config_args = {}
                if system_instruction:
                    config_args["system_instruction"] = system_instruction
                if GEMINI_TEMPERATURE is not None:
                    config_args["temperature"] = GEMINI_TEMPERATURE

                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config_args if config_args else None,
                )

                if response and response.text:
                    return response.text.strip()
                else:
                    raise RuntimeError(f"Gemini model {target_model} returned empty text.")

            except errors.APIError as exc:
                last_error = exc
                err_str = str(exc).lower()
                # If daily quota limit exceeded, retry won't help; switch model immediately
                if exc.code == 429 and ("per day" in err_str or "exceeded your current quota" in err_str or "retry in" in err_str):
                    logger.warning(
                        f"Model {target_model} daily quota exhausted. Falling back to next model..."
                    )
                    break

                # Transient error codes: 429 (RPM throttle), 500 (Internal), 502 (Bad Gateway), 503 (Unavailable), 504 (Deadline Exceeded)
                if exc.code in (429, 500, 502, 503, 504) and attempt < (GEMINI_MAX_RETRIES - 1):
                    wait_time = 3 if exc.code == 429 else 2
                    logger.warning(
                        f"Model {target_model} temporary error ({exc.code}). Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                elif exc.code in (404, 429, 500, 502, 503, 504):
                    logger.warning(
                        f"Model {target_model} failed with code {exc.code}. Falling back to next available model..."
                    )
                    break
                else:
                    raise RuntimeError(
                        f"Gemini API Error ({exc.code}): {exc.message}"
                    ) from exc

            except Exception as exc:
                last_error = exc
                logger.warning(f"Error calling {target_model}: {exc}. Trying next candidate...")
                break

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )


def generate_json(
    prompt: str,
    model: Optional[str] = None,
    system_instruction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate structured JSON using Gemini API and parse the result.
    """
    json_prompt = (
        f"{prompt}\n\n"
        f"CRITICAL: Respond ONLY with valid JSON. Do not include markdown preamble or notes."
    )
    text = generate_text(json_prompt, model=model, system_instruction=system_instruction)
    return parse_json_response(text)


def check_health() -> Dict[str, Any]:
    """Verify Gemini API connectivity and report active model."""
    try:
        client = get_client()
        result = generate_text("Ping! Respond with 'OK'.")
        return {
            "status": "healthy",
            "active_model": DEFAULT_GEMINI_MODEL,
            "response": result,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


if __name__ == "__main__":
    print("Testing Gemini Client...")
    health = check_health()
    print("Gemini Health Check:", health)
