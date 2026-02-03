from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str


async def run(code: str, tests: str, timeout: int = 10) -> SandboxResult:
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        module_path = base / "skill_module.py"
        test_path = base / "skill_test.py"
        module_path.write_text(code, encoding="utf-8")
        test_path.write_text(tests, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "python",
            str(test_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return SandboxResult(False, "", "Timeout")

        success = proc.returncode == 0
        return SandboxResult(success, stdout.decode(), stderr.decode())
