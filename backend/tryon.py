"""
Virtual Try-On Service — Multi-backend support.

Priority order (configured via env vars):
  1. Replicate (IDM-VTON) — best quality, $5 free credits → REPLICATE_API_TOKEN
  2. Fashn.ai — 25 free credits/month → FASHN_API_KEY
  3. Gradio HF Spaces (free, IDM-VTON) — no key needed, may be queued
  4. Segmind — needs $0.01/call credit top-up → SEGMIND_API_KEY

Only enabled backends that are configured. When multiple are configured,
the first available one in the priority order above is used.
"""

import os
import io
import logging
import base64
from pathlib import Path
from typing import Optional
from PIL import Image
from dotenv import load_dotenv

# Load both .env files — opentryon/.env (Segmind keys) and backend/.env (HF_TOKEN, etc.)
env_dir = Path(__file__).resolve().parent.parent
load_dotenv(env_dir / "opentryon" / ".env")
load_dotenv(env_dir / "backend" / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────

def _encode_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """Return a raw base64 string (no data: URI prefix)."""
    with io.BytesIO() as buf:
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode("utf-8")


def _resize(img: Image.Image, max_size: int = 1024) -> Image.Image:
    w, h = img.size
    if w >= h and w > max_size:
        nw = max_size
        nh = max(1, (max_size * h) // w)
        return img.resize((nw, nh), Image.Resampling.LANCZOS)
    if h > w and h > max_size:
        nh = max_size
        nw = max(1, (max_size * w) // h)
        return img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img


# ── Backend: Replicate (IDM-VTON) ────────────────────────────────────

class ReplicateVTONClient:
    """IDM-VTON via Replicate. Requires REPLICATE_API_TOKEN env var."""

    MODEL = "yisol/idm-vton:6d7eba65b6e18b6e9d0339ae14eae0d6bbf3e48c6e9e7b6a3b0c3b7b5f6a0b7"

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise RuntimeError(
                "REPLICATE_API_TOKEN is required. Get one at https://replicate.com/account"
            )
        import replicate
        self._client = replicate.Client(api_token=self.api_token)

    def generate(self, person: Image.Image, garment: Image.Image) -> Image.Image:
        person_b64 = _encode_base64(person)
        garment_b64 = _encode_base64(garment)
        logger.info("Calling Replicate IDM-VTON ...")
        output = self._client.run(
            self.MODEL,
            input={
                "human_image": f"data:image/png;base64,{person_b64}",
                "garment_image": f"data:image/png;base64,{garment_b64}",
                "category": "upper_body",
            },
        )
        if not output or not isinstance(output, list):
            raise RuntimeError(f"Replicate returned unexpected output: {output}")
        url = output[0]
        import requests
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")


# ── Backend: Fashn.ai ────────────────────────────────────────────────

class FashnVTONClient:
    """Virtual Try-On via Fashn.ai. Requires FASHN_API_KEY env var."""

    ENDPOINT = "https://api.fashn.ai/v1/run"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("FASHN_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "FASHN_API_KEY is required. Get one at https://www.fashn.ai/"
            )

    def generate(self, person: Image.Image, garment: Image.Image) -> Image.Image:
        person_b64 = _encode_base64(person)
        garment_b64 = _encode_base64(garment)
        logger.info("Calling Fashn.ai ...")
        import requests

        resp = requests.post(
            self.ENDPOINT,
            headers={"api-key": self.api_key},
            json={
                "model_image": f"data:image/png;base64,{person_b64}",
                "garment_image": f"data:image/png;base64,{garment_b64}",
                "category": "upper_body",
                "mode": "quality",
            },
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Fashn.ai returned {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()

        # Poll if status_url returned
        status_url = data.get("status_url")
        if not status_url:
            if "output" in data:
                out_url = data["output"]
                if isinstance(out_url, list):
                    out_url = out_url[0]
                return self._fetch_image(out_url)
            raise RuntimeError(f"Fashn.ai unexpected response: {data}")

        import time
        for _ in range(120):
            poll = requests.get(status_url, timeout=30)
            poll_data = poll.json()
            status = poll_data.get("status", "")
            if status == "completed":
                out_url = poll_data.get("output")
                if isinstance(out_url, list):
                    out_url = out_url[0]
                return self._fetch_image(out_url)
            if status in ("failed", "error"):
                raise RuntimeError(
                    f"Fashn.ai generation failed: {poll_data.get('error', 'unknown')}"
                )
            time.sleep(2)
        raise RuntimeError("Fashn.ai timed out after 2 minutes")

    @staticmethod
    def _fetch_image(url: str) -> Image.Image:
        import requests
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content)).convert("RGB")


# ── Backend: Gradio HF Spaces (free, no key needed) ──────────────────

class GradioVTONClient:
    """Free virtual try-on via Hugging Face Spaces (gradio_client).

    Uses IDM-VTON (yisol/IDM-VTON) — excellent quality, supports
    auto-masking. Free but may have queue delays.

    NOTE: gradio_client.Client spawns a background heartbeat thread that
    polls /heartbeat/{session_id} on the Space every ~300ms. If the
    Space doesn't expose that endpoint (404), it spams logs and drains
    bandwidth. We initialise the client lazily (on first generate())
    and dispose of it after use to limit the blast radius.
    """

    SPACE = "yisol/IDM-VTON"

    def __init__(self, hf_token: str | None = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self._client = None
        self._handle_file = None
        self._lock = __import__("threading").Lock()
        logger.info(
            "Gradio VTON client registered (Space %s) — will connect on first use",
            self.SPACE,
        )

    def _ensure_client(self):
        if self._client is not None:
            return
        with self._lock:
            if self._client is not None:
                return
            from gradio_client import Client, handle_file
            logger.info("Connecting to HF Space %s (lazy init) ...", self.SPACE)
            self._client = Client(self.SPACE, token=self.hf_token)
            self._handle_file = handle_file

    def _dispose_client(self):
        """Close the gradio client to stop the heartbeat thread."""
        client = self._client
        if client is None:
            return
        self._client = None
        self._handle_file = None
        try:
            # gradio_client >= 1.0 exposes close(); older versions don't.
            if hasattr(client, "close"):
                client.close()
        except Exception:
            pass

    def generate(
        self, person: Image.Image, garment: Image.Image
    ) -> Image.Image:
        person_path = f"/tmp/hf_vton_person_{os.getpid()}.png"
        garment_path = f"/tmp/hf_vton_garment_{os.getpid()}.png"
        person.save(person_path, format="PNG")
        garment.save(garment_path, format="PNG")
        try:
            self._ensure_client()
            logger.info("Calling IDM-VTON on HF Spaces ...")
            result = self._client.predict(
                dict={
                    "background": self._handle_file(person_path),
                    "layers": [],
                    "composite": None,
                },
                garm_img=self._handle_file(garment_path),
                garment_des="",
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon",
            )
            output = result[0] if isinstance(result, (list, tuple)) else result
            if isinstance(output, str) and os.path.exists(output):
                return Image.open(output).convert("RGB")
            raise RuntimeError(f"Gradio VTON unexpected result: {output}")
        finally:
            for p in (person_path, garment_path):
                try:
                    os.remove(p)
                except OSError:
                    pass
            # Dispose the client so the heartbeat thread stops after each call.
            # Next generate() will reconnect — small latency cost, big log savings.
            self._dispose_client()


# ── Backend: Segmind (existing, kept as option) ──────────────────────

class SegmindVTONClient:
    """Segmind Try-On Diffusion API. Needs credit top-up at cloud.segmind.com."""

    ENDPOINT = "https://api.segmind.com/v1/try-on-diffusion"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SEGMIND_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "SEGMIND_API_KEY is required. Set it in opentryon/.env"
            )

    def generate(self, person: Image.Image, garment: Image.Image) -> Image.Image:
        payload = {
            "model_image": _encode_base64(person),
            "cloth_image": _encode_base64(garment),
            "category": "Upper body",
            "base64": True,
        }
        logger.info("Calling Segmind Try-On Diffusion ...")
        import requests
        resp = requests.post(
            self.ENDPOINT,
            headers={"x-api-key": self.api_key},
            json=payload,
            timeout=300,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Segmind returned {resp.status_code}: {resp.text[:500]}"
            )
        data = resp.json()
        images = data.get("image", [])
        if isinstance(images, str):
            images = [images]
        if not images:
            raise RuntimeError("Segmind returned no images.")
        first = images[0]
        if isinstance(first, str):
            if first.startswith("data:"):
                first = first.split(",", 1)[1]
            return Image.open(io.BytesIO(base64.b64decode(first))).convert("RGB")
        raise RuntimeError(f"Unexpected Segmind result type: {type(first)}")


# ── TryOnService ─────────────────────────────────────────────────────

class TryOnService:
    """Virtual Try-On service with automatic backend selection.

    Backend priority (first configured wins):
      1. Replicate (IDM-VTON, best quality, $5 free credits)
      2. Fashn.ai (25 free credits/month)
      3. Gradio HF Spaces (free, IDM-VTON via HF)
      4. Segmind (needs top-up)

    Only one backend is active at a time.
    """

    def __init__(self) -> None:
        self._client = None
        self._backend_name = None

        # Production deployments can opt out of the free Gradio backend
        # by setting ENABLE_GRADIO_TRYON=0. The HF Space the default URL
        # points to (yisol/IDM-VTON) doesn't expose a /heartbeat endpoint,
        # so the gradio_client library floods logs with 404s. Disabling
        # it is the cleanest fix until a paid backend is configured.
        gradio_enabled = os.getenv("ENABLE_GRADIO_TRYON", "1").strip().lower() in (
            "1", "true", "yes", "on"
        )

        configs: list[tuple[str, str, type | None]] = [
            ("Replicate (IDM-VTON)",  "REPLICATE_API_TOKEN", ReplicateVTONClient),
            ("Fashn.ai",              "FASHN_API_KEY",       FashnVTONClient),
            ("Gradio HF Spaces",      "",                    GradioVTONClient if gradio_enabled else None),
            ("Segmind",               "SEGMIND_API_KEY",     SegmindVTONClient),
        ]

        for name, env_var, klass in configs:
            if klass is None:
                logger.info("⏭ Skipping %s (disabled via env var)", name)
                continue
            if env_var and not os.getenv(env_var):
                continue
            try:
                self._client = klass()
                self._backend_name = name
                logger.info("✅ Try-On backend active: %s", name)
                return
            except Exception as e:
                logger.debug("Backend %s not available: %s", name, e)

        logger.warning("❌ No VTON backend could be initialised.")

    @property
    def available(self) -> bool:
        return self._client is not None

    def process_tryon(
        self,
        person_image_bytes: bytes,
        garment_image_bytes: bytes,
    ) -> bytes:
        if self._client is None:
            raise RuntimeError(
                "Try-On service is unavailable. "
                "Set REPLICATE_API_TOKEN, FASHN_API_KEY, or SEGMIND_API_KEY, "
                "or the free Gradio HF Spaces backend is also available."
            )

        person_img = Image.open(io.BytesIO(person_image_bytes)).convert("RGB")
        garment_img = Image.open(io.BytesIO(garment_image_bytes)).convert("RGB")

        person_img = _resize(person_img, max_size=1024)
        garment_img = _resize(garment_img, max_size=768)

        logger.info("Processing Try-On via %s ...", self._backend_name)
        result_img = self._client.generate(person_img, garment_img)

        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        logger.info("Try-On completed via %s.", self._backend_name)
        return buf.getvalue()


# Singleton
tryon_service = TryOnService()
