import unittest
import asyncio
import sys

from frame_sdk import Bluetooth, Frame

class TestBluetooth(unittest.IsolatedAsyncioTestCase):
    async def test_connect_disconnect(self):
        b = Bluetooth()

        self.assertFalse(b.is_connected())

        await b.connect()
        self.assertTrue(b.is_connected())

        await b.disconnect()
        self.assertFalse(b.is_connected())

    async def test_send_lua(self):
        async with Frame() as f:

            self.assertEqual(await f.bluetooth.send_lua("print('hi')", await_print=True), "hi")

            self.assertIsNone(await f.bluetooth.send_lua("print('hi')"))
            await asyncio.sleep(0.1)

            with self.assertRaises(Exception):
                await f.run_lua("a = 1", await_print=True, timeout=1)


    async def test_send_data(self):
        async with Frame() as f:
            await f.bluetooth.send_lua(
                "frame.bluetooth.receive_callback((function(d)frame.bluetooth.send(d)end))"
            )

            self.assertEqual(await f.bluetooth.send_data(b"test", await_data=True), b"test")

            self.assertIsNone(await f.bluetooth.send_data(b"test"))
            await asyncio.sleep(0.1)

            await f.bluetooth.send_lua("frame.bluetooth.receive_callback(nil)")

            with self.assertRaises(Exception):
                await f.bluetooth.send_data(b"test", await_data=True)

    async def test_mtu(self):
        b = Bluetooth()
        await b.connect()

        max_lua_length = b.max_lua_payload()
        max_data_length = b.max_data_payload()

        self.assertEqual(max_lua_length, max_data_length + 1)

        with self.assertRaises(Exception):
            await b.send_lua("a" * max_lua_length + 1)

        with self.assertRaises(Exception):
            await b.send_data(bytearray(b"a" * max_data_length + 1))

        await b.disconnect()


if __name__ == "__main__":
    unittest.main()
