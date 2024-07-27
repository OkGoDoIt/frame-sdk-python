import asyncio
from typing import Optional, Callable, List, Tuple, Dict, Any

from bleak import BleakClient, BleakScanner, BleakError

_FRAME_DATA_PREFIX = 1
_FRAME_LONG_TEXT_PREFIX = 10
_FRAME_LONG_TEXT_END_PREFIX = 11
_FRAME_LONG_DATA_PREFIX = 1
_FRAME_LONG_DATA_END_PREFIX = 2

class Bluetooth:
    """
    Frame bluetooth class for managing a connection and transferring data to and
    from the device.
    """

    _SERVICE_UUID: str = "7a230001-5475-a6a4-654c-8431f6ad49c4"
    _TX_CHARACTERISTIC_UUID: str = "7a230002-5475-a6a4-654c-8431f6ad49c4"
    _RX_CHARACTERISTIC_UUID: str = "7a230003-5475-a6a4-654c-8431f6ad49c4"
    
    def __init__(self):
        self._btle_client: Optional[BleakClient] = None
        self._tx_characteristic: Optional[Any] = None
        self._user_disconnect_handler: Callable[[], None] = lambda: None
        
        self._max_receive_buffer: int = 10 * 1024 * 1024
        self._print_debugging: bool = False
        self._default_timeout: float = 10.0
        
        self._last_print_response: str = ""
        self._ongoing_print_response: Optional[bytearray] = None
        self._ongoing_print_response_chunk_count: Optional[int] = None
        self._print_response_event: asyncio.Event = asyncio.Event()
        self._user_print_response_handler: Callable[[str], None] = lambda _: None
        
        self._last_data_response: bytes = bytes()
        self._ongoing_data_response: Optional[bytearray] = None
        self._ongoing_data_response_chunk_count: Optional[int] = None
        self._data_response_event: asyncio.Event = asyncio.Event()
        self._user_data_response_handler: Callable[[bytes], None] = lambda _: None


    def _disconnect_handler(self, _: Any) -> None:
        """Called internally when the bluetooth connection is lost.  To add your own handler, supply a `disconnect_handler` when connecting.
        """
        self._user_disconnect_handler()
        self.__init__()


    async def _notification_handler(self, _: Any, data: bytearray) -> None:
        """Called internally when a notification is received from the device.  To add your own handlers, supply a `data_response_handler` and/or `print_response_handler` when connecting.

        Args:
            data (bytearray): The data received from the device as raw bytes

        Raises:
            Exception: _description_
            Exception: _description_
            Exception: _description_
            Exception: _description_
        """
        if data[0] == _FRAME_LONG_TEXT_PREFIX:
            # start of long printed data from prntLng() function
            if self._ongoing_print_response is None or self._ongoing_print_response_chunk_count is None:
                self._ongoing_print_response = bytearray()
                self._ongoing_print_response_chunk_count = 0
                if self._print_debugging:
                    print("Starting receiving new long printed string")
            self._ongoing_print_response += data[1:]
            self._ongoing_print_response_chunk_count += 1
            if self._print_debugging:
                print(f"Received chunk #{self._ongoing_print_response_chunk_count}: "+data[1:].decode())
            if len(self._ongoing_print_response) > self._max_receive_buffer:
                raise Exception(f"Buffered received long printed string is more than {self._max_receive_buffer} bytes")
            
        elif data[0] == _FRAME_LONG_TEXT_END_PREFIX:
            # end of long printed data from prntLng() function
            total_expected_chunk_count_as_string: str = data[1:].decode()
            if len(total_expected_chunk_count_as_string) > 0:
                total_expected_chunk_count: int = int(total_expected_chunk_count_as_string)
                if self._print_debugging:
                    print(f"Received final string chunk count: {total_expected_chunk_count}")
                if self._ongoing_print_response_chunk_count != total_expected_chunk_count:
                    raise Exception(f"Chunk count mismatch in long received string (expected {total_expected_chunk_count}, got {self._ongoing_print_response_chunk_count})")
            self._last_print_response = self._ongoing_print_response.decode()
            self._print_response_event.set()
            self._ongoing_print_response = None
            self._ongoing_print_response_chunk_count = None
            if self._print_debugging:
                print("Finished receiving long printed string: "+self._last_print_response)
            self._user_print_response_handler(self._last_print_response)
            
        elif data[0] == _FRAME_DATA_PREFIX and data[1] == _FRAME_LONG_DATA_PREFIX:
            # start of long raw data from frame.bluetooth.send("\001"..data)
            if self._ongoing_data_response is None or self._ongoing_data_response_chunk_count is None:
                self._ongoing_data_response = bytearray()
                self._ongoing_data_response_chunk_count = 0
                self._last_data_response = None
                if self._print_debugging:
                    print("Starting receiving new long raw data")
            self._ongoing_data_response += data[2:]
            self._ongoing_data_response_chunk_count += 1
            if self._print_debugging:
                print(f"Received data chunk #{self._ongoing_data_response_chunk_count}: {len(data[2:])} bytes")
            if len(self._ongoing_data_response) > self._max_receive_buffer:
                raise Exception(f"Buffered received long raw data is more than {self._max_receive_buffer} bytes")
            
        elif data[0] == _FRAME_DATA_PREFIX and data[1] == _FRAME_LONG_DATA_END_PREFIX:
            # end of long raw data from frame.bluetooth.send("\002"..chunkCount)
            total_expected_chunk_count_as_string: str = data[2:].decode()
            if len(total_expected_chunk_count_as_string) > 0:
                total_expected_chunk_count: int = int(total_expected_chunk_count_as_string)
                if self._print_debugging:
                    print(f"Received final data chunk count: {total_expected_chunk_count}")
                if self._ongoing_data_response_chunk_count != total_expected_chunk_count:
                    raise Exception(f"Chunk count mismatch in long received data (expected {total_expected_chunk_count}, got {self._ongoing_data_response_chunk_count})")
            self._last_data_response = bytes(self._ongoing_data_response)
            self._data_response_event.set()
            self._ongoing_data_response = None
            self._ongoing_data_response_chunk_count = None
            if self._print_debugging:
                if self._last_data_response is None:
                    print("Finished receiving long raw data: No data")
                else:
                    print(f"Finished receiving long raw data: {len(self._last_data_response)} bytes")
            self._user_data_response_handler(self._last_data_response)
            
        elif data[0] == _FRAME_DATA_PREFIX:
            # received single chunk raw data from frame.bluetooth.send(data)
            if self._print_debugging:
                print(f"Received data: {len(data[1:])} bytes")
            self._last_data_response = data[1:]
            self._data_response_event.set()
            self._user_data_response_handler(data[1:])
            
        else:
            # received single chunk printed text from print()
            self._last_print_response = data.decode()
            if self._print_debugging:
                print(f"Received printed string: {self._last_print_response}")
            self._print_response_event.set()
            self._user_print_response_handler(data.decode())

    @property
    def data_response_handler(self) -> Callable[[bytes], None]:
        return self._user_data_response_handler

    @data_response_handler.setter
    def data_response_handler(self, handler: Callable[[bytes], None]) -> None:
        if handler is None:
            self._user_data_response_handler = lambda _: None
        else:
            self._user_data_response_handler = handler

    @property
    def print_response_handler(self) -> Callable[[str], None]:
        return self._user_print_response_handler

    @print_response_handler.setter
    def print_response_handler(self, handler: Callable[[str], None]) -> None:
        if handler is None:
            self._user_print_response_handler = lambda _: None
        else:
            self._user_print_response_handler = handler

    async def connect(
        self,
        print_response_handler: Callable[[str], None] = lambda _: None,
        data_response_handler: Callable[[bytes], None] = lambda _: None,
        disconnect_handler: Callable[[], None] = lambda: None,
        print_debugging: bool = False,
        default_timeout: float = 10.0,
    ) -> None:
        """
        Connects to the nearest Frame device.

        `print_response_handler` and `data_response_handler` can be provided and
        will be called whenever data arrives from the device asynchronously.

        `disconnect_handler` can be provided to be called to run upon a disconnect.
        
        `print_debugging` will output the raw bytes that are sent and received from Frame if set to True
        `default_timeout` is the default timeout for waiting for a response from Frame, in seconds.  Defaults to 10 seconds.
        """
        self._user_disconnect_handler = disconnect_handler
        self._user_print_response_handler = print_response_handler
        self._user_data_response_handler = data_response_handler
        self._print_debugging = print_debugging
        self._default_timeout = default_timeout

        # returns list of (BLEDevice, AdvertisementData)
        devices: Dict[str, Tuple[Any, Any]] = await BleakScanner.discover(3, return_adv=True)

        filtered_list: List[Tuple[Any, Any]] = []
        for d in devices.values():
            if self._SERVICE_UUID in d[1].service_uuids:
                filtered_list.append(d)

        # connect to closest device
        filtered_list.sort(key=lambda x: x[1].rssi, reverse=True)
        try:
            device: Any = filtered_list[0][0]

        except IndexError:
            raise Exception("No Frame devices found")

        self._btle_client = BleakClient(
            device,
            disconnected_callback=self._disconnect_handler,
        )

        try:
            await self._btle_client.connect()

            await self._btle_client.start_notify(
                self._RX_CHARACTERISTIC_UUID,
                self._notification_handler,
            )
        except BleakError as e:
            raise Exception("Device needs to be re-paired: "+str(e))

        service: Any = self._btle_client.services.get_service(
            self._SERVICE_UUID,
        )

        self._tx_characteristic = service.get_characteristic(
            self._TX_CHARACTERISTIC_UUID,
        )

    async def disconnect(self) -> None:
        """
        Disconnects from the device.
        """
        await self._btle_client.disconnect()
        self._disconnect_handler(None)

    def is_connected(self) -> bool:
        """
        Returns `True` if the device is connected. `False` otherwise.
        """
        try:
            return self._btle_client.is_connected
        except AttributeError:
            return False

    def max_lua_payload(self) -> int:
        """
        Returns the maximum length of a Lua string which may be transmitted.  This is equal to the MTU - 3.
        """
        try:
            return self._btle_client.mtu_size - 3
        except AttributeError:
            return 0

    def max_data_payload(self) -> int:
        """
        Returns the maximum length of a raw bytearray which may be transmitted.  This is equal to the MTU - 4 (since data is prefixed with a 1 byte header).
        """
        try:
            return self._btle_client.mtu_size - 4
        except AttributeError:
            return 0
    
    @property
    def default_timeout(self) -> float:
        """
        Gets the default timeout value in seconds
        """
        return self._default_timeout

    @default_timeout.setter
    def default_timeout(self, value: float) -> None:
        """
        Sets the default timeout value in seconds
        """
        if value < 0:
            raise ValueError("default_timeout must be a non-negative float")
        self._default_timeout = value
    
    @property
    def print_debugging(self) -> bool:
        """
        Gets whether to print debugging information when sending data.
        """
        return self._print_debugging

    @print_debugging.setter
    def print_debugging(self, value: bool) -> None:
        """
        Sets whether to print debugging information when sending data.
        """
        self._print_debugging = value

    async def _transmit(self, data: bytearray) -> None:
        """Internal function for sending raw data to the device.  Instead of using this, use `send_lua()` or `send_data()`

        Args:
            data (bytearray): The data to send to the device as raw bytes

        Raises:
            Exception: If the payload length is too large
        """
        if self._print_debugging:
            print(data)  # TODO make this print nicer

        if len(data) > self._btle_client.mtu_size - 3:
            raise Exception(f"Payload length is too large: {len(data)} > {self._btle_client.mtu_size - 3}")

        await self._btle_client.write_gatt_char(self._tx_characteristic, data)

    async def send_lua(self, string: str, await_print: bool = False, timeout: Optional[float] = None) -> Optional[str]:
        """
        Sends a Lua string to the device. The string length must be less than or
        equal to `max_lua_payload()`.
        
        In general, you'd be better off using Frame.run_lua(), which handles sending an receiving values longer that the MTU limit.  This is the lower-level function to send an individual Lua string.
        
        If `await_print=True`, the function will block until a Lua print()
        occurs, or a timeout.
        """
        await self._transmit(string.encode())

        if await_print:
            return await self.wait_for_print(timeout)
        
    async def wait_for_print(self, timeout: Optional[float] = None) -> str:
        """
        Waits until a Lua print() occurs, with a max timeout in seconds.  If `timeout` is not provided, the default timeout will be used, rather than no timeout at all.
        """
        if timeout is None:
            timeout = self._default_timeout

        self._print_response_event.clear()

        try:
            await asyncio.wait_for(self._print_response_event.wait(), timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Frame didn't respond with printed data (from print() or prntLng()) within {timeout} seconds")

        return self._last_print_response
    
    async def wait_for_data(self, timeout: Optional[float] = None) -> bytes:
        """
        Waits until data has been received from the device, with a max timeout in seconds.  If `timeout` is not provided, the default timeout will be used, rather than no timeout at all.
        """
        if timeout is None:
            timeout = self._default_timeout

        self._data_response_event.clear()

        try:
            await asyncio.wait_for(self._data_response_event.wait(), timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Frame didn't respond with data (from frame.bluetooth.send(data)) within {timeout} seconds")
        return self._last_data_response

    async def send_data(self, data: bytearray, await_data: bool = False) -> Optional[bytes]:
        """
        Sends raw data to the device. The payload length must be less than or
        equal to `max_data_payload()`.
        
        If `await_data=True`, the function will block until a data response
        occurs, or a timeout.
        """
        await self._transmit(bytearray(b"\x01") + data)

        if await_data:
            return await self.wait_for_data()

    async def send_reset_signal(self) -> None:
        """
        Sends a reset signal to the device which will reset the Lua virtual
        machine.
        """
        if not self.is_connected():
            await self.connect()
        await self._transmit(bytearray(b"\x04"))

    async def send_break_signal(self) -> None:
        """
        Sends a break signal to the device which will break any currently
        executing Lua script.
        """
        if not self.is_connected():
            await self.connect()
        await self._transmit(bytearray(b"\x03"))