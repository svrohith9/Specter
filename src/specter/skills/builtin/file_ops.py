from __future__ import annotations

from pathlib import Path

from ...config import settings


def _resolve_path(path: str) -> Path:
    root = Path(settings.specter.data_dir).resolve().parent
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    if root not in candidate.parents and candidate != root:
        raise ValueError("Path outside workspace root")
    return candidate


async def file_read(path: str, max_chars: int = 5000) -> dict:
    target = _resolve_path(path)
    if not target.exists():
        return {"success": False, "data": None, "error": "File not found"}
    data = target.read_text(encoding="utf-8", errors="ignore")
    if len(data) > max_chars:
        data = data[:max_chars] + "\n...truncated"
    return {"success": True, "data": {"path": str(target), "content": data}, "error": None}


async def file_write(path: str, content: str, append: bool = False) -> dict:
    target = _resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(target, mode, encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "data": {"path": str(target), "bytes": len(content)}, "error": None}


async def file_list(path: str = ".", pattern: str = "*") -> dict:
    target = _resolve_path(path)
    if not target.exists():
        return {"success": False, "data": None, "error": "Path not found"}
    results = [str(p.relative_to(target)) for p in target.glob(pattern)]
    return {"success": True, "data": {"path": str(target), "items": results}, "error": None}
