from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


def _base_url() -> str:
    return os.getenv("SPECTER_BASE_URL", "http://127.0.0.1:8000")


def _print(obj) -> None:  # noqa: ANN001
    print(json.dumps(obj, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    url = f"{_base_url()}/webhook/cli"
    payload = {"text": args.text, "user_id": args.user_id, "agent_id": args.agent_id}
    resp = httpx.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    _print(resp.json())


def cmd_tools(args: argparse.Namespace) -> None:
    url = f"{_base_url()}/tools"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    _print(resp.json())


def cmd_exec_get(args: argparse.Namespace) -> None:
    url = f"{_base_url()}/executions/{args.exec_id}"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    _print(resp.json())


def cmd_exec_list(args: argparse.Namespace) -> None:
    url = f"{_base_url()}/executions"
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    _print(resp.json())


def cmd_exec_replay(args: argparse.Namespace) -> None:
    url = f"{_base_url()}/executions/{args.exec_id}/replay"
    resp = httpx.post(url, timeout=60)
    resp.raise_for_status()
    _print(resp.json())


def cmd_skill_install(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    payload = {
        "name": data.get("name") or Path(args.file).stem,
        "description": data.get("description", "Installed skill"),
    }
    url = f"{_base_url()}/skills/install"
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    _print(resp.json())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specter-cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run a task")
    run.add_argument("text")
    run.add_argument("--user-id", default="local")
    run.add_argument("--agent-id", default=None)
    run.set_defaults(func=cmd_run)

    tools = sub.add_parser("tools", help="List tools")
    tools.set_defaults(func=cmd_tools)

    eg = sub.add_parser("exec-get", help="Get execution by id")
    eg.add_argument("exec_id")
    eg.set_defaults(func=cmd_exec_get)

    el = sub.add_parser("exec-list", help="List executions")
    el.set_defaults(func=cmd_exec_list)

    er = sub.add_parser("exec-replay", help="Replay execution")
    er.add_argument("exec_id")
    er.set_defaults(func=cmd_exec_replay)

    si = sub.add_parser("skill-install", help="Install skill from JSON")
    si.add_argument("file")
    si.set_defaults(func=cmd_skill_install)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
