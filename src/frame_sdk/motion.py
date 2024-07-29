from __future__ import annotations
import math
from typing import Awaitable, Callable, Optional, TYPE_CHECKING, Tuple
import asyncio

_FRAME_TAP_PREFIX = b'\x04'

if TYPE_CHECKING:
    from .frame import Frame

class Direction:
    """Represents a direction in 3D space."""
    roll: float
    """
    The roll angle of the Frame in degrees.
    Range: -180.0 to 180.0
    Examples:   0.0 (level)
                10.0 (right side slightly up, head tilted to the left)
                90.0 (right side up, laying down on your left side)
                -10.0 (left side slightly up, head tilted to the right)
                -90.0 (left side up, laying down on your right side)
    """
    
    pitch: float
    """
    The pitch angle of the Frame in degrees.
    Range: -180.0 to 180.0
    Example:    0.0 (level)
                20.0 (looking slightly downcast)
                -20.0 (looking slightly upwards)
                90.0 (nose straight up at the ceiling)
                -90.0 (nose straight down towards the floor)
                110.0 (tilted backwards over the top)
                -110.0 (tilted backwards underneath)
    """
    
    heading: float
    """
    TODO: NOT YET IMPLEMENTED IN THE FIRMWARE
    The heading angle of the Frame in degrees.
    Range: 0.0 to 360.0
    Example: 0.0 (North), 90.0 (East), 180.0 (South), 270.0 (West)
    """
    
    def __init__(self, roll: float = 0.0, pitch: float = 0.0, heading: float = 0.0):
        """
        Initialize the Direction with roll, pitch, and heading values.

        Args:
            roll (float): The roll angle of the Frame in degrees.
            pitch (float): The pitch angle of the Frame in degrees.
            heading (float): The heading angle of the Frame in degrees.
        """
        self.roll = roll
        self.pitch = pitch
        self.heading = heading

    def __str__(self) -> str:
        """
        Return a string representation of the Direction.

        Returns:
            str: A string representation of the Direction.
        """
        return f"Direction(roll={self.roll}, pitch={self.pitch}, heading={self.heading})"

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the Direction.

        Returns:
            str: A detailed string representation of the Direction.
        """
        return f"Direction(roll={self.roll}, pitch={self.pitch}, heading={self.heading})"

    def __add__(self, other: Direction) -> Direction:
        """
        Add two Direction objects.

        Args:
            other (Direction): The other Direction object to add.

        Returns:
            Direction: A new Direction object representing the sum of the two directions.
        """
        new_roll = self.roll + other.roll
        new_pitch = self.pitch + other.pitch
        new_heading = (self.heading + other.heading) % 360

        # Clamp roll to be within -180 to 180 degrees
        if new_roll > 180:
            new_roll -= 360
        elif new_roll < -180:
            new_roll += 360
            
        # Clamp pitch to be within -180 to 180 degrees
        if new_pitch > 180:
            new_pitch -= 360
        elif new_pitch < -180:
            new_pitch += 360

        return Direction(
            roll=new_roll,
            pitch=new_pitch,
            heading=new_heading
        )

    def __sub__(self, other: Direction) -> Direction:
        """
        Subtract one Direction object from another.

        Args:
            other (Direction): The other Direction object to subtract.

        Returns:
            Direction: A new Direction object representing the difference between the two directions.
        """
        new_roll = self.roll - other.roll
        new_pitch = self.pitch - other.pitch
        new_heading = (self.heading - other.heading) % 360

        # Clamp roll to be within -180 to 180 degrees
        if new_roll > 180:
            new_roll -= 360
        elif new_roll < -180:
            new_roll += 360
            
        # Clamp pitch to be within -180 to 180 degrees
        if new_pitch > 180:
            new_pitch -= 360
        elif new_pitch < -180:
            new_pitch += 360

        return Direction(
            roll=new_roll,
            pitch=new_pitch,
            heading=new_heading
        )

    def amplitude(self) -> float:
        """
        Calculate the amplitude of the Direction vector.

        Returns:
            float: The amplitude of the Direction vector.
        """
        return (self.roll**2 + self.pitch**2 + self.heading**2)**0.5

class Motion:
    """Handle motion on the Frame IMU."""

    frame: "Frame" = None
        
    def __init__(self, frame: "Frame"):
        """
        Initialize the Motion class with a Frame instance.
        
        Args:
            frame (Frame): The Frame instance to associate with the Motion class.
        """
        self.frame = frame
    
    async def get_direction(self) -> Direction:
        """Gets the orientation of the Frame.  Note that the `heading` is not yet implemented"""
        result = await self.frame.run_lua("local dir = frame.imu.direction();print(dir['roll']..','..dir['pitch']..','..dir['heading'])", await_print=True)
        result = result.split(",")
        direction = Direction(roll=float(result[0]), pitch=float(result[1]), heading=float(result[2]))
        
        return direction
    
    
    async def run_on_tap(self, lua_script: Optional[str] = None, callback: Optional[Callable[[], Awaitable[None]]] = None) -> None:
        """Run a callback when the Frame is tapped.  Can include lua code to be run on Frame upon tap and/or a python callback to be run locally upon tap."""
        
        if callback is not None:
            self.frame.bluetooth.register_data_response_handler(_FRAME_TAP_PREFIX, lambda data: asyncio.create_task(callback()))
        else:
            self.frame.bluetooth.register_data_response_handler(_FRAME_TAP_PREFIX, None)
        
        if lua_script is not None and callback is not None:
            await self.frame.run_lua("function on_tap();frame.bluetooth.send('\\x"+(_FRAME_TAP_PREFIX.hex(':').replace(':','\\x'))+"');"+lua_script+";end;frame.imu.tap_callback(on_tap)", checked=True)
        elif lua_script is None and callback is not None:
            await self.frame.run_lua("function on_tap();frame.bluetooth.send('\\x"+(_FRAME_TAP_PREFIX.hex(':').replace(':','\\x'))+"');end;frame.imu.tap_callback(on_tap)", checked=True)
        elif lua_script is not None and callback is None:
            await self.frame.run_lua("function on_tap();"+lua_script+";end;frame.imu.tap_callback(on_tap)", checked=True)
        else:
            await self.frame.run_lua("frame.imu.tap_callback(nil)", checked=False)
    
    async def wait_for_tap(self) -> None:
        """Wait for the Frame to be tapped before continuing."""
        self._waiting_on_tap = asyncio.Event()
        await self.run_on_tap(callback= lambda : self._waiting_on_tap.set())
        await self._waiting_on_tap.wait()
        await self.run_on_tap(callback=None)