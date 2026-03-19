from __future__ import annotations

import subprocess
import sys

from release_metadata import update_release_docs


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Comando falló: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def ensure_git_repo() -> None:
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"])
    except RuntimeError as exc:
        raise RuntimeError("No se detectó un repositorio Git en esta carpeta.") from exc


def main() -> int:
    try:
        ensure_git_repo()
        version, updated_date = update_release_docs("backup")

        run(["git", "add", "README.md", "historial.md"])
        run(["git", "add", "-A"])

        status = run(["git", "status", "--porcelain"])
        if not status:
            print("Sin cambios para respaldar.")
            return 0

        message = f"chore: backup {version} ({updated_date})"
        run(["git", "commit", "-m", message])
        run(["git", "push", "origin", "main"])

        print(f"Respaldo GitHub completado en origin/main con versión {version}.")
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
