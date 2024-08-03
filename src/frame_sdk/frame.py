import asyncio
import hashlib
from typing import Awaitable, Callable, Optional
from .bluetooth import Bluetooth, FrameDataTypePrefixes
from .files import Files
from .camera import Camera
from .display import Display
from .microphone import Microphone
from .motion import Motion
import random
import re
import time

class Frame:
    """Represents a Frame device. Instantiate this class via `async with Frame() as f:`."""
    
    debug_on_new_connection: bool = False

    def __init__(self):
        """Initialize the Frame device and its components."""
        self.bluetooth = Bluetooth()
        self.files = Files(self)
        self.camera = Camera(self)
        self.display = Display(self)
        self.microphone = Microphone(self)
        self.motion = Motion(self)
        self._lua_on_wake = None
        self._callback_on_wake = None
        
    async def __aenter__(self) -> 'Frame':
        """Enter the asynchronous context manager."""
        await self.ensure_connected()
        return self
    
    async def __aexit__(self, exc_type: Optional[type], exc_value: Optional[BaseException], traceback: Optional[object]) -> None:
        """Exit the asynchronous context manager."""
        if self.bluetooth.is_connected():
            await self.bluetooth.disconnect()
        
    async def ensure_connected(self) -> None:
        """Ensure the Frame is connected, establishing a connection if not."""
        if not self.bluetooth.is_connected():
            await self.bluetooth.connect()
            self.bluetooth.print_debugging = Frame.debug_on_new_connection
            await self.bluetooth.send_break_signal()
            await self.inject_all_library_functions()
            await self.run_lua(f"is_awake=true;frame.time.utc({int(time.time())});frame.time.zone('{time.strftime('%z')[:3]}:{time.strftime('%z')[3:]}')", checked=True)

    async def evaluate(self, lua_expression: str) -> str:
        """Evaluates a Lua expression on the device and returns the result.
        
        Args:
            lua_expression (str): The Lua expression to evaluate.
        
        Returns:
            str: The result of the evaluation.
        """
        await self.ensure_connected()
        return await self.run_lua(f"prntLng(tostring({lua_expression}))", await_print=True)

    async def run_lua(self, lua_string: str, await_print: bool = False, checked: bool = False, timeout: Optional[float] = None) -> Optional[str]:
        """
        Run a Lua string on the device, automatically determining the appropriate method based on length.
        
        If `await_print=True` or `checked=True`, the function will block, otherwise it will return immediately.
        
        Args:
            lua_string (str): The Lua code to execute.
            await_print (bool): Whether to wait for a print statement from the Lua code.
            checked (bool): Whether to wait for confirmation of successful execution.
            timeout (Optional[float]): The maximum time to wait for execution.
        
        Returns:
            Optional[str]: The result of the Lua execution if `await_print` is True.
        """
        await self.ensure_connected()
        # replace any print() calls with prntLng() calls
        # TODO: this is a dirty hack and instead we should fix the implementation of print() in the Frame
        lua_string = re.sub(r'\bprint\(', 'prntLng(', lua_string)
        
        if len(lua_string) <= self.bluetooth.max_lua_payload():
            if checked and not await_print:
                lua_string += ";print(\"+\")"
                if len(lua_string) <= self.bluetooth.max_lua_payload():
                    result = await self.bluetooth.send_lua(lua_string, await_print=True, timeout=timeout)
                    if result != "+":
                        raise Exception(f"Lua did not run successfully: {result}")
                    return None
            else:
                return await self.bluetooth.send_lua(lua_string, await_print=await_print, timeout=timeout)
        
        return await self.send_long_lua(lua_string, await_print=await_print, checked=checked, timeout=timeout)

    async def send_long_lua(self, string: str, await_print: bool = False, checked: bool = False, timeout: Optional[float] = None) -> Optional[str]:
        """
        Sends a Lua string to the device that is longer than the MTU limit and thus
        must be sent via writing to a file and requiring that file.
        
        If `await_print=True` or `checked=True`, the function will block, otherwise it will return immediately.
        
        Args:
            string (str): The Lua code to execute.
            await_print (bool): Whether to wait for a print statement from the Lua code.
            checked (bool): Whether to wait for confirmation of successful execution.
            timeout (Optional[float]): The maximum time to wait for execution.
        
        Returns:
            Optional[str]: The result of the Lua execution if `await_print` is True.
        """
        await self.ensure_connected()
        
        # we use a random name here since require() only works once per file.
        # TODO: confirm that the Frame implementation of Lua actually works this way.  If not, we don't need to randomize the name.
        random_name = ''.join(chr(ord('a')+random.randint(0,25)) for _ in range(4))
        
        await self.files.write_file(f"/{random_name}.lua", string.encode(), checked=True)
        if await_print:
            response = await self.bluetooth.send_lua(f"require(\"{random_name}\")", await_print=True, timeout=timeout)
        elif checked:
            response = await self.bluetooth.send_lua(f"require(\"{random_name}\");print('done')", await_print=True, timeout=timeout)
            if response != "done":
                raise Exception(f"require() did not return 'done': {response}")
            response = None
        else:
            response = await self.bluetooth.send_lua(f"require(\"{random_name}\")")
        await self.files.delete_file(f"/{random_name}.lua")
        return response
    
    async def get_battery_level(self) -> int:
        """Returns the battery level as a percentage between 1 and 100.
        
        Returns:
            int: The battery level percentage.
        """
        await self.ensure_connected()
        response = await self.bluetooth.send_lua("print(frame.battery_level())", await_print=True)
        return int(float(response))
    
    async def delay(self, seconds: float) -> None:
        """Delays execution on Frame for a given number of seconds.  Technically this sends a sleep command, but it doesn't actually change the power mode.  This function does not block, returning immediately.
        
        Args:
            seconds (float): The number of seconds to sleep.
        """
        if seconds <= 0:
            raise ValueError("Delay seconds must be a positive number.")
        await self.ensure_connected()
        await self.run_lua(f"frame.sleep({seconds})")
    
    async def sleep(self, deep_sleep: bool = False) -> None:
        """Puts the Frame into sleep mode.  There are two modes: normal and deep.
        Normal sleep mode can still receive bluetooth data, and is essentially the same as clearing the display and putting the camera in low power mode.  The Frame will retain the time and date, and any functions and variables will stay in memory.
        Deep sleep mode saves additional power, but has more limitations.  The Frame will not retain the time and date, and any functions and variables will not stay in memory.  Blue data will not be received.  The only way to wake the Frame from deep sleep is to tap it.
        The difference in power usage is fairly low, so it's often best to use normal sleep mode unless you need the extra power savings.
        """
        await self.ensure_connected()
        if deep_sleep:
            await self.run_lua("frame.sleep()")
        else:
            if self._lua_on_wake is not None or self._callback_on_wake is not None:
                run_on_wake = self._lua_on_wake or ""
                if self._callback_on_wake is not None:
                    run_on_wake = "frame.bluetooth.send('\\x"+FrameDataTypePrefixes.WAKE.value_as_hex+"');"+run_on_wake
                run_on_wake = "if not is_awake then;is_awake=true;"+run_on_wake+";end"
                self.motion.run_on_tap(run_on_wake)
            await self.run_lua("frame.display.text(' ',1,1);frame.display.show();frame.camera.sleep()", checked=True)
            self.camera.is_awake = False
            
    async def stay_awake(self, value: bool) -> None:
        """Prevents Frame from going to sleep while it's docked onto the charging cradle.
        This can help during development where continuous power is needed, however may
        degrade the display or cause burn-in if used for extended periods of time.
        
        Args:
            value (bool): True to stay awake, False to allow sleep.
        """
        await self.ensure_connected()
        await self.run_lua(f"frame.stay_awake({str(value).lower()})", checked=True)
    
    async def inject_library_function(self, name: str, function: str, version: int) -> None:
        """
        Inject a function into the global environment of the device.  Used to push helper library functions to the device.
        
        Args:
            name (str): The name of the function.
            function (str): The function code.
            version (int): The version of the function.
        """
        await self.ensure_connected()
        
        exists = await self.bluetooth.send_lua(f"print({name} ~= nil)", await_print=True)
        if (self.bluetooth._print_debugging):
            print(f"Function {name} exists: {exists}")
        if (exists != "true"):
            # function does not yet exist, so let's see if the file for it does
            exists = await self.files.file_exists(f"/lib-{version}/{name}.lua")
            if (self.bluetooth._print_debugging):
                print(f"File /lib-{version}/{name}.lua exists: {exists}")

            if (exists):
                response = await self.bluetooth.send_lua(f"require(\"lib-{version}/{name}\");print(\"l\")", await_print=True)
                if response == "l":
                    return
            
            if (self.bluetooth._print_debugging):
                print(f"Writing file /lib-{version}/{name}.lua")
            await self.files.write_file(f"/lib-{version}/{name}.lua", function.encode(), checked=True)
            
            if (self.bluetooth._print_debugging):
                print(f"Requiring lib-{version}/{name}")
            response = await self.bluetooth.send_lua(f"require(\"lib-{version}/{name}\");print(\"l\")", await_print=True)
            if response != "l":
                raise Exception(f"Error injecting library function: {response}")
            
    async def inject_all_library_functions(self) -> None:
        """
        Inject all library functions into the global environment of the device.
        """
        from .library_functions import library_print_long
        # hash the library_print_long function to get a version id (take only the first 6 chars)
        library_version = hashlib.sha256(library_print_long.encode()).hexdigest()[:6]
        
        await self.ensure_connected()
        response = await self.bluetooth.send_lua(f"frame.file.mkdir(\"lib-{library_version}\");print(\"c\")", await_print=True)
        if response == "c":
            if (self.bluetooth._print_debugging):
                print("Created lib directory")
        else:
            if (self.bluetooth._print_debugging):
                print("Did not create lib directory: "+response)
        await self.inject_library_function("prntLng", library_print_long, library_version)
        
    
    def escape_lua_string(self, string: str) -> str:
        """Escape a string for use in Lua.
        
        Args:
            string (str): The string to escape.
        
        Returns:
            str: The escaped string.
        """
        return string.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t").replace("\"", "\\\"").replace("[", "[").replace("]", "]")
    
    async def run_on_wake(self, lua_script: Optional[str] = None, callback: Optional[Callable[[], None ]] = None) -> None:
        """
        Runs a Lua function when the device wakes up from sleep.  Can include lua code to be run on Frame upon wake and/or a python callback to be run locally upon wake.
        """
        self._lua_on_wake = lua_script
        self._callback_on_wake = callback

        if callback is not None:
            self.bluetooth.register_data_response_handler(FrameDataTypePrefixes.WAKE, lambda data: callback())
        else:
            self.bluetooth.register_data_response_handler(FrameDataTypePrefixes.WAKE, None)
        
        if lua_script is not None and callback is not None:
            await self.files.write_file("main.lua",("is_awake=true;frame.bluetooth.send('\\x"+FrameDataTypePrefixes.WAKE.value_as_hex+"');\n"+lua_script).encode(), checked=True)
        elif lua_script is None and callback is not None:
            await self.files.write_file("main.lua",("is_awake=true;frame.bluetooth.send('\\x"+FrameDataTypePrefixes.WAKE.value_as_hex+"')").encode(), checked=True)
        elif lua_script is not None and callback is None:
            await self.files.write_file("main.lua","is_awake=true;"+lua_script.encode(), checked=True)
        else:
            await self.files.write_file("main.lua",b"is_awake=true", checked=True)