import os
import unittest
import asyncio
import sys
import time
import numpy as np

from frame_sdk import Frame
from frame_sdk.motion import Direction

class TestMotion(unittest.IsolatedAsyncioTestCase):
    async def test_get_direction(self):
        async with Frame() as f:
            await f.display.show_text("Testing motion, don't move the Frame!")
            direction1 = await f.motion.get_direction()
            self.assertIsInstance(direction1, Direction)
            self.assertGreaterEqual(direction1.pitch, -180)
            self.assertLessEqual(direction1.pitch, 180)
            self.assertGreaterEqual(direction1.roll, -180)
            self.assertLessEqual(direction1.roll, 180)
            self.assertGreaterEqual(direction1.heading, 0)
            self.assertLessEqual(direction1.heading, 360)
            await asyncio.sleep(1)
            direction2 = await f.motion.get_direction()
            await f.display.clear()
            self.assertIsInstance(direction2, Direction)
            diff = direction2 - direction1
            self.assertAlmostEqual(diff.amplitude(), 0, delta=5)
            self.assertAlmostEqual(direction1.pitch, direction2.pitch, delta=5)
            self.assertAlmostEqual(direction1.roll, direction2.roll, delta=5)
            self.assertAlmostEqual(
                direction1.heading, direction2.heading, delta=5)

    async def test_register_tap_handler(self):
        async with Frame() as f:
            # no good way to actually test these being called, but let's at least make sure they don't throw errors
            await f.display.show_text("Testing tap, tap the Frame!")
            await f.motion.run_on_tap(callback=lambda: print("Tapped again!"))
            await f.motion.run_on_tap(lua_script="print('tap1')", callback=lambda: print("tap2"))
            await f.motion.run_on_tap(None, None)
            await asyncio.sleep(1)
            await f.motion.run_on_tap(lua_script="frame.display.text('tapped!',1,1);frame.display.show()")
            


if __name__ == "__main__":
    unittest.main()
