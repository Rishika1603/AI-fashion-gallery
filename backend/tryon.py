import os
import io
import tempfile
import logging
import traceback
from PIL import Image
from pathlib import Path

try:
    from gradio_client import Client, handle_file
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TryOnService:
    def __init__(self):
        self.client = None
        self.current_space = None
        self.is_mock = not GRADIO_AVAILABLE
        
        # List of free virtual try-on spaces (in priority order)
        self.spaces = [
            "Kwai-Kolors/Kolors-Virtual-Try-On",  # Best quality, recommended
            "levihsu/OOTDiffusion",  # Good for full-body
        ]
        
        if not self.is_mock:
            self._connect_to_any_space()
        else:
            logger.warning("gradio_client not installed. Running in MOCK mode.")
    
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
                    api_name="/tryon" if "Kolors" in self.current_space else "/process"
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
    
    def _mock_tryon(self, person_img, garment_img):
        """Fallback mock implementation"""
        import time
        time.sleep(2)  # Simulate processing
        
        # Prepare with aspect ratio preservation
        person_img = self._prepare_image(person_img, max_size=1024)
        garment_img = self._prepare_image(garment_img, max_size=768)
        
        # Simple overlay
        result_img = person_img.copy()
        garment_small = garment_img.resize((300, 400))
        
        # Center the garment overlay
        x_offset = (result_img.width - garment_small.width) // 2
        y_offset = result_img.height // 3
        result_img.paste(garment_small, (x_offset, y_offset))
        
        # Convert to bytes
        output_buffer = io.BytesIO()
        result_img.save(output_buffer, format="PNG")
        return output_buffer.getvalue()

# Initialize the service
tryon_service = TryOnService()
