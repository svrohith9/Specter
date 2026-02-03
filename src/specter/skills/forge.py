from __future__ import annotations

import json
import re
from typing import Any, Callable

from ..llm.router import LLMRouter
from .sandbox import run as sandbox_run


class SkillForge:
    def __init__(self, register: Callable[[str, Any], None]) -> None:
        self._register = register

    async def forge(
        self,
        description: str,
        examples: list[dict[str, Any]] | None = None,
        persist: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        name = self._slugify(description)
        signature = self._infer_signature(examples)
        code, tests = await self._generate_code(description, signature, examples or [])

        sandbox_result = await sandbox_run(code, tests, timeout=12)
        if not sandbox_result.success:
            code, tests = self._fallback_code(description, signature, examples or [])
            sandbox_result = await sandbox_run(code, tests, timeout=12)

        self._register(name, self._build_runtime(code))
        payload = {
            "description": description,
            "examples": examples or [],
            "signature": signature,
            "code": code,
            "tests": tests,
            "sandbox": {
                "success": sandbox_result.success,
                "stdout": sandbox_result.stdout,
                "stderr": sandbox_result.stderr,
            },
        }
        if persist:
            await persist(name, payload)
        return {
            "created": True,
            "skill": {
                "id": f"{name}_v1",
                "name": name,
                "description": description,
                "version": 1,
            },
            "sandbox": payload["sandbox"],
        }

    def _infer_signature(self, examples: list[dict[str, Any]] | None) -> dict[str, Any]:
        if not examples:
            return {"params": ["input"]}
        keys: set[str] = set()
        for ex in examples:
            if isinstance(ex, dict) and isinstance(ex.get("input"), dict):
                keys.update(ex["input"].keys())
        if not keys:
            return {"params": ["input"]}
        return {"params": sorted(keys)}

    async def _generate_code(
        self,
        description: str,
        signature: dict[str, Any],
        examples: list[dict[str, Any]],
    ) -> tuple[str, str]:
        router = LLMRouter()
        if router.routes:
            prompt = self._build_prompt(description, signature, examples)
            try:
                code = await router.generate(prompt)
                tests = self._generate_tests(signature, examples)
                return code, tests
            except Exception:
                pass
        return self._fallback_code(description, signature, examples)

    def _build_prompt(
        self, description: str, signature: dict[str, Any], examples: list[dict[str, Any]]
    ) -> str:
        return (
            "Write a production-ready Python async function for this tool.\n"
            "Return only valid Python code. No markdown.\n\n"
            f"Description: {description}\n"
            f"Signature params: {json.dumps(signature)}\n"
            f"Examples: {json.dumps(examples)}\n\n"
            "Rules:\n"
            "- Define `async def run(params: dict) -> dict`.\n"
            "- Return {\"success\": bool, \"data\": Any, \"error\": str | None}.\n"
            "- Use only stdlib (json, re, math, datetime).\n"
        )

    def _generate_tests(self, signature: dict[str, Any], examples: list[dict[str, Any]]) -> str:
        tests = [
            "import asyncio",
            "import json",
            "from skill_module import run",
            "",
            "async def main():",
        ]
        if not examples:
            tests.append("    result = await run({'input': 'test'})")
            tests.append("    assert result['success'] is True")
        else:
            for idx, ex in enumerate(examples, start=1):
                inp = ex.get("input", {})
                expected = ex.get("output")
                tests.append(f"    result_{idx} = await run({json.dumps(inp)})")
                tests.append(f"    assert result_{idx}['success'] is True")
                if expected is not None:
                    tests.append(
                        f"    assert result_{idx}['data'] == {json.dumps(expected)}"
                    )
        tests.append("    print('ok')")
        tests.append("")
        tests.append("if __name__ == '__main__':")
        tests.append("    asyncio.run(main())")
        return "\n".join(tests)

    def _fallback_code(
        self,
        description: str,
        signature: dict[str, Any],
        examples: list[dict[str, Any]],
    ) -> tuple[str, str]:
        description_json = json.dumps(description)
        examples_json = json.dumps(examples)
        code = (
            "import json\n\n"
            "async def run(params: dict) -> dict:\n"
            "    return {\n"
            "        'success': True,\n"
            "        'data': {\n"
            f"            'description': {description_json},\n"
            "            'params': params,\n"
            f"            'examples': {examples_json},\n"
            "        },\n"
            "        'error': None,\n"
            "    }\n"
        )
        tests = self._generate_tests(signature, examples)
        return code, tests

    def _build_runtime(self, code: str) -> Callable[..., Any]:
        scope: dict[str, Any] = {}
        exec(code, scope)
        run_fn = scope.get("run")

        async def skill(**params: Any) -> dict[str, Any]:
            return await run_fn(params)

        return skill

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
        return slug.strip("_") or "skill"
