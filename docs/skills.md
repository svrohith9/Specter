# Skills

## Overview
Skills are executable tools used by the execution graph. Built-ins live in `src/specter/skills/builtin/` and generated skills in `src/specter/skills/generated/`.

## Design
- Async functions with structured return values
- Registered via `SkillManager`
- Lightweight template skills can be created via `POST /skills/forge`
- Skills can be installed from JSON via `POST /skills/install`

## Return format
```json
{ "success": true, "data": {}, "error": null }
```
