# Skills

## Overview
Skills are executable tools used by the execution graph. Built-ins live in `src/specter/skills/builtin/` and generated skills in `src/specter/skills/generated/`.

## Design
- Async functions with structured return values
- Registered via `SkillManager`
- (Planned) auto-generation with tests

## Return format
```json
{ "success": true, "data": {}, "error": null }
```
