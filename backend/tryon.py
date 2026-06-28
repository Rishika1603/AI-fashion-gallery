import os
import io
import tempfile
import logging
import traceback
from pathlib import Path
from PIL import Image, ImageFilter
from dotenv import load_dotenv

try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

try:
    from opentryon.tryon.api.segmind import SegmindVTONAdapter
    SEGMIND_AVAILABLE = True
except Exception:
    SEGMIND_AVAILABLE = False

# Load env from opentryon as fallback for Segmind key
load_dotenv(Path(__file__).resolve().parent.parent / "opentryon" / ".env")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_segmind_adapter():
    if not SEGMIND_AVAILABLE:
        return None
    api_key = os.getenv("SEGMIND_API_KEY")
    if not api_key:
        return None
    try:
        return SegmindVTONAdapter(api_key=api_key)
    except Exception:
        return None


class TryOnService:
    def __init__(self):
        self.client = None
        self.current_space = None
        self.is_mock = not GRADIO_AVAILABLE
        self.segmind = _load_segmind_adapter()

        # List of free virtual try-on spaces (in priority order)
        self.spaces = [
            "Kwai-Kolors/Kolors-Virtual-Try-On",  # Best quality, recommended
            "levihsu/OOTDiffusion",  # Good for full-body
        ]

        if self.segmind is None:
            if not self.is_mock:
                self._connect_to_any_space()
            else:
                logger.warning("gradio_client not installed. No Segmind key. Running in MOCK mode.")
        else:
            logger.info("Segmind try-on adapter configured.")

    def _connect_to_any_space(self):
        """Try connecting to any available space"""
        for space_id in self.spaces:
            try:
                logger.info(f"Attempting to connect to {space_id}...")
                client = Client(space_id)
                # Test connection
                logger.info(f"Successfully connected to {space_id}!")
                self.client = client
                self.current_space = space_id
                return
            except Exception as e:
                logger.warning(f"Failed to connect to {space_id}: {e}")
                continue

        # If all spaces fail
        logger.error("Failed to connect to any virtual try-on space")
        logger.warning("Falling back to MOCK mode")
        self.is_mock = True
        self.client = None

    def _prepare_image(self, img, max_size=1024):
        """
        Prepare image with proper aspect ratio preservation
        """
        # Get original dimensions
        width, height = img.size

        # Calculate scaling to fit within max_size while preserving aspect ratio
        if width > height:
            if width > max_size:
                new_width = max_size
                new_height = int((max_size / width) * height)
            else:
                new_width, new_height = width, height
        else:
            if height > max_size:
                new_height = max_size
                new_width = int((max_size / height) * width)
            else:
                new_width, new_height = width, height

        # Resize with high-quality resampling
        if (new_width, new_height) != (width, height):
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return img

    def process_tryon(self, person_image_bytes, garment_image_bytes):
        """
        Process the virtual try-on request.
        Returns bytes of the result image.
        """
        logger.info("Processing Try-On request...")

        # Load images
        person_img = Image.open(io.BytesIO(person_image_bytes)).convert("RGB")
        garment_img = Image.open(io.BytesIO(garment_image_bytes)).convert("RGB")

        if self.segmind is not None:
            try:
                return self._segmind_tryon(person_img, garment_img)
            except Exception as e:
                logger.error(f"Segmind try-on failed: {e}")
                if not self.is_mock or self.client is None:
                    raise

        if self.is_mock or self.client is None:
            logger.info("Running in MOCK mode - returning simple overlay")
            return self._mock_tryon(person_img, garment_img)

        try:
            # Prepare images with proper aspect ratio
            person_img = self._prepare_image(person_img, max_size=1024)
            garment_img = self._prepare_image(garment_img, max_size=768)

            # Save images to temporary files (required by Gradio Client)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as person_file:
                person_img.save(person_file, format='PNG', quality=95)
                person_path = person_file.name

            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as garment_file:
                garment_img.save(garment_file, format='PNG', quality=95)
                garment_path = garment_file.name

            try:
                logger.info(f"Sending request to {self.current_space}...")

                # Call the Gradio API
                # Kolors/IDM-VTON usually use (person_image, garment_image)
                result = self.client.predict(
                    handle_file(person_path),  # Person image
                    handle_file(garment_path),  # Garment image
                    api_name="/tryon" if "Kolors" in self.current_space else "/process",
                )

                logger.info(f"Received result from IDM-VTON: type={type(result)}, value={result}")

                # Result is typically a tuple: (result_image_path, masked_image_path)
                # Handle different return formats
                try:
                    if isinstance(result, tuple) and len(result) > 0:
                        result_image_path = result[0]
                        logger.info(f"Extracted from tuple: {result_image_path}")
                    elif isinstance(result, str):
                        result_image_path = result
                        logger.info(f"Direct string result: {result_image_path}")
                    elif isinstance(result, dict):
                        # Sometimes Gradio returns a dict with file info
                        if 'path' in result:
                            result_image_path = result['path']
                        elif 'name' in result:
                            result_image_path = result['name']
                        else:
                            logger.error(f"Dict result without path/name: {result}")
                            raise Exception(f"Unexpected dict format: {result}")
                        logger.info(f"Extracted from dict: {result_image_path}")
                    else:
                        logger.error(f"Unexpected result format: type={type(result)}, value={result}")
                        raise Exception(f"Unexpected API response format: {type(result)}")

                    # Read the result image
                    logger.info(f"Attempting to read file: {result_image_path}")
                    with open(result_image_path, 'rb') as f:
                        result_bytes = f.read()
                except AttributeError as ae:
                    logger.error(f"AttributeError details: {ae}, result type: {type(result)}, result: {result}")
                    raise

                # Clean up temp files
                try:
                    os.unlink(person_path)
                    os.unlink(garment_path)
                except:
                    pass

                logger.info("Successfully processed try-on!")
                return result_bytes

            except Exception as e:
                # Clean up temp files on error
                try:
                    if os.path.exists(person_path):
                        os.unlink(person_path)
                    if os.path.exists(garment_path):
                        os.unlink(garment_path)
                except:
                    pass
                raise e

        except Exception as e:
            logger.error(f"Gradio API error: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            logger.warning("Falling back to MOCK mode for this request")
            return self._mock_tryon(person_img, garment_img)

    def _segmind_tryon(self, person_img, garment_img):
        person_img = self._prepare_image(person_img, max_size=1024)
        garment_img = self._prepare_image(garment_img, max_size=768)

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as person_file:
            person_img.save(person_file, format='PNG')
            person_path = person_file.name
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as garment_file:
            garment_img.save(garment_file, format='PNG')
            garment_path = garment_file.name

        try:
            images = self.segmind.generate_and_decode(
                model_image=person_path,
                cloth_image=garment_path,
                category="Upper body",
            )
            buf = io.BytesIO()
            images[0].save(buf, format='PNG')
            return buf.getvalue()
        finally:
            try:
                os.unlink(person_path)
                os.unlink(garment_path)
            except Exception:
                pass

    def _mock_tryon(self, person_img, garment_img):
        """Improved mock: remove garment background and blend into person image."""
        import time
        time.sleep(2)  # Simulate processing

        person = self._prepare_image(person_img, max_size=1024).convert("RGBA")
        garment = self._prepare_image(garment_img, max_size=768).convert("RGBA")

        # Remove garment background using simple color-distance heuristic
        garment_no_bg = self._remove_background(garment)

        # Determine placement region based on garment aspect ratio
        pw, ph = person.size
        gw, gh = garment_no_bg.size
        max_w = int(pw * 0.75)
        scale = min(1.0, max(1, max_w) / max(1, gw))
        new_gw = max(1, int(gw * scale))
        new_gh = max(1, int(gh * scale))
        garment_resized = garment_no_bg.resize((new_gw, new_gh), Image.Resampling.LANCZOS)

        # Default placement: center-bottom (torso)
        x = (pw - new_gw) // 2
        y = int(ph * 0.25)

        # Soft feathered paste using alpha channel
        person_rgba = person.copy()
        garment_rgba = garment_resized.copy()
        person_rgba.paste(garment_rgba, (x, y), garment_rgba)

        out = person_rgba.convert("RGB")
        output_buffer = io.BytesIO()
        out.save(output_buffer, format="PNG")
        return output_buffer.getvalue()

    def _remove_background(self, img: Image.Image) -> Image.Image:
        """Simple background removal using white/light-color thresholding."""
        img = img.convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            r, g, b, a = item
            brightness = (r + g + b) / 3
            if brightness > 230 and r > 200 and g > 200 and b > 200:
                # Likely white background -> transparent
                new_data.append((r, g, b, 0))
            else:
                new_data.append((r, g, b, a))
        img.putdata(new_data)
        return img

# Initialize the service
tryon_service = TryOnService()
