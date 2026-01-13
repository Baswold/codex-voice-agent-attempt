from __future__ import annotations

import audioop
from typing import Optional

from .audio import AudioFrame


class WakeDetector:
    async def process(self, frame: AudioFrame) -> bool:
        raise NotImplementedError

    def reset(self) -> None:
        return


class EnergyWakeDetector(WakeDetector):
    def __init__(self, threshold: int = 1200, consecutive: int = 5) -> None:
        self.threshold = threshold
        self.consecutive = consecutive
        self._count = 0

    async def process(self, frame: AudioFrame) -> bool:
        energy = audioop.rms(frame.data, 2)
        if energy >= self.threshold:
            self._count += 1
        else:
            self._count = 0
        return self._count >= self.consecutive

    def reset(self) -> None:
        self._count = 0


class ManualWakeDetector(WakeDetector):
    def __init__(self) -> None:
        self._armed = True

    def trigger(self) -> None:
        self._armed = True

    async def process(self, frame: AudioFrame) -> bool:
        if self._armed:
            self._armed = False
            return True
        return False

    def reset(self) -> None:
        self._armed = True
