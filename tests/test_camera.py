import os
import unittest
import asyncio
import sys
import time

from frame_sdk import Frame
from frame_sdk.camera import AutofocusType, Quality

class TestCamera(unittest.IsolatedAsyncioTestCase):
    async def test_get_photo(self):
        """
        Test taking a photo
        """
        async with Frame() as f:
            photo = await f.camera.take_photo()
            self.assertGreater(len(photo), 2000)

    async def test_save_photo_to_disk(self):
        """
        Test saving a photo to disk
        """
        async with Frame() as f:
            await f.camera.save_photo("test_photo.jpg")
            self.assertTrue(os.path.exists("test_photo.jpg"))
            self.assertGreater(os.path.getsize("test_photo.jpg"), 2000)
            os.remove("test_photo.jpg")

    async def test_photo_with_autofocus_options(self):
        """
        Test taking a photo with various autofocus options
        """
        async with Frame() as f:

            startTime = time.time()
            photo = await f.camera.take_photo(autofocus_seconds=None)
            endTime = time.time()
            self.assertGreater(len(photo), 2000)
            timeToTakePhotoWithoutAutoFocus = endTime - startTime

            startTime = time.time()
            photo = await f.camera.take_photo(autofocus_seconds=1, autofocus_type=AutofocusType.SPOT)
            endTime = time.time()
            self.assertGreater(len(photo), 2000)
            timeToTakePhotoWithAutoFocus1Sec = endTime - startTime

            self.assertGreater(timeToTakePhotoWithAutoFocus1Sec, timeToTakePhotoWithoutAutoFocus)

            startTime = time.time()
            photo = await f.camera.take_photo(autofocus_seconds=3, autofocus_type=AutofocusType.CENTER_WEIGHTED)
            endTime = time.time()
            self.assertGreater(len(photo), 2000)
            timeToTakePhotoWithAutoFocus3Sec = endTime - startTime

            self.assertGreater(timeToTakePhotoWithAutoFocus3Sec, timeToTakePhotoWithAutoFocus1Sec)

    async def test_photo_with_quality_options(self):
        """
        Test taking a photo with various quality options
        """
        async with Frame() as f:
            photo = await f.camera.take_photo(quality=Quality.VERY_LOW)
            very_low_quality_size = len(photo)
            self.assertGreater(very_low_quality_size, 2000)

            photo = await f.camera.take_photo(quality=Quality.LOW)
            low_quality_size = len(photo)
            self.assertGreater(low_quality_size, very_low_quality_size)

            photo = await f.camera.take_photo(quality=Quality.MEDIUM)
            medium_quality_size = len(photo)
            self.assertGreater(medium_quality_size, low_quality_size)

            photo = await f.camera.take_photo(quality=Quality.HIGH)
            high_quality_size = len(photo)
            self.assertGreater(high_quality_size, medium_quality_size)

            photo = await f.camera.take_photo(quality=Quality.VERY_HIGH)
            very_high_quality_size = len(photo)
            self.assertGreater(very_high_quality_size, high_quality_size)

    async def test_photo_with_resolution_options(self):
        """
        Test taking a photo with various resolution options
        """
        async with Frame() as f:
            photo = await f.camera.take_photo(resolution=100)
            res_100_size = len(photo)
            self.assertGreater(res_100_size, 1000)

            photo = await f.camera.take_photo(resolution=512)
            res_512_size = len(photo)
            self.assertGreater(res_512_size, res_100_size)

            photo = await f.camera.take_photo(resolution=720)
            res_720_size = len(photo)
            self.assertGreater(res_720_size, res_512_size)

    async def test_photo_with_pan_options(self):
        """
        Test taking a photo with various pan options
        """
        async with Frame() as f:
            photo = await f.camera.take_photo(pan=-140)
            pan_m140_size = len(photo)
            self.assertGreater(pan_m140_size, 2000)

            photo = await f.camera.take_photo(pan=140)
            pan_140_size = len(photo)
            self.assertGreater(pan_140_size, 2000)


if __name__ == "__main__":
    unittest.main()
