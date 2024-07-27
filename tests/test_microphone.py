import os
import unittest
import asyncio
import sys
import time
import numpy as np

sys.path.append("..")
from src.frame_sdk import Frame

class TestMicrophone(unittest.IsolatedAsyncioTestCase):
    async def test_basic_audio_recording(self):
        async with Frame() as f:
            f.microphone.sample_rate = 8000
            f.microphone.bit_depth = 16
            audio_data = await f.microphone.record_audio(None, 5)
            self.assertAlmostEqual(len(audio_data), 5 * 8000, delta=4000)
            self.assertLessEqual(np.max(audio_data), np.iinfo(np.int16).max)
            self.assertGreaterEqual(np.min(audio_data), np.iinfo(np.int16).min)
            self.assertGreater(np.max(audio_data) - np.min(audio_data), 50)
            
            f.microphone.sample_rate = 16000
            f.microphone.bit_depth = 8
            audio_data = await f.microphone.record_audio(None, 5)
            self.assertAlmostEqual(len(audio_data), 5 * 16000, delta=4000)
            self.assertLessEqual(np.max(audio_data), np.iinfo(np.int8).max)
            self.assertGreaterEqual(np.min(audio_data), np.iinfo(np.int8).min)
            self.assertGreater(np.max(audio_data) - np.min(audio_data), 5)
    
    async def test_end_on_silence(self):
        async with Frame() as f:
            f.microphone.sample_rate = 8000
            f.microphone.bit_depth = 16
            await f.display.show_text("Testing microphone, please be silent!")
            audio_data = await f.microphone.record_audio(2, 20)
            await f.display.clear()
            self.assertLess(len(audio_data), 5 * 8000)
    
    async def test_save_audio(self):
        async with Frame() as f:
            f.microphone.sample_rate = 8000
            f.microphone.bit_depth = 16
            await f.display.show_text("Testing microphone, please be silent!")
            length = await f.microphone.save_audio_file("test.wav",2,20)
            await f.display.clear()
            self.assertLess(length, 5)
            self.assertTrue(os.path.exists("test.wav"))
            self.assertGreater(os.path.getsize("test.wav"), 2000)
            os.remove("test.wav")


if __name__ == "__main__":
    unittest.main()
