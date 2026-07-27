# /// script
# dependencies = [
#   "windup @ git+https://github.com/dipakkrishnan/windup.git@0b8d501",
# ]
# ///
"""Install Health OS's owner-approved recurring agentic refresh."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from windup import Task, install


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--cadence", choices=("daily", "weekly"), default="daily")
    parser.add_argument("--hour", type=int, default=7)
    parser.add_argument("--model", default="")
    parser.add_argument("--python", type=Path, required=True)
    args = parser.parse_args()

    plugin = Path(__file__).resolve().parent.parent
    repo = args.repo.expanduser().resolve()
    if not (repo / "health.db").is_file():
        parser.error(f"not a Health OS data repository: {repo}")
    python = args.python.expanduser().resolve()
    if not python.is_file() or not os.access(python, os.X_OK):
        parser.error(f"Python interpreter is not executable: {python}")

    state = repo / ".health-os"
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    prompt = state / "agentic-refresh.md"
    prompt.write_text(
        (plugin / "automation" / "agentic-refresh.md").read_text(encoding="utf-8")
        + "\n## Installed paths\n"
        + f"- Plugin root: `{json.dumps(str(plugin))}`\n"
        + f"- Health data repository: `{json.dumps(str(repo))}`\n"
        + f"- Python interpreter: `{json.dumps(str(python))}`\n",
        encoding="utf-8",
    )
    prompt.chmod(0o600)

    task = Task(
        id="health-os-agentic-refresh",
        name="Health OS refresh",
        agent=args.agent,
        prompt_path=prompt,
        cwd=repo,
        cadence=args.cadence,
        hour=args.hour,
        model=args.model,
        allowed_tools=(
            "Read",
            "Write",
            f"Bash({python} {plugin / 'core' / 'connect.py'} *)",
            f"Bash({python} {plugin / 'core' / 'health_core.py'} *)",
        ),
        environment=(
            ("HEALTH_OS_REPO", str(repo)),
            ("PLUGIN_ROOT", str(plugin)),
            ("PATH", os.environ.get("PATH", "/usr/bin:/bin")),
        ),
    )
    print(f"Installed {install(task)}")


if __name__ == "__main__":
    main()
