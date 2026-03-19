from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
README_PATH = ROOT / "README.md"
HISTORIAL_PATH = ROOT / "historial.md"


def current_version() -> str:
    now = dt.date.today()
    return f"1.{now.year}.{now.month:02d}{now.day:02d}"


def current_date_iso() -> str:
    return dt.date.today().isoformat()


def update_readme(version: str, updated_date: str) -> None:
    text = README_PATH.read_text(encoding="utf-8")
    text = re.sub(r"^- Version: .*", f"- Version: {version}", text, flags=re.MULTILINE)
    text = re.sub(
        r"^- Ultima actualizacion: .*",
        f"- Ultima actualizacion: {updated_date}",
        text,
        flags=re.MULTILINE,
    )
    README_PATH.write_text(text, encoding="utf-8")


def update_historial(version: str, updated_date: str, operation: str) -> None:
    text = HISTORIAL_PATH.read_text(encoding="utf-8")

    header_re = re.compile(r"^## \[[^\]]+\] - \d{4}-\d{2}-\d{2}", re.MULTILINE)
    first_header = header_re.search(text)

    if first_header:
        text = text[: first_header.start()] + f"## [{version}] - {updated_date}" + text[first_header.end() :]
    else:
        text += f"\n\n## [{version}] - {updated_date}\n"

    infra_lines = {
        "backup": "- Respaldo a GitHub ejecutado mediante backup_to_github.py.",
        "deploy": "- Deploy a produccion ejecutado mediante deploy_to_server.py.",
    }

    marker = "### Infraestructura"
    idx = text.find(marker)
    if idx != -1:
        section_end = text.find("\n### ", idx + len(marker))
        if section_end == -1:
            section_end = len(text)
        section = text[idx:section_end]
        line = infra_lines[operation]
        if line not in section:
            if section.rstrip().endswith("Sin cambios."):
                section = section.replace("- Sin cambios.", line)
            else:
                section = section.rstrip() + f"\n{line}\n"
            text = text[:idx] + section + text[section_end:]

    HISTORIAL_PATH.write_text(text, encoding="utf-8")


def update_release_docs(operation: str) -> tuple[str, str]:
    version = current_version()
    updated_date = current_date_iso()
    update_readme(version, updated_date)
    update_historial(version, updated_date, operation)
    return version, updated_date
