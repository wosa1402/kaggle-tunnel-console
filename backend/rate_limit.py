"""In-memory per-IP login brute-force protection.

Sliding-window failure counter: N failures inside WINDOW seconds triggers
a LOCKOUT. Counters live in memory only — restart clears them (acceptable
for auth rate limiting; data is advisory, not durable).
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict

from fastapi import HTTPException, Request, status

MAX_FAILURES = 5
WINDOW_SECONDS = 600      # 10 minutes
LOCKOUT_SECONDS = 900     # 15 minutes


@dataclass
class _Entry:
    failures: deque = field(default_factory=deque)
    locked_until: float = 0.0


class LoginRateLimiter:
    def __init__(self) -> None:
        self._entries: Dict[str, _Entry] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _prune(entry: _Entry, now: float) -> None:
        while entry.failures and now - entry.failures[0] > WINDOW_SECONDS:
            entry.failures.popleft()

    def check(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            entry = self._entries.get(ip)
            if entry and entry.locked_until > now:
                wait = int(entry.locked_until - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Try again in {wait}s.",
                    headers={"Retry-After": str(wait)},
                )

    def record_failure(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            entry = self._entries.setdefault(ip, _Entry())
            self._prune(entry, now)
            entry.failures.append(now)
            if len(entry.failures) >= MAX_FAILURES:
                entry.locked_until = now + LOCKOUT_SECONDS
                entry.failures.clear()

    def record_success(self, ip: str) -> None:
        with self._lock:
            self._entries.pop(ip, None)


login_limiter = LoginRateLimiter()


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
