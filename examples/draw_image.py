from PIL import Image
import numpy as np
from typing import List, Tuple, Dict
import asyncio
from frame_sdk import Frame
from frame_sdk.display import PixelArtConverter
from functools import lru_cache
import time
import logging
from collections import Counter
    
from collections import defaultdict
import logging
from typing import List, Dict, Tuple
import numpy as np
from bleak.exc import BleakError
from skimage import io
from pyxelate import Pyx, Pal
import numpy as np
from collections import defaultdict
import logging
from typing import List, Tuple, Dict
import asyncio
from bleak.exc import BleakError
from PIL import Image
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
import matplotlib.pyplot as plt
import numpy as np
from typing import List
from frame_sdk.display import PaletteColors

def visualize_palette_conversion(image_path: str, target_width: int = 128, target_height: int = 128):
    """
    Visualize the palette conversion of an image using matplotlib.
    
    Args:
        image_path (str): Path to the input image
        target_width (int): Target width for conversion
        target_height (int): Target height for conversion
    """
    palette_data = PixelArtConverter.convert_image_to_palette(
        image_path, 
        target_width=target_width, 
        target_height=target_height
    )
    
    rgb_array = np.zeros((target_height, target_width, 3), dtype=np.uint8)
    
    for y in range(target_height):
        for x in range(target_width):
            color = palette_data[y][x]
            if isinstance(color, PaletteColors):
                color_value = color.value
            else:
                color_value = int(color)
            rgb_array[y, x] = PixelArtConverter.PALETTE_RGB[color_value]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    original_img = plt.imread(image_path)
    ax1.imshow(original_img)
    ax1.set_title('Original Image')
    ax1.axis('off')
    
    ax2.imshow(rgb_array)
    ax2.set_title('Palette Converted Image')
    ax2.axis('off')
    
    palette_reference = np.zeros((16, 1, 3), dtype=np.uint8)
    for i in range(16):
        palette_reference[i, 0] = PixelArtConverter.PALETTE_RGB[i]
    
    ax3 = fig.add_axes([0.92, 0.1, 0.02, 0.8])
    ax3.imshow(palette_reference)
    ax3.set_title('Palette')
    ax3.set_xticks([])
    ax3.set_yticks(range(16))
    ax3.set_yticklabels([color.name for color in PaletteColors])
    
    plt.tight_layout()
    
    unique_colors = set()
    color_counts = {}
    for row in palette_data:
        for color in row:
            if isinstance(color, PaletteColors):
                color_name = color.name
            else:
                color_name = PaletteColors(int(color)).name
            unique_colors.add(color_name)
            color_counts[color_name] = color_counts.get(color_name, 0) + 1
    
    print("\nColor Distribution:")
    total_pixels = target_width * target_height
    for color_name, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_pixels) * 100
        print(f"{color_name}: {count} pixels ({percentage:.1f}%)")
    
    return palette_data, rgb_array


async def display_image(frame: Frame, x: int, y: int, image_path: str, 
                       width: int = 64, height: int = 64, scale: int = 1):
    """
    Load, process and display an image file on the Frame device.
    
    Args:
        frame (Frame): Frame device instance
        x (int): X coordinate to start drawing
        y (int): Y coordinate to start drawing
        image_path (str): Path to the image file
        width (int): Desired width in pixels
        height (int): Desired height in pixels
        scale (int): Scale factor for the image
    """
    try:
        logging.info(f"Processing image file: {image_path}")
        logging.info(f"Displaying image at ({x}, {y}) with scale {scale}")
        
        palette_data = PixelArtConverter.convert_image_to_palette(image_path, target_width=width, target_height=height)
        await frame.display.draw_image(x=0, y=0, image_data=palette_data, scale=1)
        await frame.display.show()
        
        logging.info("Image display completed successfully")
        
    except FileNotFoundError:
        logging.error(f"Image file not found: {image_path}")
        raise
    except BleakError as e:
        logging.error(f"Bluetooth communication error: {e}")
        raise
    except Exception as e:
        logging.error(f"Error processing or displaying image: {e}")
        raise



async def main():
    logging.info("Starting main application...")
    try:
        async with Frame() as f:
            logging.info("Frame connection established")
            await display_image(
                frame=f,
                image_path="output.png",
                x=10,
                y=10,
                width=64,
                height=64,
                scale=1
            )
            logging.info("Image display completed successfully")
    except Exception as e:
        logging.error(f"Error in main execution: {e}", exc_info=True)
    finally:
        logging.info("Application shutting down")

if __name__ == "__main__":
    '''
    # install pyxelate
    pip install git+https://github.com/sedthh/pyxelate.git
    
    # create  a 2 color quantized image of cat.jpeg
    pyxelate cat.jpeg output.png --palette 2
    '''
    
    # Uncomment this to see how the image should look in frame
    # palette_data, rgb_array = visualize_palette_conversion("output.png", target_width=128, target_height=128)
    # plt.show(block=False)
    
    # display output.png in frame
    asyncio.run(main())