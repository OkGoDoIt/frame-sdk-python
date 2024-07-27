from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import numpy as np
import asyncio
import simpleaudio
import time
import wave

if TYPE_CHECKING:
    from .frame import Frame

class Microphone:
    """Record and play audio using the Frame microphone."""

    frame: "Frame" = None
    _audio_buffer: Optional[np.ndarray] = None
        
    def __init__(self, frame: "Frame"):
        """
        Initialize the Microphone with a Frame instance.

        Args:
            frame (Frame): The Frame instance to associate with the Microphone.
        """
        self.frame = frame
        self._audio_buffer = None
        self._bit_depth = 16
        self._sample_rate = 8000
        self._silence_threshold = 0.02
        self._audio_finished_event = asyncio.Event()
        self._seconds_per_packet = 0
        self._last_sound_time = 0
        self._noise_floor = 0
    
    @property
    def silence_threshold(self) -> float:
        """
        Get the silence threshold as a float between 0 and 1.

        Returns:
            float: The current silence threshold.
        """
        return self._silence_threshold

    @silence_threshold.setter
    def silence_threshold(self, value: float) -> None:
        """
        Set the silence threshold to a float between 0 and 1.  0.02 is the default, however you may adjust this value to be more or less sensitive to sound.

        Args:
            value (float): The new silence threshold, between 0 and 1.
        """
        self._silence_threshold = value

    @property
    def bit_depth(self) -> int:
        """
        Get the bit depth (number of bits per audio sample), either 8 or 16.

        Returns:
            int: The current bit depth.
        """
        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, value: int) -> None:
        """
        Set the bit depth (number of bits per audio sample) to either 8 or 16.  The default is 16.

        Args:
            value (int): The new bit depth. Must be 8 or 16.

        Raises:
            ValueError: If the bit depth is not 8 or 16.
        """
        if value not in [8, 16]:
            raise ValueError("Bit depth must be 8 or 16")
        self._bit_depth = value

    @property
    def sample_rate(self) -> int:
        """
        Get the sample rate (number of audio samples per second), either 8000 or 16000.

        Returns:
            int: The current sample rate.
        """
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        """
        Set the sample rate (number of audio samples per second) to either 8000 or 16000.  The default is 8000.

        Args:
            value (int): The new sample rate. Must be 8000 or 16000.

        Raises:
            ValueError: If the sample rate is not 8000 or 16000.
        """
        if value not in [8000, 16000]:
            raise ValueError("Sample rate must be 8000 or 16000")
        self._sample_rate = value

    async def record_audio(self, silence_cutoff_length_in_seconds: Optional[int] = 3, max_length_in_seconds: Optional[int] = 30) -> np.ndarray:
        """
        Record audio from the microphone.

        Args:
            silence_cutoff_length_in_seconds (int): The length of silence to allow before stopping the recording.  Defaults to 3 seconds, however you can set to None to disable silence detection.
            max_length_in_seconds (int): The maximum length of the recording.  Defaults to 30 seconds.

        Returns:
            np.ndarray: The recorded audio data.
        """
        await self.frame.run_lua("frame.microphone.stop()", checked=False)

        self._audio_buffer = np.array([], dtype=np.int8 if self.bit_depth == 8 else np.int16)
        self.frame.bluetooth.data_response_handler = self._audio_buffer_handler
        self._audio_finished_event.clear()
        
        bytes_per_second = self.sample_rate * (self.bit_depth // 8)
        seconds_per_byte = 1 / bytes_per_second
        self._seconds_per_packet = seconds_per_byte * (self.frame.bluetooth.max_data_payload() - 1)
        self._silence_cutoff_length_in_seconds = silence_cutoff_length_in_seconds
        self._last_sound_time = time.time()
        
        if self.frame.bluetooth.print_debugging:
            print(f"Starting audio recording at {self.sample_rate} Hz, {self.bit_depth}-bit")
        await self.frame.bluetooth.send_lua(f"microphoneRecordAndSend({self.sample_rate},{self.bit_depth},nil)")
        try:
            await asyncio.wait_for(self._audio_finished_event.wait(), timeout=max_length_in_seconds)
            # Trim the final _silence_cutoff_length_in_seconds seconds
            trim_length = (self._silence_cutoff_length_in_seconds - 0.5) * self._sample_rate
            if len(self._audio_buffer) > trim_length:
                self._audio_buffer = self._audio_buffer[:-int(trim_length)]
        except asyncio.TimeoutError:
            pass
        if self.frame.bluetooth.print_debugging:
            print(f"\nAudio recording finished with {len(self._audio_buffer)*self._seconds_per_packet} seconds of audio")
        self.frame.bluetooth.data_response_handler = None
        await self.frame.bluetooth.send_break_signal()
        await self.frame.run_lua("frame.microphone.stop()")
        
        if len(self._audio_buffer) > 1024:
            return self._audio_buffer[1024:]
        else:
            return self._audio_buffer
    
    async def save_audio_file(self, filename: str, silence_cutoff_length_in_seconds: int = 3, max_length_in_seconds: int = 60) -> float:
        """
        Save the recorded audio to a file. Regardless of any filename extension, the file will be saved as a PCM wav file.

        Args:
            filename (str): The name of the file to save the audio to.
            silence_cutoff_length_in_seconds (int): The length of silence to detect before stopping the recording automatically.
            max_length_in_seconds (int): The maximum length of the recording.

        Returns:
            float: The length of the recorded audio in seconds.
        """
        audio_data = await self.record_audio(silence_cutoff_length_in_seconds, max_length_in_seconds)
        
        if len(audio_data) == 0:
            raise ValueError("No audio data recorded")

        # Normalize the 8 or 16 bit data range to (-1, 1) for playback
        if self.bit_depth == 8:
            audio_data = np.int16(audio_data)
        
        # based on the max and min values, normalize the data to be within the range of int16.min and int16.max.
        real_range = np.max(audio_data) - np.min(audio_data)
        ideal_range = np.iinfo(np.int16).max - np.iinfo(np.int16).min
        scale_factor = np.min([ideal_range / real_range, np.iinfo(np.int16).max / np.max(audio_data), np.iinfo(np.int16).min / np.min(audio_data)])
        audio_data = (audio_data * scale_factor).astype(np.int16)

        with wave.open(filename,"wb") as f:
            f.setnchannels(1)
            f.setsampwidth(16 // 8)
            f.setframerate(self.sample_rate)
            f.writeframes(audio_data.tobytes())
            
        length_in_seconds = len(audio_data) / self.sample_rate
        return length_in_seconds
    
    def _audio_buffer_handler(self, data: bytes) -> None:
        """
        Handle incoming audio data and update the audio buffer.

        Args:
            data (bytes): The incoming audio data.
        """
        if self._audio_buffer is None:
            return
        if data[0] != 5:
            # we expect the `microphoneRecordAndSend()` Lua function to send a 5 as the first byte of microphone data
            # if we receive anything else, we assume it's not microphone data and ignore it
            return
        
        audio_data = self._convert_bytes_to_audio_data(data[1:], self.bit_depth)
        self._audio_buffer = np.concatenate((self._audio_buffer, audio_data))
        
        if self._silence_cutoff_length_in_seconds is not None:
            min_amplitude = int(np.min(audio_data))
            max_amplitude = int(np.max(audio_data))
            delta = max_amplitude - min_amplitude
            
            if self._bit_depth == 8:
                delta = float(delta / np.iinfo(np.int8).max)
            elif self._bit_depth == 16:
                delta = float(delta / np.iinfo(np.int16).max)
            
            self._noise_floor = self._noise_floor + (delta - self._noise_floor) * 0.1
            
            if delta - self._noise_floor > self._silence_threshold:
                self._last_sound_time = time.time()
                if self.frame.bluetooth.print_debugging:
                    print("+", end="", flush=True)
            else:
                if time.time() - self._last_sound_time > self._silence_cutoff_length_in_seconds:
                    self._audio_finished_event.set()
                elif self.frame.bluetooth.print_debugging:
                    print("-", end="", flush=True)
    
    def _convert_bytes_to_audio_data(self, audio_buffer: bytes, bit_depth: int) -> np.ndarray:
        """
        Convert raw audio bytes to a NumPy array.

        Args:
            audio_buffer (bytes): The raw audio data.
            bit_depth (int): The bit depth of the audio data.

        Returns:
            np.ndarray: The converted audio data.
        """
        if bit_depth == 16:
            audio_data = np.frombuffer(bytearray(audio_buffer), dtype=np.int16)
        elif bit_depth == 8:
            audio_data = np.frombuffer(bytearray(audio_buffer), dtype=np.int8)
        else:
            raise ValueError("Unsupported bit depth")
        
        return audio_data
    
    def play_audio_background(self, audio_data: np.ndarray, sample_rate: Optional[int] = None, bit_depth: Optional[int] = None) -> simpleaudio.PlayObject:
        """
        Play audio data in the background.

        Args:
            audio_data (np.ndarray): The audio data to play.
            sample_rate (Optional[int]): The sample rate of the audio data. Defaults to the instance's sample rate.
            bit_depth (Optional[int]): The bit depth of the audio data. Defaults to the instance's bit depth.

        Returns:
            simpleaudio.PlayObject: The play object for the audio.
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        if bit_depth is None:
            bit_depth = self.bit_depth
            
        if bit_depth == 8:
            # Normalize to 16-bit range
            audio_data = audio_data.astype(np.int16)
            np.multiply(audio_data, 32767 / np.max(np.abs(audio_data)), out=audio_data, casting='unsafe')
        else:
            # Normalize to 16-bit range
            np.multiply(audio_data, 32767 / np.max(np.abs(audio_data)), out=audio_data, casting='unsafe')
            audio_data = audio_data.astype(np.int16)
        return simpleaudio.play_buffer(audio_data, num_channels=1, bytes_per_sample=2, sample_rate=sample_rate)
    
    def play_audio(self, audio_data: np.ndarray, sample_rate: Optional[int] = None, bit_depth: Optional[int] = None) -> None:
        """
        Play audio data and wait for it to finish.

        Args:
            audio_data (np.ndarray): The audio data to play.
            sample_rate (Optional[int]): The sample rate of the audio data. Defaults to the instance's sample rate.
            bit_depth (Optional[int]): The bit depth of the audio data. Defaults to the instance's bit depth.
        """
        player = self.play_audio_background(audio_data, sample_rate, bit_depth)
        player.wait_done()
    
    async def play_audio_async(self, audio_data: np.ndarray, sample_rate: Optional[int] = None, bit_depth: Optional[int] = None) -> None:
        """
        Play audio data asynchronously.

        Args:
            audio_data (np.ndarray): The audio data to play.
            sample_rate (Optional[int]): The sample rate of the audio data. Defaults to the instance's sample rate.
            bit_depth (Optional[int]): The bit depth of the audio data. Defaults to the instance's bit depth.
        """
        player = self.play_audio_background(audio_data, sample_rate, bit_depth)
        while player.is_playing():
            await asyncio.sleep(0.1)