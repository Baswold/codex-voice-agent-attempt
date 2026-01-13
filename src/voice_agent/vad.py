from __future__ import annotations

import audioop
from typing import AsyncIterator, Iterable, List

from .audio import AudioFrame


class EnergyVAD:
    def __init__(self, threshold: int = 500, speech_frames: int = 3, silence_frames: int = 5) -> None:
        self.threshold = threshold
        self.speech_frames = speech_frames
        self.silence_frames = silence_frames
        self._speech_count = 0
        self._silence_count = 0

    def reset(self) -> None:
        self._speech_count = 0
        self._silence_count = 0

    def is_speech(self, frame: AudioFrame) -> bool:
        energy = audioop.rms(frame.data, 2)
        if energy >= self.threshold:
            self._speech_count += 1
            self._silence_count = 0
        else:
            self._silence_count += 1
        speaking = self._speech_count >= self.speech_frames
        if self._silence_count >= self.silence_frames:
            self._speech_count = 0
        return speaking


async def segment_frames(frames: AsyncIterator[AudioFrame], vad: EnergyVAD) -> AsyncIterator[List[AudioFrame]]:
    current: List[AudioFrame] = []
    async for frame in frames:
        if vad.is_speech(frame):
            current.append(frame)
            continue
        if current:
            yield current
            current = []
    if current:
        yield current
