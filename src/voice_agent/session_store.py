from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def record_turn(self, session_id: str, user_text: str, response_text: str, tools: List[Dict[str, Any]]) -> None:
        self.append(
            {
                "type": "turn",
                "session": session_id,
                "ts": time.time(),
                "user": user_text,
                "response": response_text,
                "tools": tools,
            }
        )

    def record_summary(self, session_id: str, summary: str) -> None:
        self.append(
            {
                "type": "summary",
                "session": session_id,
                "ts": time.time(),
                "summary": summary,
            }
        )
