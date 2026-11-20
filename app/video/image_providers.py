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
                backoff = 2.0 * (2 ** (attempt - 1)) + random.uniform(0.5, 1.5)
                logger.warning(f"[{self.name}] Rate limit encountered: {rle}. Sleeping {backoff:.1f}s before retry...")
                time.sleep(backoff)
            except ProviderTimeoutError as te:
                last_error = te
                logger.warning(f"[{self.name}] Timeout on attempt {attempt}: {te}")
                time.sleep(1.0 * attempt)
            except ProviderConfigError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(f"[{self.name}] Generation attempt {attempt} failed: {exc}")
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

    def __init__(self, model: Optional[str] = None, timeout: int = 30, max_retries: int = 3, **kwargs: Any):
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
        encoded_prompt = urllib.parse.quote(prompt.strip())
        model_name = self.model or ""
        # Pollinations made 'flux' a paid tier (HTTP 402); default/turbo models are free
        model_param = (
            f"&model={model_name}"
            if model_name and model_name.lower() not in ("flux", "default", "none")
            else ""
        )
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&nologo=true&seed={gen_seed}{model_param}"
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
            if he.code == 429:
                raise ProviderRateLimitError(f"Pollinations API rate limit reached (HTTP {he.code}).")
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

    def generate_image_bytes(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        **kwargs: Any,
    ) -> bytes:
        gen_seed = seed if seed is not None else int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
        rng = random.Random(gen_seed)

        r_base = rng.randint(20, 180)
        g_base = rng.randint(20, 180)
        b_base = rng.randint(30, 200)

        img = Image.new("RGB", (width, height), (r_base, g_base, b_base))
        draw = ImageDraw.Draw(img)

        # Draw distinct pseudo-random spatial color blocks so spatial color embedding, dHash, and pHash are completely unique across seeds
        for row in range(8):
            for col in range(8):
                bx0 = int((width / 8) * col)
                by0 = int((height / 8) * row)
                bx1 = int((width / 8) * (col + 1))
                by1 = int((height / 8) * (row + 1))
                cell_r = rng.randint(15, 240)
                cell_g = rng.randint(15, 240)
                cell_b = rng.randint(15, 240)
                draw.rectangle([bx0, by0, bx1, by1], fill=(cell_r, cell_g, cell_b))

        # Draw decorative geometric elements to ensure distinct texture, variance, and visual identity
        margin = 60
        gold_color = (255, 215, 0)
        draw.rectangle([margin, margin, width - margin, height - margin], outline=gold_color, width=6)

        # Draw diagonal accent lines
        num_stripes = rng.randint(4, 12)
        for i in range(num_stripes):
            y_pos = int((height / (num_stripes + 1)) * (i + 1))
            shade = rng.randint(40, 220)
            draw.line([(margin + 10, y_pos), (width - margin - 10, y_pos + rng.randint(-50, 50))], fill=(shade, shade, 255), width=3)

        # Draw circles
        for _ in range(rng.randint(3, 8)):
            cx = rng.randint(margin + 50, width - margin - 50)
            cy = rng.randint(margin + 100, height - margin - 100)
            rad = rng.randint(25, 90)
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(rng.randint(180, 255), rng.randint(180, 255), 100), width=3)

        # Embed text identifying the scene prompt
        draw.text((margin + 30, margin + 50), "MOCK AI SCENE ASSET", fill=(255, 255, 255))
        draw.text((margin + 30, margin + 90), f"Seed: {gen_seed}", fill=(200, 200, 200))
        draw.text((margin + 30, margin + 130), prompt[:50], fill=(220, 220, 220))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        return buf.getvalue()


_PROVIDER_REGISTRY: Dict[str, Type[BaseImageProvider]] = {
    "pollinations": PollinationsImageProvider,
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

    p_name = (provider_name or os.getenv("IMAGE_PROVIDER", "pollinations")).strip().lower()
    if is_testing and not provider_name:
        p_name = "mock"

    cls = _PROVIDER_REGISTRY.get(p_name)
    if not cls:
        available = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ProviderConfigError(f"Unknown image provider '{p_name}'. Available providers: {available}")

    from config.settings import IMAGE_TIMEOUT, IMAGE_MAX_RETRIES, IMAGE_MODEL

    t_out = timeout if timeout is not None else IMAGE_TIMEOUT
    retries = max_retries if max_retries is not None else IMAGE_MAX_RETRIES
    m_name = model if model is not None else (None if p_name == "mock" else IMAGE_MODEL)

    return cls(model=m_name, timeout=t_out, max_retries=retries, **kwargs)
