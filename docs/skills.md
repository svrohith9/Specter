# Skills

## Overview
Skills are executable tools used by the execution graph. Built-ins live in `src/specter/skills/builtin/` and generated skills in `src/specter/skills/generated/`.

## Design
- Async functions with structured return values
- Registered via `SkillManager`
- Skills can be generated with code + tests via `POST /skills/forge`
- Skills can be installed from JSON via `POST /skills/install`

## Skill Forge payload
```json
{
  "description": "Summarize an array of bullet points",
  "examples": [
    { "input": { "bullets": ["a", "b"] }, "output": "a; b" }
  ]
}
```

Generated skills implement:
```python
async def run(params: dict) -> dict:
    return {"success": True, "data": ..., "error": None}
```

## Return format
```json
{ "success": true, "data": {}, "error": null }
```
