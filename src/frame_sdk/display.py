from __future__ import annotations
import asyncio
from typing import Optional, TYPE_CHECKING, List, Union
from enum import Enum

if TYPE_CHECKING:
    from .frame import Frame
    
from enum import Enum
import numpy as np
import logging
from PIL import Image
class PixelArtConverter:
    PALETTE_RGB = np.array([
        [0, 0, 0],        # VOID
        [255, 255, 255],  # WHITE
        [157, 157, 157],  # GRAY
        [190, 38, 51],    # RED
        [224, 111, 139],  # PINK
        [73, 60, 43],     # DARKBROWN
        [164, 100, 34],   # BROWN
        [235, 137, 49],   # ORANGE
        [247, 226, 107],  # YELLOW
        [47, 72, 78],     # DARKGREEN
        [68, 137, 26],    # GREEN
        [163, 206, 39],   # LIGHTGREEN
        [27, 38, 50],     # NIGHTBLUE
        [0, 87, 132],     # SEABLUE
        [49, 162, 242],   # SKYBLUE
        [178, 220, 239],  # CLOUDBLUE
    ])

    @staticmethod
    def _find_unique_colors(img_array: np.ndarray) -> set:
        return {tuple(color) for color in np.unique(img_array.reshape(-1, 3), axis=0)}

    @staticmethod
    def _find_closest_palette_color(color: tuple) -> int:
        """Find the closest palette color and return its index (PaletteColors value)"""
        color_array = np.array(color)
        distances = np.sqrt(np.sum((PixelArtConverter.PALETTE_RGB - color_array) ** 2, axis=1))
        return int(np.argmin(distances))

    @classmethod
    def convert_image_to_palette(cls, image_path: str, target_width: int = 64, target_height: int = 64) -> List[List[PaletteColors]]:
        """
        Convert an image to Frame's PaletteColors format by quantizing to the closest matching colors.
        The source image will be automatically quantized from its original color depth
        to Frame's fixed 16-color palette: VOID (black), WHITE, GRAY, RED, PINK, DARKBROWN,
        BROWN, ORANGE, YELLOW, DARKGREEN, GREEN, LIGHTGREEN, NIGHTBLUE, SEABLUE, 
        SKYBLUE, and CLOUDBLUE.

        This method performs the following steps:
        1. Loads and resizes the image to the target dimensions
        2. Converts the image to RGB format if needed
        3. Quantizes the image colors to match Frame's 16-color palette using nearest neighbor color matching
        4. Returns a 2D array of PaletteColors enum values

        Args:
            image_path (str): Path to the source image file
            target_width (int, optional): Desired width of the output image. Defaults to 64.
            target_height (int, optional): Desired height of the output image. Defaults to 64.

        Returns:
            List[List[PaletteColors]]: 2D array of PaletteColors enum values representing the quantized image.
            Each pixel is mapped to the closest matching color in Frame's 16-color palette.
        """
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = img.resize((target_width, target_height), Image.Resampling.NEAREST)
            img_array = np.array(img)
            
            unique_colors = cls._find_unique_colors(img_array)
            
            color_mapping = {
                color: cls._find_closest_palette_color(color)
                for color in unique_colors
            }
            
            palette_data = [[
                PaletteColors(color_mapping[tuple(pixel)])
                for pixel in row
            ] for row in img_array]
            
            return palette_data

class Alignment(Enum):
    """Enum for text alignment options."""
    TOP_LEFT = 'top_left'
    TOP_CENTER = 'top_center'
    TOP_RIGHT = 'top_right'
    MIDDLE_LEFT = 'middle_left'
    MIDDLE_CENTER = 'middle_center'
    MIDDLE_RIGHT = 'middle_right'
    BOTTOM_LEFT = 'bottom_left'
    BOTTOM_CENTER = 'bottom_center'
    BOTTOM_RIGHT = 'bottom_right'

char_width_mapping = {
    0x000020: 13,
    0x000021: 5,
    0x000022: 13,
    0x000023: 19,
    0x000024: 17,
    0x000025: 34,
    0x000026: 20,
    0x000027: 5,
    0x000028: 10,
    0x000029: 11,
    0x00002A: 21,
    0x00002B: 19,
    0x00002C: 8,
    0x00002D: 17,
    0x00002E: 6,
    0x000030: 18,
    0x000031: 16,
    0x000032: 16,
    0x000033: 15,
    0x000034: 18,
    0x000035: 15,
    0x000036: 17,
    0x000037: 15,
    0x000038: 18,
    0x000039: 17,
    0x00003A: 6,
    0x00003B: 8,
    0x00003C: 19,
    0x00003D: 19,
    0x00003E: 19,
    0x00003F: 14,
    0x000040: 31,
    0x000041: 22,
    0x000042: 18,
    0x000043: 16,
    0x000044: 19,
    0x000045: 17,
    0x000046: 17,
    0x000047: 18,
    0x000048: 19,
    0x000049: 12,
    0x00004A: 14,
    0x00004B: 19,
    0x00004C: 16,
    0x00004D: 23,
    0x00004E: 19,
    0x00004F: 20,
    0x000050: 18,
    0x000051: 22,
    0x000052: 20,
    0x000053: 17,
    0x000054: 20,
    0x000055: 19,
    0x000056: 21,
    0x000057: 23,
    0x000058: 21,
    0x000059: 23,
    0x00005A: 17,
    0x00005B: 9,
    0x00005C: 15,
    0x00005D: 10,
    0x00005E: 20,
    0x00005F: 25,
    0x000060: 11,
    0x000061: 19,
    0x000062: 18,
    0x000063: 13,
    0x000064: 18,
    0x000065: 16,
    0x000066: 15,
    0x000067: 20,
    0x000068: 18,
    0x000069: 5,
    0x00006A: 11,
    0x00006B: 18,
    0x00006C: 8,
    0x00006D: 28,
    0x00006E: 18,
    0x00006F: 18,
    0x000070: 18,
    0x000071: 18,
    0x000072: 11,
    0x000073: 15,
    0x000074: 14,
    0x000075: 17,
    0x000076: 19,
    0x000077: 30,
    0x000078: 20,
    0x000079: 20,
    0x00007A: 16,
    0x00007B: 12,
    0x00007C: 5,
    0x00007D: 12,
    0x00007E: 17,
    0x0000A1: 6,
    0x0000A2: 14,
    0x0000A3: 18,
    0x0000A5: 22,
    0x0000A9: 28,
    0x0000AB: 17,
    0x0000AE: 29,
    0x0000B0: 15,
    0x0000B1: 20,
    0x0000B5: 17,
    0x0000B7: 6,
    0x0000BB: 17,
    0x0000BF: 14,
    0x0000C0: 22,
    0x0000C1: 23,
    0x0000C2: 23,
    0x0000C3: 23,
    0x0000C4: 23,
    0x0000C5: 23,
    0x0000C6: 32,
    0x0000C7: 16,
    0x0000C8: 17,
    0x0000C9: 16,
    0x0000CA: 17,
    0x0000CB: 17,
    0x0000CC: 12,
    0x0000CD: 11,
    0x0000CE: 16,
    0x0000CF: 15,
    0x0000D0: 22,
    0x0000D1: 19,
    0x0000D2: 20,
    0x0000D3: 20,
    0x0000D4: 20,
    0x0000D5: 20,
    0x0000D6: 20,
    0x0000D7: 18,
    0x0000D8: 20,
    0x0000D9: 19,
    0x0000DA: 19,
    0x0000DB: 19,
    0x0000DC: 19,
    0x0000DD: 22,
    0x0000DE: 18,
    0x0000DF: 19,
    0x0000E0: 19,
    0x0000E1: 19,
    0x0000E2: 19,
    0x0000E3: 19,
    0x0000E4: 19,
    0x0000E5: 19,
    0x0000E6: 29,
    0x0000E7: 14,
    0x0000E8: 17,
    0x0000E9: 16,
    0x0000EA: 17,
    0x0000EB: 17,
    0x0000EC: 11,
    0x0000ED: 11,
    0x0000EE: 16,
    0x0000EF: 15,
    0x0000F0: 18,
    0x0000F1: 16,
    0x0000F2: 18,
    0x0000F3: 18,
    0x0000F4: 18,
    0x0000F5: 17,
    0x0000F6: 18,
    0x0000F7: 19,
    0x0000F8: 18,
    0x0000F9: 17,
    0x0000FA: 17,
    0x0000FB: 16,
    0x0000FC: 17,
    0x0000FD: 20,
    0x0000FE: 18,
    0x0000FF: 20,
    0x000131: 5,
    0x000141: 19,
    0x000142: 10,
    0x000152: 30,
    0x000153: 30,
    0x000160: 17,
    0x000161: 15,
    0x000178: 22,
    0x00017D: 18,
    0x00017E: 17,
    0x000192: 16,
    0x0020AC: 18,
    0x0F0000: 70,
    0x0F0001: 70,
    0x0F0002: 70,
    0x0F0003: 70,
    0x0F0004: 91,
    0x0F0005: 70,
    0x0F0006: 70,
    0x0F0007: 70,
    0x0F0008: 70,
    0x0F0009: 70,
    0x0F000A: 70,
    0x0F000B: 70,
    0x0F000C: 70,
    0x0F000D: 70,
    0x0F000E: 77,
    0x0F000F: 76,
    0x0F0010: 70
}

from enum import Enum

class PaletteColors(Enum):
    VOID = 0
    WHITE = 1
    GRAY = 2
    RED = 3
    PINK = 4
    DARKBROWN = 5
    BROWN = 6
    ORANGE = 7
    YELLOW = 8
    DARKGREEN = 9
    GREEN = 10
    LIGHTGREEN = 11
    NIGHTBLUE = 12
    SEABLUE = 13
    SKYBLUE = 14
    CLOUDBLUE = 15


class Display:
    """Displays text and graphics on the Frame display."""

    frame: "Frame" = None

    color_palette_mapping = {
        PaletteColors.VOID: (0, 0, 0),
        PaletteColors.WHITE: (255, 255, 255),
        PaletteColors.GRAY: (157, 157, 157),
        PaletteColors.RED: (190, 38, 51),
        PaletteColors.PINK: (224, 111, 139),
        PaletteColors.DARKBROWN: (73, 60, 43),
        PaletteColors.BROWN: (164, 100, 34),
        PaletteColors.ORANGE: (235, 137, 49),
        PaletteColors.YELLOW: (247, 226, 107),
        PaletteColors.DARKGREEN: (47, 72, 78),
        PaletteColors.GREEN: (68, 137, 26),
        PaletteColors.LIGHTGREEN: (163, 206, 39),
        PaletteColors.NIGHTBLUE: (27, 38, 50),
        PaletteColors.SEABLUE: (0, 87, 132),
        PaletteColors.SKYBLUE: (49, 162, 242),
        PaletteColors.CLOUDBLUE: (178, 220, 239),
    }

    _line_height = 60
    _char_spacing = 4

    @property
    def line_height(self) -> int:
        """Gets the height of each line of text in pixels. It is 60 by default, however you may override that value to change the vertical spacing of the text in all text displaying functions."""
        return self._line_height

    @line_height.setter
    def line_height(self, value: int):
        """Sets the height of each line of text in pixels. It is 60 by default, however you may override that value to change the vertical spacing of the text in all text displaying functions."""
        if value < 0:
            raise ValueError("line_height must be a non-negative integer")
        self._line_height = value

    @property
    def char_spacing(self) -> int:
        """Gets the spacing between characters in pixels. It is 4 by default."""
        return self._char_spacing

    @char_spacing.setter
    def char_spacing(self, value: int):
        """Sets the spacing between characters in pixels."""
        if value < 0:
            raise ValueError("char_spacing must be a non-negative integer")
        self._char_spacing = value

    def __init__(self, frame: "Frame"):
        """
        Initialize the Display class.

        Args:
            frame (Frame): The Frame object to associate with this display.
        """
        self.frame = frame
        
    @staticmethod
    def parse_alignment(align: Alignment) -> tuple[str, str]:
        """
        Parse the alignment enum to horizontal and vertical alignment strings.

        Args:
            align (Alignment): The alignment enum value.

        Returns:
            tuple[str, str]: A tuple containing horizontal and vertical alignment strings.
        """
        alignments = {
            Alignment.TOP_LEFT: ("left", "top"),
            Alignment.TOP_CENTER: ("center", "top"),
            Alignment.TOP_RIGHT: ("right", "top"),
            Alignment.MIDDLE_LEFT: ("left", "middle"),
            Alignment.MIDDLE_CENTER: ("center", "middle"),
            Alignment.MIDDLE_RIGHT: ("right", "middle"),
            Alignment.BOTTOM_LEFT: ("left", "bottom"),
            Alignment.BOTTOM_CENTER: ("center", "bottom"),
            Alignment.BOTTOM_RIGHT: ("right", "bottom"),
        }
        return alignments.get(align, ("left", "top"))

    async def show_text(self, text: str, x: int = 1, y: int = 1, max_width: Optional[int] = 640, max_height: Optional[int] = None, align: Alignment = Alignment.TOP_LEFT, color: PaletteColors = PaletteColors.WHITE):
        """
        Show text on the display.

        Args:
            text (str): The text to display.
            x (int): The left pixel position to start the text.  Defaults to 1.
            y (int): The top pixel position to start the text.  Defaults to 1.
            max_width (Optional[int]): The maximum width for the text bounding box. If text is wider than this, it will be word-wrapped onto multiple lines automatically. Set to the full width of the display by default (640px), but can be overridden with None/null to disable word-wrapping.
            max_height (Optional[int]): The maximum height for the text bounding box. If text is taller than this, it will be cut off at that height. Also useful for vertical alignment. Set to the full height of the display by default (400px).
            align (Alignment): The alignment of the text, both horizontally if a max_width is provided, and vertically if a max_height is provided. Can be any value in frame.display.Alignment, such as Alignment.TOP_LEFT, Alignment.MIDDLE_CENTER, etc.
        """
        await self.write_text(text, x, y, max_width, max_height, align, color)
        await self.show()

    async def write_text(self, text: str, x: int = 1, y: int = 1, max_width: Optional[int] = 640, max_height: Optional[int] = None, align: Alignment = Alignment.TOP_LEFT, color: PaletteColors = PaletteColors.WHITE):
        """
        Write text to the display buffer.

        Args:
            text (str): The text to write.
            x (int): The left pixel position to start the text.  Defaults to 1.
            y (int): The top pixel position to start the text.  Defaults to 1.
            max_width (Optional[int]): The maximum width for the text bounding box. If text is wider than this, it will be word-wrapped onto multiple lines automatically. Set to the full width of the display by default (640px), but can be overridden with None/null to disable word-wrapping.
            max_height (Optional[int]): The maximum height for the text bounding box. If text is taller than this, it will be cut off at that height. Also useful for vertical alignment. Set to the full height of the display by default (400px).
            align (Alignment): The alignment of the text, both horizontally if a max_width is provided, and vertically if a max_height is provided. Can be any value in frame.display.Alignment, such as Alignment.TOP_LEFT, Alignment.MIDDLE_CENTER, etc.
            color (Palette_Colors): The color of the text. Defaults to Palette_Colors.WHITE.
        """
        if max_width is not None:
            text = self.wrap_text(text, max_width)

        horizontal_align, vertical_align = self.parse_alignment(align)

        total_height_of_text = self.get_text_height(text)
        vertical_offset = 0
        if vertical_align == "middle":
            vertical_offset = (max_height if max_height is not None else (400-y)) // 2 - total_height_of_text // 2
        elif vertical_align == "bottom":
            vertical_offset = (max_height if max_height is not None else (400-y)) - total_height_of_text

        for line in text.split("\n"):
            this_line_x = x
            if horizontal_align == "center":
                this_line_x = x + (max_width if max_width is not None else (640-x)) // 2 - self.get_text_width(line) // 2
            elif horizontal_align == "right":
                this_line_x = x + (max_width if max_width is not None else (640-x)) - self.get_text_width(line)
            lua_to_send = f"frame.display.text(\"{self.frame.escape_lua_string(line)}\",{this_line_x},{y+vertical_offset}"
            if self.char_spacing != 4 or color != PaletteColors.WHITE:
                lua_to_send += ',{'
                if self.char_spacing != 4:
                    lua_to_send += f'spacing={self.char_spacing}'
                if self.char_spacing != 4 and color != PaletteColors.WHITE:
                    lua_to_send += ','
                if color != PaletteColors.WHITE:
                    lua_to_send += f'color="{color.name}"'
                lua_to_send += '}'
            lua_to_send += ')'
            await self.frame.run_lua(lua_to_send, checked=True)
            y += self.line_height
            if max_height is not None and y > max_height or y+vertical_offset > 640:
                break
            
    async def scroll_text(self, text: str, lines_per_frame: int = 5, delay: float = 0.12, color: PaletteColors = PaletteColors.WHITE):
        """
        Scroll text vertically on the display.

        Args:
            text (str): The text to scroll. It is automatically wrapped to fit the display width.
            lines_per_frame (int): The number of vertical pixels to scroll per frame. Defaults to 5. Higher values scroll faster, but will be more jumpy.
            delay (float): The delay between frames in seconds. Defaults to 0.12 seconds. Lower values are faster, but may cause graphical glitches.
        """
        margin = self.line_height
        text = self.wrap_text(text, 640)
        total_height = self.get_text_height(text)
        if total_height < 400:
            await self.write_text(text)
            return
        await self.frame.run_lua(f"scrollText(\"{self.frame.escape_lua_string(text)}\",{self.line_height},{total_height},{lines_per_frame},{delay},'{color.name}',{self.char_spacing})",checked=True,timeout=total_height/lines_per_frame*(delay+0.1)+5)

    def wrap_text(self, text: str, max_width: int) -> str:
        """
        Wrap text to fit within a specified width.

        Args:
            text (str): The text to wrap.
            max_width (int): The maximum width for the text bounding box.

        Returns:
            str: The wrapped text.
        """
        lines = text.split("\n")
        output = ""
        for line in lines:
            if self.get_text_width(line) <= max_width:
                output += line+"\n"
            else:
                this_line = ""
                words = line.split(" ")
                for word in words:
                    if self.get_text_width(this_line+" "+word) > max_width:
                        output += this_line+"\n"
                        this_line = word
                    elif len(this_line) == 0:
                        this_line = word
                    else:
                        this_line += " "+word
                if len(this_line) > 0:
                    output += this_line+"\n"
        return output.rstrip("\n")

    def get_text_height(self, text: str) -> int:
        """
        Gets the rendered height of text in pixels.
        This does not perform any text wrapping but does respect any manually-included line breaks.
        The rendered height is affected by the `line_height` property.

        Args:
            text (str): The text to measure.

        Returns:
            int: The height of the text in pixels.
        """
        num_lines = text.count("\n") + 1
        return num_lines * (self.line_height)

    def get_text_width(self, text: str) -> int:
        """
        Gets the rendered width of text in pixels.
        Text on Frame is variable width, so this is important for positioning text.
        This does not perform any text wrapping but does respect any manually-included line breaks.

        Args:
            text (str): The text to measure.

        Returns:
            int: The width of the text in pixels.
        """
        width = 0
        for char in text:
            width += char_width_mapping.get(ord(char), 25) + self.char_spacing
        return width

    async def show(self):
        """Swaps the buffer to show the changes.
        The Frame display has 2 buffers. All writing to the display via frame.display.write_text(), frame.display.draw_rect(), etc write to an off-screen buffer and are not visible. This allows you to write multiple actions at once. When you have completed drawing and want to show it to the user, call frame.display.show() which will display the buffered graphics and clear a new off-screen buffer for whatever you want to draw next."""
        await self.frame.run_lua("frame.display.show()", checked=True)

    async def clear(self):
        """Clears the display."""
        await self.frame.run_lua("frame.display.bitmap(1,1,4,2,15,\"\\xFF\")")
        await self.show()

    async def set_palette(self, paletteIndex: PaletteColors, rgb_color: tuple[int, int, int]):
        """
        Sets a color in the display palette.

        Args:
            paletteIndex (PaletteColors): The PaletteColor to set.
            rgb_color (tuple[int, int, int]): The RGB color tuple.

        Raises:
            ValueError: If the index is out of range.
        """
        if isinstance(paletteIndex, int):
            paletteIndex = PaletteColors(paletteIndex % 16)

        color = tuple(max(0, min(255, c)) for c in rgb_color)
        self.palette[paletteIndex] = color
        await self.frame.run_lua(f"frame.display.assign_color({paletteIndex.name},{color[0]},{color[1]},{color[2]})", checked=True)

    def _draw_rect_lua(self, x: int, y: int, w: int, h: int, color: PaletteColors):
        if isinstance(color, PaletteColors):
            color = color.value

        w = w // 8 * 8
        return f"frame.display.bitmap({x},{y},{w},2,{color},string.rep(\"\\xFF\",{(w//8)*h}))"

    async def draw_rect(self, x: int, y: int, w: int, h: int, color: PaletteColors = PaletteColors.WHITE):
        """
        Draws a filled rectangle on the display.

        Args:
            x (int): The x position of the upper-left corner of the rectangle.
            y (int): The y position of the upper-left corner of the rectangle.
            w (int): The width of the rectangle.
            h (int): The height of the rectangle.
            color (PaletteColors): The color of the rectangle.
        """
        if isinstance(color, PaletteColors):
            color = color.value

        w = w // 8 * 8
        await self.frame.run_lua(self._draw_rect_lua(x, y, w, h, color))
        
    async def draw_rect_filled(self, x: int, y: int, w: int, h: int, border_width: int, border_color: PaletteColors, fill_color: PaletteColors):
        """
        Draws a filled rectangle with a border on the display.

        Args:
            x (int): The x position of the upper-left corner of the rectangle.
            y (int): The y position of the upper-left corner of the rectangle.
            w (int): The width of the rectangle.
            h (int): The height of the rectangle.
            border_width (int): The width of the border in pixels.
            border_color (PaletteColors): The color of the border.
            fill_color (PaletteColors): The color of the fill.
        """

        w = w // 8 * 8
        if border_width > 0:
            border_width = border_width // 8 * 8
            if border_width == 0:
                border_width = 8
        else:
            await self.draw_rect(x, y, w, h, fill_color)
            return

        # draw entire rectangle as border color
        lua_to_send = self._draw_rect_lua(x, y, w, h, border_color)
        # draw the inside rectangle
        lua_to_send += self._draw_rect_lua(x+border_width, y+border_width, w-border_width*2, h-border_width*2, fill_color)
        await self.frame.run_lua(lua_to_send, checked=True)
    
    async def draw_image(self, *, x: int, y: int, image_data: List[List[PaletteColors]], 
                    scale: int = 1) -> List[List[PaletteColors]]:
        """
        Draws a quantized image on the Frame display using bitmap operations.
        It supports different color modes (2-color, 4-color, and 16-color) and uses a single
        color mode for the entire image based on the maximum color value present.

        Args:
            x (int): The x coordinate where the image will be drawn (1-based indexing).
            y (int): The y coordinate where the image will be drawn (1-based indexing).
            image_data (List[List[PaletteColors]]): 2D array of quantized PaletteColors representing the image pixels.
            scale (int, optional): Scaling factor for the image. Defaults to 1.

        Returns:
            List[List[PaletteColors]]: The processed image data that was drawn.
        """
        if not image_data or not image_data[0]:
            logging.warning("Empty image data received")
            return []

        height = len(image_data)
        width = len(image_data[0])
        logging.debug(f"Processing image: {width}x{height} at scale {scale}")

        # Ensure coordinates are within valid range
        lua_x = max(1, min(640 - width * scale, x + 1))
        lua_y = max(1, min(400 - height * scale, y + 1))

        try:
            await self.clear()
            await asyncio.sleep(0.1)  # Small delay after clear

            # Determine color mode for entire image
            max_color = max(
                max(color.value if isinstance(color, PaletteColors) else int(color)
                    for color in row)
                for row in image_data
            )

            if max_color <= 1:
                color_mode = 2
                pixels_per_byte = 8
                bit_mask = 0x01
                bits_per_pixel = 1
            elif max_color <= 3:
                color_mode = 4
                pixels_per_byte = 4
                bit_mask = 0x03
                bits_per_pixel = 2
            else:
                color_mode = 16
                pixels_per_byte = 2
                bit_mask = 0x0F
                bits_per_pixel = 4

            bytes_needed = (width + pixels_per_byte - 1) // pixels_per_byte
            commands = []

            # Process each row
            for row_idx, row in enumerate(image_data):
                row_values = [color.value if isinstance(color, PaletteColors) else int(color) for color in row]

                # Group pixels by color
                color_groups = {}
                for i, color in enumerate(row_values):
                    if color not in color_groups:
                        color_groups[color] = []
                    color_groups[color].append(i)

                # Generate commands for each color in this row
                for color, positions in color_groups.items():
                    pattern = bytearray(bytes_needed)
                    
                    # Set bits for this color's pixels
                    for pos in positions:
                        byte_idx = pos // pixels_per_byte
                        bit_pos = (pixels_per_byte - 1 - (pos % pixels_per_byte)) * bits_per_pixel
                        pattern[byte_idx] |= bit_mask << bit_pos

                    if not any(pattern):  # Skip empty patterns
                        continue

                    # scaled row commands
                    for sy in range(scale):
                        current_y = lua_y + row_idx * scale + sy
                        if current_y <= 400:  # Check y boundary
                            pattern_hex = ''.join([f'\\x{b:02x}' for b in pattern])
                            cmd = f'frame.display.bitmap({lua_x},{current_y},{width},{color_mode},{color},"{pattern_hex}")'
                            commands.append(cmd)

            # Execute commands in chunks to maintain connection
            CHUNK_SIZE = 40
            for i in range(0, len(commands), CHUNK_SIZE):
                chunk = commands[i:i + CHUNK_SIZE]
                for cmd in chunk:
                    await self.frame.run_lua(cmd)
                await asyncio.sleep(0.001)
                
            await self.show()
            logging.debug("Image drawing completed successfully")
            return image_data

        except Exception as e:
            logging.error(f"Error during image drawing: {str(e)}")
            raise