import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

class SessionLogger:
    """Writes session transcripts in JSONL format for auditing and diagnostics."""

    def __init__(self, logs_dir: Path, session_id: Optional[str] = None):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or f"session_{int(time.time())}"
        self.log_file = self.logs_dir / f"{self.session_id}.jsonl"
        self._step_counter = 0

    def log_step(self, step_type: str, payload: Dict[str, Any]):
        self._step_counter += 1
        entry = {
            "step": self._step_counter,
            "timestamp": time.time(),
            "type": step_type,
            "payload": payload
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
