from __future__ import annotations
import os
import uuid

class SessionContext:
    def __init__(self, session_id: str | None = None, user_role: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_role = user_role
        self._cache: dict = {}
        self._temp_files: list[str] = []

    def cache_set(self, key: str, value) -> None:
        self._cache[key] = value

    def cache_get(self, key: str):
        return self._cache.get(key)

    def register_temp_file(self, path: str) -> None:
        self._temp_files.append(path)

    def cleanup(self) -> None:
        self._cache.clear()
        for tmp_file in self._temp_files:
            try:
                os.unlink(tmp_file)
            except FileNotFoundError:
                pass
        self._temp_files.clear()

_SESSIONS: dict[str, SessionContext] = {}

def get_or_create_session(session_id: str, user_role: str) -> SessionContext:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = SessionContext(session_id, user_role)
    return _SESSIONS[session_id]

def end_session(session_id: str) -> None:
    session = _SESSIONS.pop(session_id, None)
    if session:
        session.cleanup()
