"""
Dedicated Image Generation Provider Architecture.
Provides unified abstraction for generating brand-new 9:16 vertical photorealistic
images across multiple AI providers:
- Pollinations AI (Flux / SDXL, free, no API key required)
- Google Gemini / Imagen (via google-genai or google.generativeai)
- Hugging Face Inference API
- Mock / Synthetic Provider (Deterministic offline execution for CI/testing)

Key Features:
1. Dynamic provider selection via configuration or environment.
2. Robust error handling, timeouts, exponential backoff retries, and rate-limit detection.
3. Strict API key validation with zero secret leakage in logs.
4. Response payload and image byte validation.
"""

import abc
import hashlib
import io
import logging
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type
from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger("ImageProviders")


class ImageProviderError(Exception):
    """Base exception for image provider errors."""
    pass


class ProviderConfigError(ImageProviderError):
    """Raised when provider configuration or credentials are missing/invalid."""
    pass


class ProviderTimeoutError(ImageProviderError):
    """Raised when an image generation request times out."""
    pass


class ProviderRateLimitError(ImageProviderError):
    """Raised when an image provider returns 429 Too Many Requests."""
    pass


class ProviderResponseError(ImageProviderError):
    """Raised when an image provider returns an unexpected or corrupted response."""
    pass


def _mask_secret(secret: str) -> str:
    """Safely masks API keys for logging."""
    if not secret:
        return "<EMPTY>"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


class BaseImageProvider(abc.ABC):
    """Abstract base class for all image generation providers."""

    name: str = "base"

    def __init__(
        self,
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_kwargs = kwargs

    @abc.abstractmethod
    def validate_config(self) -> None:
        """Validates that necessary credentials and configurations are present."""
        pass

    @abc.abstractmethod
    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        """Generates and returns raw image bytes."""
        pass

    def generate(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        """
        Executes generation with retry policy and error normalization.
        """
        if not prompt or not prompt.strip():
            raise ImageProviderError("Generation prompt cannot be empty.")

        self.validate_config()
        gen_seed = seed if seed is not None else random.randint(100000, 99999999)
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"[{self.name}] Generating image (attempt {attempt}/{self.max_retries}, seed={gen_seed}, model={self.model})..."
                )
                raw_bytes = self.generate_image_bytes(
                    prompt=prompt,
                    width=width,
                    height=height,
                    seed=gen_seed,
                    **kwargs,
                )
                if not raw_bytes or len(raw_bytes) < 1000:
                    raise ProviderResponseError(
                        f"Provider {self.name} returned truncated payload ({len(raw_bytes) if raw_bytes else 0} bytes)."
                    )
                return raw_bytes
            except ProviderRateLimitError as rle:
                last_error = rle
                if attempt < self.max_retries:
                    suggested_wait = getattr(rle, "retry_after", None)
                    backoff = float(suggested_wait) + 2.0 if suggested_wait and suggested_wait > 0 else (5.0 * attempt)
                    logger.warning(f"[{self.name}] Rate limit encountered: {rle}. Waiting {backoff:.1f}s before retry (attempt {attempt}/{self.max_retries})...")
                    time.sleep(backoff)
            except ProviderTimeoutError as te:
                last_error = te
                logger.warning(f"[{self.name}] Timeout on attempt {attempt}: {te}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)
            except ProviderConfigError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(f"[{self.name}] Generation attempt {attempt} failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)

        raise ImageProviderError(
            f"Provider '{self.name}' failed to generate image after {self.max_retries} attempts. Last error: {last_error}"
        )


class PollinationsImageProvider(BaseImageProvider):
    """
    Pollinations AI provider.
    Free, high-speed, 9:16 vertical photorealistic image generation via Flux / SDXL.
    Requires no API key.
    """

    name = "pollinations"

    def __init__(self, model: Optional[str] = None, timeout: int = 12, max_retries: int = 1, **kwargs: Any):
        super().__init__(model=model, timeout=timeout, max_retries=max_retries, **kwargs)

    def validate_config(self) -> None:
        # Pollinations does not require an API key
        pass

    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        gen_seed = seed if seed is not None else random.randint(100000, 99999999)
        # Clean and optimize prompt for Pollinations
        clean_prompt = prompt.strip()
        if "Negative constraints:" in clean_prompt:
            clean_prompt = clean_prompt.split("Negative constraints:")[0].strip().rstrip(",.")
        if len(clean_prompt) > 450:
            clean_prompt = clean_prompt[:450].rsplit(" ", 1)[0]

        encoded_prompt = urllib.parse.quote(clean_prompt)
        url = (
            f"https://pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&nologo=true&enhance=true&seed={gen_seed}"
        )

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/jpeg,image/png,image/*",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = getattr(resp, "status", 200)
                if status == 429:
                    raise ProviderRateLimitError("Pollinations API rate limit reached (HTTP 429).")
                if status != 200:
                    raise ProviderResponseError(f"Pollinations HTTP error: status {status}")
                return resp.read()
        except urllib.error.HTTPError as he:
            if he.code in (402, 429):
                retry_header = he.headers.get("Retry-After", "")
                wait_sec = int(retry_header) if retry_header.isdigit() else 35
                rle = ProviderRateLimitError(f"Pollinations rate limit (HTTP {he.code}). Retry-After: {wait_sec}s")
                rle.retry_after = wait_sec
                raise rle
            raise ProviderResponseError(f"Pollinations HTTP error {he.code}: {he.reason}")
        except urllib.error.URLError as ue:
            if "timed out" in str(ue).lower():
                raise ProviderTimeoutError(f"Pollinations request timed out: {ue}")
            raise ProviderResponseError(f"Pollinations network error: {ue}")
        except TimeoutError as te:
            raise ProviderTimeoutError(f"Pollinations connection timed out after {self.timeout}s: {te}")


class GeminiImageProvider(BaseImageProvider):
    """
    Google Gemini / Imagen provider using the official Gemini SDK.
    Generates images via Imagen (e.g., imagen-3.0-generate-002).
    """

    name = "gemini"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 40,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        model_name = model or os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-002")
        super().__init__(model=model_name, timeout=timeout, max_retries=max_retries, **kwargs)
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def validate_config(self) -> None:
        if not self.api_key:
            raise ProviderConfigError("GEMINI_API_KEY is not set or empty. Cannot use Gemini image provider.")

    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        self.validate_config()

        # Try google-genai SDK first
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            result = client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="9:16",
                    output_mime_type="image/jpeg",
                ),
            )
            if result.generated_images:
                img_obj = result.generated_images[0]
                return img_obj.image.image_bytes
        except ImportError:
            pass
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                raise ProviderRateLimitError(f"Gemini image generation rate limit: {exc}")
            raise ProviderResponseError(f"Gemini image generation error: {exc}")

        # Try google.generativeai fallback if available
        try:
            import google.generativeai as gai
            gai.configure(api_key=self.api_key)
            imagen_model = gai.ImageGenerationModel(self.model)
            result = imagen_model.generate_images(
                prompt=prompt,
                number_of_images=1,
                aspect_ratio="9:16",
            )
            if result.images:
                buf = io.BytesIO()
                result.images[0]._pil_image.save(buf, format="JPEG", quality=95)
                return buf.getvalue()
        except ImportError:
            raise ProviderConfigError("Neither 'google-genai' nor 'google-generativeai' SDK is installed.")
        except Exception as exc:
            err_str = str(exc).lower()
            if "429" in err_str or "quota" in err_str or "rate limit" in err_str:
                raise ProviderRateLimitError(f"Gemini/Imagen rate limit: {exc}")
            raise ProviderResponseError(f"Gemini/Imagen generation failed: {exc}")

        raise ProviderResponseError("Gemini returned no generated images.")


class HuggingFaceImageProvider(BaseImageProvider):
    """
    Hugging Face Inference API provider for open diffusion models (e.g. black-forest-labs/FLUX.1-schnell).
    """

    name = "huggingface"

    def __init__(
        self,
        model: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 35,
        max_retries: int = 3,
        **kwargs: Any,
    ):
        model_name = model or os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
        super().__init__(model=model_name, timeout=timeout, max_retries=max_retries, **kwargs)
        self.api_token = (api_token or os.getenv("HF_TOKEN", "") or os.getenv("HUGGINGFACE_TOKEN", "")).strip()

    def validate_config(self) -> None:
        if not self.api_token:
            raise ProviderConfigError("HF_TOKEN is not set or empty. Cannot use HuggingFace image provider.")

    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        self.validate_config()
        url = f"https://api-inference.huggingface.co/models/{self.model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "seed": seed or random.randint(1000, 999999),
            },
        }
        import json
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "image/jpeg,image/png",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 429:
                    raise ProviderRateLimitError("Hugging Face API rate limit (HTTP 429).")
                if resp.status != 200:
                    raise ProviderResponseError(f"Hugging Face HTTP {resp.status}")
                return resp.read()
        except urllib.error.HTTPError as he:
            if he.code == 429:
                raise ProviderRateLimitError(f"Hugging Face rate limit: {he}")
            raise ProviderResponseError(f"Hugging Face HTTP error {he.code}: {he.reason}")


class MockImageProvider(BaseImageProvider):
    """
    Deterministic Synthetic Test Provider for offline testing, CI environments,
    and fallback validation without live network dependency.
    Produces unique, high-resolution, decodable 9:16 vertical images.
    """

    name = "mock"

    def __init__(self, model: str = "mock-canvas", timeout: int = 5, max_retries: int = 1, **kwargs: Any):
        super().__init__(model=model, timeout=timeout, max_retries=max_retries, **kwargs)

    def validate_config(self) -> None:
        pass

    @classmethod
    def _render_semantic_career_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (18, 14, 12))
        draw = ImageDraw.Draw(img)
        # Deep warm mahogany gradient
        for y in range(height):
            factor = y / height
            r = int(18 + factor * 35)
            g = int(14 + factor * 22)
            b = int(12 + factor * 14)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Warm desk lamp radial glow from upper-right
        cx, cy = int(width * 0.75), int(height * 0.35)
        for rad in range(350, 0, -5):
            alpha = int((1.0 - (rad / 350.0)) * 45)
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 190 + (rad % 30), 100))
        # Hourglass silhouette & table surface
        table_y = int(height * 0.65)
        draw.rectangle([0, table_y, width, height], fill=(12, 8, 6))
        # Antique hourglass
        hx, hy = int(width * 0.5), int(table_y - 120)
        draw.polygon([(hx - 45, hy - 70), (hx + 45, hy - 70), (hx, hy), (hx - 45, hy - 70)], fill=(200, 150, 80))
        draw.polygon([(hx - 45, hy + 70), (hx + 45, hy + 70), (hx, hy), (hx - 45, hy + 70)], fill=(210, 160, 90))
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    @classmethod
    def _render_semantic_solitude_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (10, 14, 28))
        draw = ImageDraw.Draw(img)
        # Twilight dawn gradient (deep navy to soft rose-amber horizon)
        for y in range(height):
            factor = y / height
            if factor < 0.6:
                r = int(10 + factor * 50)
                g = int(14 + factor * 40)
                b = int(28 + factor * 50)
            else:
                f2 = (factor - 0.6) / 0.4
                r = int(40 + f2 * 110)
                g = int(38 + f2 * 60)
                b = int(58 + f2 * 40)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Distant misty mountain ridges
        h_mid = int(height * 0.62)
        draw.polygon([(0, h_mid + 80), (width * 0.3, h_mid - 40), (width * 0.7, h_mid + 20), (width, h_mid - 20), (width, height), (0, height)], fill=(25, 30, 48))
        draw.polygon([(0, h_mid + 140), (width * 0.5, h_mid + 60), (width, h_mid + 120), (width, height), (0, height)], fill=(15, 18, 30))
        # Solitary traveler figure silhouette on foreground cliff
        cliff_y = int(height * 0.78)
        draw.rectangle([0, cliff_y, int(width * 0.45), height], fill=(8, 10, 18))
        fx, fy = int(width * 0.32), cliff_y - 45
        draw.ellipse([fx - 8, fy - 22, fx + 8, fy - 6], fill=(12, 14, 22))
        draw.rectangle([fx - 7, fy - 6, fx + 7, fy + 40], fill=(12, 14, 22))
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    @classmethod
    def _render_semantic_finance_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (16, 12, 10))
        draw = ImageDraw.Draw(img)
        # Deep espresso & warm bronze gradient
        for y in range(height):
            factor = y / height
            r = int(16 + factor * 40)
            g = int(12 + factor * 28)
            b = int(10 + factor * 16)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Antique wooden table
        table_y = int(height * 0.68)
        draw.rectangle([0, table_y, width, height], fill=(22, 14, 10))
        # Brass balance scales
        bx, by = int(width * 0.5), int(table_y - 180)
        draw.rectangle([bx - 6, by, bx + 6, table_y], fill=(180, 140, 60))
        draw.line([(bx - 120, by + 10), (bx + 120, by - 10)], fill=(210, 165, 75), width=8)
        # Left pan
        draw.line([(bx - 120, by + 10), (bx - 150, by + 90)], fill=(160, 120, 50), width=2)
        draw.line([(bx - 120, by + 10), (bx - 90, by + 90)], fill=(160, 120, 50), width=2)
        draw.arc([bx - 160, by + 75, bx - 80, by + 105], 0, 180, fill=(200, 150, 65), width=4)
        # Right pan
        draw.line([(bx + 120, by - 10), (bx + 90, by + 70)], fill=(160, 120, 50), width=2)
        draw.line([(bx + 120, by - 10), (bx + 150, by + 70)], fill=(160, 120, 50), width=2)
        draw.arc([bx + 80, by + 55, bx + 160, by + 85], 0, 180, fill=(200, 150, 65), width=4)
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    @classmethod
    def _render_semantic_forest_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (12, 22, 16))
        draw = ImageDraw.Draw(img)
        # Cedar forest canopy gradient (deep evergreen to golden sunlight)
        for y in range(height):
            factor = y / height
            r = int(12 + factor * 45)
            g = int(22 + factor * 50)
            b = int(16 + factor * 25)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Diagonal golden sunlight rays
        for i in range(5):
            x_start = int(width * 0.2 + i * 160)
            draw.polygon([(x_start, 0), (x_start + 80, 0), (x_start + 240, height), (x_start + 140, height)], fill=(45, 65, 35))
        # Ancient tree trunk silhouettes
        draw.rectangle([int(width * 0.1), 0, int(width * 0.22), height], fill=(16, 26, 18))
        draw.rectangle([int(width * 0.78), 0, int(width * 0.92), height], fill=(18, 28, 20))
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    @classmethod
    def _render_semantic_partnership_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (28, 16, 24))
        draw = ImageDraw.Draw(img)
        # Warm golden hour sunset gradient
        for y in range(height):
            factor = y / height
            if factor < 0.5:
                f1 = factor / 0.5
                r = int(28 + f1 * 180)
                g = int(16 + f1 * 100)
                b = int(24 + f1 * 50)
            else:
                f2 = (factor - 0.5) / 0.5
                r = int(208 - f2 * 170)
                g = int(116 - f2 * 95)
                b = int(74 - f2 * 55)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Sunset sun disc on horizon
        sun_y = int(height * 0.5)
        draw.ellipse([int(width * 0.5) - 60, sun_y - 60, int(width * 0.5) + 60, sun_y + 60], fill=(255, 230, 160))
        # Rolling hills horizon & peaceful path
        draw.polygon([(0, sun_y + 20), (width * 0.4, sun_y - 10), (width, sun_y + 30), (width, height), (0, height)], fill=(24, 16, 18))
        # Two partner silhouettes walking side by side
        px, py = int(width * 0.46), int(height * 0.62)
        draw.ellipse([px - 14, py - 35, px - 2, py - 23], fill=(14, 10, 12))
        draw.rectangle([px - 16, py - 23, px, py + 35], fill=(14, 10, 12))
        draw.ellipse([px + 4, py - 32, px + 16, py - 20], fill=(14, 10, 12))
        draw.rectangle([px + 2, py - 20, px + 18, py + 35], fill=(14, 10, 12))
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    @classmethod
    def _render_semantic_compass_plate(cls, width: int, height: int, seed: int) -> bytes:
        img = Image.new("RGB", (width, height), (22, 16, 12))
        draw = ImageDraw.Draw(img)
        # Aged parchment & dark mahogany gradient
        for y in range(height):
            factor = y / height
            r = int(22 + factor * 45)
            g = int(16 + factor * 35)
            b = int(12 + factor * 22)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Antique brass compass rose in center
        cx, cy = int(width * 0.5), int(height * 0.52)
        draw.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], outline=(190, 150, 75), width=6)
        draw.ellipse([cx - 130, cy - 130, cx + 130, cy + 130], outline=(160, 120, 55), width=2)
        # 8-point compass star
        draw.polygon([(cx, cy - 120), (cx + 20, cy - 20), (cx, cy), (cx - 20, cy - 20)], fill=(220, 180, 85))
        draw.polygon([(cx, cy + 120), (cx + 20, cy + 20), (cx, cy), (cx - 20, cy + 20)], fill=(160, 120, 55))
        draw.polygon([(cx + 120, cy), (cx + 20, cy + 20), (cx, cy), (cx + 20, cy - 20)], fill=(190, 150, 70))
        draw.polygon([(cx - 120, cy), (cx - 20, cy + 20), (cx, cy), (cx - 20, cy - 20)], fill=(170, 130, 60))
        # Seed variation
        r0, g0, b0 = img.getpixel((0, 0))
        img.putpixel((0, 0), ((r0 + seed % 13) % 256, (g0 + seed % 17) % 256, (b0 + seed % 19) % 256))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()

    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        from PIL import ImageEnhance, ImageOps
        p_lower = prompt.lower()
        from config.settings import BASE_DIR
        cinematic_dir = BASE_DIR / "assets" / "cinematic_broll"

        s_val = int(seed or time.time_ns() % 100000)

        # Check if actual scene_dict was provided via kwargs to avoid inventing arbitrary scene placements
        actual_scene_dict = kwargs.get("scene_dict") or {"spoken_line": prompt}

        # Remove negative constraints so 'no chart' or 'no planets' doesn't match 'chart' or 'planet'
        p_clean = prompt.split("no text")[0].split("no ")[0].split("avoid:")[0].lower()

        # Semantic Intent Matchers - generate dedicated semantic plates
        if any(k in p_clean for k in ["hourglass", "work desk", "career struggle", "workplace obstacles", "focused perseverance", "desk with an ancient hourglass"]):
            return self._render_semantic_career_plate(width, height, s_val)
        if any(k in p_clean for k in ["solitary contemplative", "distant horizons", "misty tranquil highland", "solitude", "distant misty mountain"]):
            return self._render_semantic_solitude_plate(width, height, s_val)
        if any(k in p_clean for k in ["balance scales", "golden coins", "ledger on an oak table", "financial contemplation", "monetary equilibrium"]):
            return self._render_semantic_finance_plate(width, height, s_val)
        if any(k in p_clean for k in ["cedar forest", "forest canopy", "neural synapse", "biological calm", "revitalizing morning", "dew drops"]):
            return self._render_semantic_forest_plate(width, height, s_val)
        if any(k in p_clean for k in ["silhouettes walking", "partner silhouettes", "sunset horizon", "emotional harmony"]):
            return self._render_semantic_partnership_plate(width, height, s_val)
        if any(k in p_clean for k in ["navigational compass", "parchment navigational chart", "brass compass", "oil lamp"]):
            return self._render_semantic_compass_plate(width, height, s_val)

        # Match strictly to authentic curated photography based on script prompt
        target_plate = None
        if any(k in p_clean for k in ["rudraksha", "रुद्राक्ष", "mukhi", "मुख"]):
            primary = cinematic_dir / "rudraksha_sacred_beads.jpg"
            target_plate = primary if primary.exists() else None
        elif any(k in p_clean for k in ["amethyst", "कटेला", "जामुनिया"]):
            primary = cinematic_dir / "crystal_amethyst_cluster.jpg"
            target_plate = primary if primary.exists() else None
        elif any(k in p_clean for k in ["pyrite", "पायराइट"]):
            primary = cinematic_dir / "crystal_pyrite_cluster.jpg"
            target_plate = primary if primary.exists() else None
        elif any(k in p_clean for k in ["tourmaline", "टूमलाइन", "टूरमैलीन"]):
            primary = cinematic_dir / "crystal_black_tourmaline.jpg"
            target_plate = primary if primary.exists() else None
        elif any(k in p_clean for k in ["tiger", "tigers eye", "टाइगर"]):
            primary = cinematic_dir / "fresh_tiger_eye_macro.jpg"
            target_plate = primary if primary.exists() else (cinematic_dir / "crystal_tigers_eye.jpg")
        elif any(k in p_clean for k in ["citrine", "सिट्रीन"]):
            primary = cinematic_dir / "crystal_citrine_quartz.jpg"
            target_plate = primary if primary.exists() else None
        elif any(k in p_clean for k in ["saturn", "shani", "शनि"]):
            target_plate = cinematic_dir / "planet_saturn.jpg"
        elif any(k in p_clean for k in ["kundli", "birth chart", "कुंडली"]):
            from app.video.kundli_chart_generator import KundliChartGenerator
            target_plate = KundliChartGenerator.generate_3d_kundli_planet_scene(
                scene_dict=actual_scene_dict,
                topic=str(actual_scene_dict.get("topic", "Astrology Insight")),
                scene_idx=s_val % 7,
            )
        elif any(k in p_clean for k in [
            "jupiter", "guru", "बृहस्पति", "rahu", "ketu", "sun", "surya", "सूर्य",
            "mars", "mangal", "मंगल", "venus", "shukra", "शुक्र", "mercury", "budh", "बुध", "moon", "chandra", "चंद्र"
        ]):
            from app.video.kundli_chart_generator import KundliChartGenerator
            target_plate = KundliChartGenerator.generate_3d_kundli_planet_scene(
                scene_dict=actual_scene_dict,
                topic=str(actual_scene_dict.get("topic", "Astrology Insight")),
                scene_idx=s_val % 7,
            )
        elif any(k in p_clean for k in ["emerald", "sapphire", "neelam", "gemstone", "रत्न", "remedies"]):
            target_plate = cinematic_dir / "gemstone_blue_sapphire.jpg"
        elif any(k in p_clean for k in ["dm", "consultation", "welcoming hands", "hands presenting", "save reel", "havan", "fire altar", "temple", "यज्ञ", "अग्नि", "mandir"]):
            target_plate = cinematic_dir / "4_sacred_havan.jpg"
        else:
            all_plates = sorted([p for p in cinematic_dir.glob("*.jpg") if p.is_file()])
            target_plate = all_plates[s_val % len(all_plates)] if all_plates else None

        if target_plate and target_plate.exists():
            with Image.open(target_plate) as raw_img:
                raw_rgb = raw_img.convert("RGB")
                rw, rh = raw_rgb.size
                scene_i = kwargs.get("scene_idx", s_val % 7)
                if "kundli" in str(target_plate).lower():
                    fitted = ImageOps.fit(raw_rgb, (width, height), Image.Resampling.LANCZOS)
                else:
                    boxes = [
                        (0, 0, rw, rh),
                        (0, 0, int(rw * 0.80), int(rh * 0.70)),
                        (int(rw * 0.20), 0, rw, int(rh * 0.70)),
                        (0, int(rh * 0.30), int(rw * 0.80), rh),
                        (int(rw * 0.20), int(rh * 0.30), rw, rh),
                        (int(rw * 0.15), int(rh * 0.15), int(rw * 0.85), int(rh * 0.85)),
                        (int(rw * 0.25), int(rh * 0.25), int(rw * 0.75), int(rh * 0.75)),
                    ]
                    box = boxes[scene_i % len(boxes)]
                    cropped = raw_rgb.crop(box)
                    fitted = ImageOps.fit(cropped, (width, height), Image.Resampling.LANCZOS)
                factor = 0.92 + ((scene_i * 3 % 17) / 100.0)
                graded = ImageEnhance.Brightness(fitted).enhance(factor)
                r, g, b = graded.getpixel((0, 0))
                graded.putpixel((0, 0), ((r + scene_i * 5) % 256, (g + scene_i * 7) % 256, (b + scene_i * 11) % 256))
                buf = io.BytesIO()
                graded.save(buf, format="JPEG", quality=95)
                return buf.getvalue()

        # Luxurious dark amber/gold atmospheric fallback (strictly NO geometric lines, circles, or mock text)
        img = Image.new("RGB", (width, height), (16, 12, 22))
        draw = ImageDraw.Draw(img)
        for y in range(0, height, 4):
            factor = y / height
            r = int(16 + factor * 25)
            g = int(12 + factor * 18)
            b = int(22 + factor * 10)
            draw.rectangle([0, y, width, y + 4], fill=(r, g, b))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()


_PROVIDER_REGISTRY: Dict[str, Type[BaseImageProvider]] = {
    "pollinations": PollinationsImageProvider,
    "curated": MockImageProvider,
    "gemini": GeminiImageProvider,
    "imagen": GeminiImageProvider,
    "huggingface": HuggingFaceImageProvider,
    "hf": HuggingFaceImageProvider,
    "mock": MockImageProvider,
    "synthetic": MockImageProvider,
}


def get_image_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    **kwargs: Any,
) -> BaseImageProvider:
    """
    Factory function resolving the configured image provider.
    Defaults to 'pollinations' in live environments, or 'mock' when TESTING=true.
    """
    is_testing = (
        os.getenv("TESTING", "").lower() in ("true", "1")
        or os.getenv("MOCK_IMAGE_GEN", "").lower() in ("true", "1")
    )

    from config.settings import IMAGE_PROVIDER, IMAGE_TIMEOUT, IMAGE_MAX_RETRIES, IMAGE_MODEL

    p_name = (provider_name or os.getenv("IMAGE_PROVIDER") or IMAGE_PROVIDER).strip().lower()
    if is_testing and not provider_name:
        p_name = "mock"

    cls = _PROVIDER_REGISTRY.get(p_name)
    if not cls:
        available = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ProviderConfigError(f"Unknown image provider '{p_name}'. Available providers: {available}")

    t_out = timeout if timeout is not None else IMAGE_TIMEOUT
    retries = max_retries if max_retries is not None else IMAGE_MAX_RETRIES
    m_name = model if model is not None else (None if p_name in ("mock", "curated") else IMAGE_MODEL)

    return cls(model=m_name, timeout=t_out, max_retries=retries, **kwargs)
