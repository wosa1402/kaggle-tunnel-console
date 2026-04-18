"""Kaggle CLI wrapper with per-account credential isolation.

Uses subprocess with explicit KAGGLE_CONFIG_DIR env var per call, so parallel
requests from different accounts don't step on each other.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import CREDS_DIR, TEMPLATE_IPYNB, WORK_DIR
from .db import Account

PLACEHOLDER = "{{TUNNEL_TOKEN}}"


def _creds_dir_for(account: Account) -> Path:
    d = CREDS_DIR / str(account.id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "kaggle.json"
    path.write_text(
        json.dumps(
            {"username": account.kaggle_username, "key": account.kaggle_api_key}
        ),
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return d


def _work_dir_for(account: Account) -> Path:
    d = WORK_DIR / str(account.id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run(args: list[str], creds_dir: Path, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    import os

    env = os.environ.copy()
    env["KAGGLE_CONFIG_DIR"] = str(creds_dir)
    return subprocess.run(
        args,
        env=env,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _render_template(template_path: Path, token: str) -> dict[str, Any]:
    nb = json.loads(template_path.read_text(encoding="utf-8"))
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", [])
        if isinstance(src, list):
            cell["source"] = [s.replace(PLACEHOLDER, token) for s in src]
        elif isinstance(src, str):
            cell["source"] = src.replace(PLACEHOLDER, token)
    return nb


def push_kernel(account: Account) -> dict[str, Any]:
    if not TEMPLATE_IPYNB.exists():
        raise FileNotFoundError(
            f"Template notebook not found at {TEMPLATE_IPYNB}. "
            "Upload your tunnel template .ipynb (with {{TUNNEL_TOKEN}} placeholder) first."
        )

    if "/" not in account.kernel_slug:
        raise ValueError("kernel_slug must be in the form 'username/slug'")

    rendered = _render_template(TEMPLATE_IPYNB, account.tunnel_token)

    work = _work_dir_for(account)
    nb_path = work / "notebook.ipynb"
    nb_path.write_text(json.dumps(rendered), encoding="utf-8")

    metadata = {
        "id": account.kernel_slug,
        "title": account.kernel_slug.split("/", 1)[1].replace("-", " ").title(),
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
    }
    (work / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    creds = _creds_dir_for(account)
    result = _run(["kaggle", "kernels", "push", "-p", str(work)], creds)

    if result.returncode != 0:
        return {
            "ok": False,
            "stage": "push",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    return {
        "ok": True,
        "stage": "push",
        "pushed_at": datetime.utcnow().isoformat(),
        "stdout": result.stdout,
    }


_STATUS_RE = re.compile(r'status\s+"?([a-zA-Z]+)"?', re.IGNORECASE)


def fetch_status(account: Account) -> dict[str, Any]:
    creds = _creds_dir_for(account)
    result = _run(
        ["kaggle", "kernels", "status", account.kernel_slug],
        creds,
    )
    raw = (result.stdout or "") + (result.stderr or "")
    m = _STATUS_RE.search(raw)
    status = m.group(1).lower() if m else "unknown"
    return {
        "ok": result.returncode == 0,
        "status": status,
        "raw": raw.strip(),
    }


def pull_kernel_source(account: Account, dest_dir: Path) -> dict[str, Any]:
    """Pull a kernel's source + metadata to dest_dir. Used for bootstrap."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    creds = _creds_dir_for(account)
    result = _run(
        ["kaggle", "kernels", "pull", account.kernel_slug, "-p", str(dest_dir), "-m"],
        creds,
    )
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
