"""
Fashn.ai Comprehensive Service — All API features excluding model-swap.

Provides async methods for every Fashn.ai model endpoint:
  - tryon-max          Virtual Try-On (model + product)
  - product-to-model   Product on generated model
  - face-to-model      Face image → upper-body avatar
  - model-create       Create AI models from model photos
  - edit               Post-processing / restyle
  - reframe            Aspect ratio change
  - image-to-video     Still image → short MP4
  - background-remove  Remove background → transparent PNG

Uses the unified POST /v1/run + polling pattern.
Auth: Bearer token via FASHN_API_KEY in .env.
"""

import os
import io
import json
import logging
import asyncio
import base64
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env files
env_dir = Path(__file__).resolve().parent.parent
load_dotenv(env_dir / "opentryon" / ".env")
load_dotenv(env_dir / "backend" / ".env")

logger = logging.getLogger(__name__)

BASE_URL = "https://api.fashn.ai/v1"


def _image_to_data_url(image_bytes: bytes, fmt: str = "png") -> str:
    """Convert raw image bytes to a data: URI."""
    ext = fmt.lower().replace("jpeg", "jpg")
    return f"data:image/{ext};base64,{base64.b64encode(image_bytes).decode('utf-8')}"


def _detect_format(image_bytes: bytes) -> str:
    """Detect image format from magic bytes. Defaults to png."""
    if image_bytes[:4] == b"\xff\xd8\xff":
        return "jpeg"
    if image_bytes[:4] == b"\x89PNG":
        return "png"
    if image_bytes[:4] == b"RIFF":
        return "webp"
    return "png"


class FashnAIClient:
    """Async client for all Fashn.ai model endpoints."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FASHN_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "FASHN_API_KEY is required. Get one at https://www.fashn.ai/"
            )
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── generic helpers ────────────────────────────────────────────────

    async def _run_model(
        self,
        model_name: str,
        inputs: dict,
        timeout: int = 180,
        poll_interval: float = 2.0,
    ) -> dict:
        """POST to /v1/run, then poll /v1/status/{id} until completion."""
        import httpx

        payload = {"model_name": model_name, "inputs": inputs}

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            logger.info("Fashn.ai %s: submitting request ...", model_name)
            resp = await client.post(
                f"{BASE_URL}/run",
                headers=self._headers,
                json=payload,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Fashn.ai {model_name} returned {resp.status_code}: {resp.text[:500]}"
                )
            data = resp.json()
            pred_id = data.get("id")
            if not pred_id:
                raise RuntimeError(
                    f"Fashn.ai {model_name} unexpected response: {data}"
                )

            # Poll status
            max_attempts = int(timeout / poll_interval)
            for attempt in range(max_attempts):
                await asyncio.sleep(poll_interval)
                status_resp = await client.get(
                    f"{BASE_URL}/status/{pred_id}",
                    headers=self._headers,
                )
                if status_resp.status_code != 200:
                    raise RuntimeError(
                        f"Fashn.ai status poll failed {status_resp.status_code}: {status_resp.text[:300]}"
                    )
                status_data = status_resp.json()
                status = status_data.get("status", "")

                if status == "completed":
                    logger.info(
                        "Fashn.ai %s completed (attempt %d)", model_name, attempt + 1
                    )
                    return status_data
                if status in ("failed", "error"):
                    err = status_data.get("error", {})
                    if isinstance(err, dict):
                        err_msg = err.get("message", str(err))
                    else:
                        err_msg = str(err)
                    raise RuntimeError(
                        f"Fashn.ai {model_name} failed: {err_msg}"
                    )
                # else starting / in_queue / processing — keep polling

            raise RuntimeError(
                f"Fashn.ai {model_name} timed out after {timeout}s"
            )

    @staticmethod
    def _extract_first_output(result: dict) -> str:
        """Get the first output URL or base64 string from a completed result."""
        outputs = result.get("output") or []
        if not outputs:
            raise RuntimeError("Fashn.ai returned no outputs")
        first = outputs[0] if isinstance(outputs, list) else outputs
        if not isinstance(first, str):
            raise RuntimeError(f"Fashn.ai unexpected output type: {type(first)}")
        return first

    # ── image helpers ──────────────────────────────────────────────────

    @staticmethod
    def _maybe_encode_image(
        image_bytes: Optional[bytes],
        fmt: Optional[str] = None,
    ) -> Optional[str]:
        """Encode raw bytes to data: URI, or return None."""
        if image_bytes is None:
            return None
        if fmt is None:
            fmt = _detect_format(image_bytes)
        return _image_to_data_url(image_bytes, fmt)

    @staticmethod
    def _prepare_image_input(
        image_value,
        field_name: str = "image",
    ) -> Optional[str]:
        """Convert a Pillow Image, bytes, or string to a data: URI or URL."""
        if image_value is None:
            return None
        if isinstance(image_value, bytes):
            return FashnAIClient._maybe_encode_image(image_value)
        if isinstance(image_value, str):
            # Already a URL or data: URI
            return image_value
        # Pillow Image
        import io as _io
        from PIL import Image

        buf = _io.BytesIO()
        image_value.save(buf, format="PNG")
        return _image_to_data_url(buf.getvalue(), "png")

    # ── Feature endpoints ──────────────────────────────────────────────

    async def try_on(
        self,
        product_image,  # bytes | str URL | PIL.Image
        model_image,    # bytes | str URL | PIL.Image
        prompt: Optional[str] = None,
        resolution: str = "1k",
        generation_mode: Optional[str] = None,
        num_images: int = 1,
        seed: Optional[int] = None,
        output_format: str = "png",
        return_base64: bool = False,
    ) -> bytes:
        """
        Virtual Try-On Max — place a product on a model image.
        Returns PNG/JPEG bytes.
        """
        inputs = {
            "product_image": self._prepare_image_input(product_image, "product_image"),
            "model_image": self._prepare_image_input(model_image, "model_image"),
            "num_images": num_images,
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if prompt:
            inputs["prompt"] = prompt
        if resolution:
            inputs["resolution"] = resolution
        if generation_mode:
            inputs["generation_mode"] = generation_mode
        if seed is not None:
            inputs["seed"] = seed

        result = await self._run_model("tryon-max", inputs)
        return await self._resolve_output(result, output_format)

    async def product_to_model(
        self,
        product_image,
        prompt: Optional[str] = None,
        image_prompt=None,
        face_reference=None,
        face_reference_mode: Optional[str] = None,
        background_reference=None,
        aspect_ratio: Optional[str] = None,
        resolution: str = "1k",
        generation_mode: Optional[str] = None,
        num_images: int = 1,
        seed: Optional[int] = None,
        output_format: str = "png",
        return_base64: bool = False,
    ) -> bytes:
        """
        Product to Model — generate a model wearing the product.
        Returns PNG/JPEG bytes.
        """
        inputs = {
            "product_image": self._prepare_image_input(product_image, "product_image"),
            "num_images": num_images,
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if prompt:
            inputs["prompt"] = prompt
        if image_prompt:
            inputs["image_prompt"] = self._prepare_image_input(image_prompt, "image_prompt")
        if face_reference:
            inputs["face_reference"] = self._prepare_image_input(face_reference, "face_reference")
        if face_reference_mode:
            inputs["face_reference_mode"] = face_reference_mode
        if background_reference:
            inputs["background_reference"] = self._prepare_image_input(background_reference, "background_reference")
        if aspect_ratio:
            inputs["aspect_ratio"] = aspect_ratio
        if resolution:
            inputs["resolution"] = resolution
        if generation_mode:
            inputs["generation_mode"] = generation_mode
        if seed is not None:
            inputs["seed"] = seed

        result = await self._run_model("product-to-model", inputs)
        return await self._resolve_output(result, output_format)

    async def face_to_model(
        self,
        face_image,
        prompt: Optional[str] = None,
        aspect_ratio: str = "2:3",
        resolution: str = "1k",
        generation_mode: Optional[str] = None,
        num_images: int = 1,
        seed: Optional[int] = None,
        output_format: str = "jpeg",
        return_base64: bool = False,
    ) -> bytes:
        """
        Face to Model — transform a face/headshot into an upper-body avatar.
        Returns image bytes.
        """
        inputs = {
            "face_image": self._prepare_image_input(face_image, "face_image"),
            "aspect_ratio": aspect_ratio,
            "num_images": num_images,
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if prompt:
            inputs["prompt"] = prompt
        if resolution:
            inputs["resolution"] = resolution
        if generation_mode:
            inputs["generation_mode"] = generation_mode
        if seed is not None:
            inputs["seed"] = seed

        result = await self._run_model("face-to-model", inputs)
        return await self._resolve_output(result, output_format)

    async def model_create(
        self,
        model_image,
        model_name: Optional[str] = None,
        output_format: str = "png",
        return_base64: bool = False,
    ) -> dict:
        """
        Model Create — create an AI model from model photos for use in
        virtual try-ons. This is an async queued operation.
        Returns the full result dict (may contain model_id or status info).
        """
        inputs = {
            "model_image": self._prepare_image_input(model_image, "model_image"),
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if model_name:
            inputs["name"] = model_name

        result = await self._run_model(
            "model-create",
            inputs,
            timeout=300,  # model creation can take longer
        )
        return result

    async def edit(
        self,
        image,
        prompt: str,
        mask=None,
        image_context=None,
        resolution: str = "1k",
        generation_mode: Optional[str] = None,
        num_images: int = 1,
        seed: Optional[int] = None,
        output_format: str = "png",
        return_base64: bool = False,
    ) -> bytes:
        """
        Edit — restyle / adjust / fix details while preserving subject.
        Returns image bytes.
        """
        inputs = {
            "image": self._prepare_image_input(image, "image"),
            "prompt": prompt,
            "num_images": num_images,
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if mask:
            inputs["mask"] = self._prepare_image_input(mask, "mask")
        if image_context:
            inputs["image_context"] = self._prepare_image_input(image_context, "image_context")
        if resolution:
            inputs["resolution"] = resolution
        if generation_mode:
            inputs["generation_mode"] = generation_mode
        if seed is not None:
            inputs["seed"] = seed

        result = await self._run_model("edit", inputs)
        return await self._resolve_output(result, output_format)

    async def reframe(
        self,
        image,
        aspect_ratio: str = "1:1",
        resolution: str = "1k",
        generation_mode: Optional[str] = None,
        num_images: int = 1,
        seed: Optional[int] = None,
        output_format: str = "png",
        return_base64: bool = False,
    ) -> bytes:
        """
        Reframe — change aspect ratio by smart crop or out-paint.
        Returns image bytes.
        """
        inputs = {
            "image": self._prepare_image_input(image, "image"),
            "aspect_ratio": aspect_ratio,
            "num_images": num_images,
            "output_format": output_format,
            "return_base64": return_base64,
        }
        if resolution:
            inputs["resolution"] = resolution
        if generation_mode:
            inputs["generation_mode"] = generation_mode
        if seed is not None:
            inputs["seed"] = seed

        result = await self._run_model("reframe", inputs)
        return await self._resolve_output(result, output_format)

    async def image_to_video(
        self,
        image,
        prompt: Optional[str] = None,
        duration: int = 5,
        resolution: str = "720p",
        return_base64: bool = False,
    ) -> str:
        """
        Image to Video — animate a still image into a short MP4 clip.
        Returns a URL (string) or base64 data URI string.
        """
        inputs = {
            "image": self._prepare_image_input(image, "image"),
            "duration": duration,
            "resolution": resolution,
        }
        if prompt:
            inputs["prompt"] = prompt

        result = await self._run_model(
            "image-to-video",
            inputs,
            timeout=300,  # video takes longer
            poll_interval=5.0,
        )
        return self._extract_first_output(result)

    async def background_remove(
        self,
        image,
        return_base64: bool = False,
    ) -> bytes:
        """
        Background Remove — remove background, return transparent PNG bytes.
        """
        inputs = {
            "image": self._prepare_image_input(image, "image"),
            "return_base64": return_base64,
        }
        result = await self._run_model(
            "background-remove",
            inputs,
            timeout=30,  # fast endpoint
            poll_interval=0.5,
        )
        return await self._resolve_output(result, "png")

    # ── output resolution ──────────────────────────────────────────────

    async def _resolve_output(self, result: dict, fmt: str = "png") -> bytes:
        """Fetch output URL or decode base64 into bytes."""
        output = self._extract_first_output(result)
        if output.startswith("data:"):
            # Base64 inline
            _, b64 = output.split(",", 1)
            return base64.b64decode(b64)
        if output.startswith("http"):
            # CDN URL — download
            import httpx

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(output)
                resp.raise_for_status()
                return resp.content
        raise RuntimeError(f"Unknown output format: {output[:80]}")


# Singleton
fashn_client: Optional[FashnAIClient] = None


def get_fashn_client() -> Optional[FashnAIClient]:
    """Get or create the singleton FashnAIClient."""
    global fashn_client
    if fashn_client is None:
        try:
            fashn_client = FashnAIClient()
        except RuntimeError as e:
            logger.warning("Fashn.ai client not available: %s", e)
            return None
    return fashn_client
