"""In-process job registry for research runs. Ephemeral unless persisted to disk."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}
_PERSIST_DIR = Path("data/api_jobs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_type: str, payload: dict[str, Any]) -> str:
    job_id = uuid.uuid4().hex[:12]
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": _now(),
        "updated_at": _now(),
        "job_type": job_type,
        "payload": payload,
        "error": None,
        "result": None,
    }
    with _LOCK:
        _JOBS[job_id] = record
    _persist(job_id)
    return job_id


def get_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is not None:
            return dict(job)
    path = _PERSIST_DIR / f"{job_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        items = sorted(_JOBS.values(), key=lambda j: j["created_at"], reverse=True)
        return [dict(j) for j in items[:limit]]


def _update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = _now()
    _persist(job_id)


def _persist(job_id: str) -> None:
    try:
        _PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            job = _JOBS.get(job_id)
            if not job:
                return
            payload = dict(job)
        path = _PERSIST_DIR / f"{job_id}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def run_in_background(job_id: str, fn: Callable[[], dict[str, Any]]) -> None:
    def worker() -> None:
        _update(job_id, status="running")
        try:
            result = fn()
            _update(job_id, status="completed", result=result, error=None)
        except Exception as exc:
            _update(job_id, status="failed", error=str(exc), result=None)

    thread = threading.Thread(target=worker, name=f"job-{job_id}", daemon=True)
    thread.start()
