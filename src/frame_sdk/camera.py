from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from exif import Image
from datetime import datetime

if TYPE_CHECKING:
    from .frame import Frame

class Camera:
    """Helpers for working with the Frame camera."""

    frame: "Frame" = None
    
    LOW_QUALITY = 10
    MEDIUM_QUALITY = 25
    HIGH_QUALITY = 50
    FULL_QUALITY = 100
    
    AUTOFOCUS_TYPE_SPOT = "SPOT"
    AUTOFOCUS_TYPE_AVERAGE = "AVERAGE"
    AUTOFOCUS_TYPE_CENTER_WEIGHTED = "CENTER_WEIGHTED"

    _auto_process_photo = True
    
    def __init__(self, frame: "Frame"):
        """Initialize the Camera with a Frame instance."""
        self.frame = frame
        self.is_awake = True
        
    @property
    def auto_process_photo(self) -> bool:
        """If true, the camera will automatically process the photo to correct rotation and add metadata."""
        return self._auto_process_photo
    
    @auto_process_photo.setter
    def auto_process_photo(self, value: bool):
        """If true, the camera will automatically process the photo to correct rotation and add metadata."""
        self._auto_process_photo = value
    
    
    async def take_photo(self, autofocus_seconds: Optional[int] = 3, quality: int = MEDIUM_QUALITY, autofocus_type: str = AUTOFOCUS_TYPE_AVERAGE) -> bytes:
        """Take a photo with the camera.

        Args:
            autofocus_seconds (Optional[int]): If provided, the camera will attempt to focus for the specified number of seconds.  Defaults to 3.  If `None`, the camera will not attempt to focus at all.
            quality (int): The quality of the photo. Defaults to MEDIUM_QUALITY.  May be one of LOW_QUALITY (10), MEDIUM_QUALITY (25), HIGH_QUALITY (50), or FULL_QUALITY (100).
            autofocus_type (str): The type of autofocus. Defaults to AUTOFOCUS_TYPE_AVERAGE.  May be one of AUTOFOCUS_TYPE_SPOT, AUTOFOCUS_TYPE_AVERAGE, or AUTOFOCUS_TYPE_CENTER_WEIGHTED.
        
        Returns:
            bytes: The photo as a byte array.
        
        Raises:
            Exception: If the photo capture fails.
        """
        
        if not self.is_awake:
            await self.frame.run_lua("frame.camera.wake()", checked=True)
            self.is_awake = True
        
        await self.frame.bluetooth.send_lua(f"cameraCaptureAndSend({quality},{autofocus_seconds or 'nil'},{autofocus_type})")
        image_buffer = await self.frame.bluetooth.wait_for_data()
        
        if image_buffer is None or len(image_buffer) == 0:
            raise Exception("Failed to get photo")
        
        if self.auto_process_photo:
            image_buffer = self.process_photo(image_buffer, autofocus_type)
        return image_buffer
    
    async def save_photo(self, filename: str, autofocus_seconds: Optional[int] = 3, quality: int = MEDIUM_QUALITY, autofocus_type: str = AUTOFOCUS_TYPE_AVERAGE):
        """Save a photo to a file.
        
        Args:
            filename (str): The name of the file to save the photo.  The file will always be saved as a jpeg image regardless of the file extension.
            autofocus_seconds (Optional[int]): If provided, the camera will attempt to focus for the specified number of seconds.  Defaults to 3.  If `None`, the camera will not attempt to focus at all.
            quality (int): The quality of the photo. Defaults to MEDIUM_QUALITY.  May be one of LOW_QUALITY (10), MEDIUM_QUALITY (25), HIGH_QUALITY (50), or FULL_QUALITY (100).
            autofocus_type (str): The type of autofocus. Defaults to AUTOFOCUS_TYPE_AVERAGE.  May be one of AUTOFOCUS_TYPE_SPOT, AUTOFOCUS_TYPE_AVERAGE, or AUTOFOCUS_TYPE_CENTER_WEIGHTED.
        """
        image_buffer = await self.take_photo(autofocus_seconds, quality, autofocus_type)

        with open(filename, "wb") as f:
            f.write(image_buffer)
            
    def process_photo(self, image_buffer: bytes, autofocus_type: str) -> bytes:
        """Process a photo to correct rotation and add metadata.
        
        Args:
            image_buffer (bytes): The photo as a byte array.
            autofocus_type (str): The type of autofocus that was used to capture the photo.  Should be one of AUTOFOCUS_TYPE_SPOT, AUTOFOCUS_TYPE_AVERAGE, or AUTOFOCUS_TYPE_CENTER_WEIGHTED.
        
        Returns:
            bytes: The processed photo as a byte array.
        """
        image = Image(image_buffer)
        image.orientation = 8
        image.make = "Brilliant Labs"
        image.model = "Frame"
        image.software = "Frame Python SDK"
        if autofocus_type == self.AUTOFOCUS_TYPE_AVERAGE:
            image.metering_mode = 1
        elif autofocus_type == self.AUTOFOCUS_TYPE_CENTER_WEIGHTED:
            image.metering_mode = 2
        elif autofocus_type == self.AUTOFOCUS_TYPE_SPOT:
            image.metering_mode = 3
        image.datetime_original = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
        return image.get_file()