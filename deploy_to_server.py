from __future__ import annotations

import argparse
import os
import posixpath
import shlex
import subprocess
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

from release_metadata import update_release_docs

ROOT = Path(__file__).resolve().parent


def run_local(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Comando local falló: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def git_tracked_files() -> list[str]:
    output = run_local(["git", "ls-files"])
    files = [line.strip() for line in output.splitlines() if line.strip()]
    if not files:
        raise RuntimeError("No se encontraron archivos versionados con git ls-files.")
    return files


def remote_quote(value: str) -> str:
    return shlex.quote(value)


def ensure_remote_dirs(sftp: paramiko.SFTPClient, remote_project_path: str, file_paths: list[str]) -> None:
    existing = {remote_project_path}
    for rel in file_paths:
        dir_rel = posixpath.dirname(rel.replace("\\", "/"))
        if not dir_rel:
            continue
        current = remote_project_path
        for chunk in dir_rel.split("/"):
            current = posixpath.join(current, chunk)
            if current in existing:
                continue
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)
            existing.add(current)


def ensure_remote_dir(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    parts = [chunk for chunk in remote_path.replace("\\", "/").split("/") if chunk]
    if remote_path.startswith("/"):
        current = "/"
    else:
        current = ""

    for part in parts:
        current = f"{current.rstrip('/')}/{part}" if current else part
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def upload_runtime_data(
    sftp: paramiko.SFTPClient,
    remote_project_path: str,
    local_instance: Path,
    local_uploads: Path,
) -> tuple[int, int]:
    db_uploaded = 0
    upload_files = 0

    if local_instance.exists():
        db_files = list(local_instance.glob("*.db")) + list(local_instance.glob("*.sqlite")) + list(local_instance.glob("*.sqlite3"))
        remote_instance_dir = posixpath.join(remote_project_path, "instance")
        ensure_remote_dir(sftp, remote_instance_dir)
        for db_file in db_files:
            remote_file = posixpath.join(remote_instance_dir, db_file.name)
            sftp.put(str(db_file), remote_file)
            db_uploaded += 1

    if local_uploads.exists():
        remote_upload_dir = posixpath.join(remote_project_path, "uploads")
        ensure_remote_dir(sftp, remote_upload_dir)
        for local_file in local_uploads.rglob("*"):
            if not local_file.is_file():
                continue
            rel = local_file.relative_to(local_uploads).as_posix()
            remote_file = posixpath.join(remote_upload_dir, rel)
            ensure_remote_dir(sftp, posixpath.dirname(remote_file))
            sftp.put(str(local_file), remote_file)
            upload_files += 1

    return db_uploaded, upload_files


def remote_file_exists(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
    try:
        sftp.stat(remote_path)
        return True
    except FileNotFoundError:
        return False


def walk_remote_files(sftp: paramiko.SFTPClient, remote_root: str) -> list[str]:
    files: list[str] = []
    stack = [remote_root]

    while stack:
        current = stack.pop()
        for entry in sftp.listdir_attr(current):
            child = posixpath.join(current, entry.filename)
            is_dir = bool(entry.st_mode & 0o040000)
            if is_dir:
                stack.append(child)
            else:
                files.append(child)

    return files


def sync_runtime_data_from_server(
    sftp: paramiko.SFTPClient,
    remote_project_path: str,
    local_instance: Path,
    local_uploads: Path,
) -> tuple[int, int, int]:
    db_downloaded = 0
    uploads_downloaded = 0
    uploads_skipped = 0

    remote_instance_dir = posixpath.join(remote_project_path, "instance")
    if remote_file_exists(sftp, remote_instance_dir):
        local_instance.mkdir(parents=True, exist_ok=True)
        for entry in sftp.listdir_attr(remote_instance_dir):
            remote_file = posixpath.join(remote_instance_dir, entry.filename)
            if bool(entry.st_mode & 0o040000):
                continue
            lower_name = entry.filename.lower()
            if not (lower_name.endswith(".db") or lower_name.endswith(".sqlite") or lower_name.endswith(".sqlite3")):
                continue
            local_file = local_instance / entry.filename
            sftp.get(remote_file, str(local_file))
            db_downloaded += 1

    remote_uploads_dir = posixpath.join(remote_project_path, "uploads")
    if remote_file_exists(sftp, remote_uploads_dir):
        local_uploads.mkdir(parents=True, exist_ok=True)
        for remote_file in walk_remote_files(sftp, remote_uploads_dir):
            rel = posixpath.relpath(remote_file, remote_uploads_dir)
            local_file = local_uploads / Path(rel)
            local_file.parent.mkdir(parents=True, exist_ok=True)

            # Requisito: no sobreescribir uploads existentes en desarrollo.
            if local_file.exists():
                uploads_skipped += 1
                continue

            sftp.get(remote_file, str(local_file))
            uploads_downloaded += 1

    return db_downloaded, uploads_downloaded, uploads_skipped


def upload_tracked_files(sftp: paramiko.SFTPClient, remote_project_path: str, file_paths: list[str]) -> None:
    ensure_remote_dirs(sftp, remote_project_path, file_paths)
    for rel in file_paths:
        local_file = ROOT / rel
        if not local_file.exists():
            continue
        remote_file = posixpath.join(remote_project_path, rel.replace("\\", "/"))
        sftp.put(str(local_file), remote_file)


def run_remote(ssh: paramiko.SSHClient, command: str, sudo_password: str | None = None) -> str:
    full_command = command
    if sudo_password is not None:
        full_command = f"echo {remote_quote(sudo_password)} | sudo -S bash -lc {remote_quote(command)}"

    stdin, stdout, stderr = ssh.exec_command(full_command)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")

    if exit_status != 0:
        raise RuntimeError(f"Comando remoto falló ({exit_status}): {command}\n{err.strip()}")
    return out.strip()


def resolve_remote_path(ssh: paramiko.SSHClient, remote_python: str, path_value: str) -> str:
    cmd = f"{remote_quote(remote_python)} -c {remote_quote(f'import os; print(os.path.expanduser({path_value!r}))')}"
    resolved = run_remote(ssh, cmd)
    if not resolved:
        raise RuntimeError("No fue posible resolver DEPLOY_REMOTE_PROJECT_PATH en el servidor remoto")
    return resolved


def load_required_env(*, require_public_url: bool = True) -> dict[str, str]:
    load_dotenv(ROOT / ".env")
    env = {
        "host": os.getenv("DEPLOY_SSH_HOST", "").strip(),
        "port": os.getenv("DEPLOY_SSH_PORT", "22").strip(),
        "user": os.getenv("DEPLOY_SSH_USER", "").strip(),
        "password": os.getenv("DEPLOY_SSH_PASSWORD", "").strip(),
        "service_name": os.getenv("DEPLOY_SERVICE_NAME", "contable").strip(),
        "remote_python": os.getenv("DEPLOY_PYTHON", "python3").strip(),
        "remote_venv": os.getenv("DEPLOY_REMOTE_VENV", ".venv").strip(),
        "remote_project": os.getenv("DEPLOY_REMOTE_PROJECT_PATH", "").strip(),
        "first_sync_data": os.getenv("DEPLOY_FIRST_SYNC_DATA", "0").strip(),
        "push_runtime_to_server": os.getenv("DEPLOY_PUSH_RUNTIME_TO_SERVER", "0").strip(),
        "pull_runtime_after_deploy": os.getenv("DEPLOY_PULL_RUNTIME_AFTER_DEPLOY", "1").strip(),
        "public_url": os.getenv("DEPLOY_PUBLIC_URL", "").strip(),
        "app_port": os.getenv("DEPLOY_APP_PORT", "5200").strip(),
    }
    required_fields = ["host", "user", "password", "remote_project"]
    if require_public_url:
        required_fields.append("public_url")

    for required in required_fields:
        if not env[required]:
            raise RuntimeError(f"Variable requerida no definida en .env: {required}")
    return env


def connect_ssh(env: dict[str, str]) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=env["host"],
        port=int(env["port"]),
        username=env["user"],
        password=env["password"],
        timeout=20,
    )
    return ssh


def build_service_content(remote_project: str, service_name: str) -> str:
    return "\n".join(
        [
            "[Unit]",
            f"Description={service_name} Flask Service",
            "After=network.target",
            "",
            "[Service]",
            "Type=simple",
            "User=ubuntu",
            "Group=ubuntu",
            f"WorkingDirectory={remote_project}",
            f"Environment=\"PATH={remote_project}/.venv/bin\"",
            f"ExecStart={remote_project}/.venv/bin/gunicorn --config {remote_project}/gunicorn_config.py wsgi:app",
            "Restart=always",
            "RestartSec=5",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )


def build_nginx_content(domain: str, remote_project: str, app_port: str) -> str:
    return "\n".join(
        [
            "server {",
            "    listen 80;",
            f"    server_name {domain};",
            "",
            "    location / {",
            f"        proxy_pass http://127.0.0.1:{app_port};",
            "        proxy_http_version 1.1;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "    }",
            "",
            "    location /static {",
            f"        alias {remote_project}/static;",
            "        expires 30d;",
            "    }",
            "",
            "    location /uploads {",
            f"        alias {remote_project}/uploads;",
            "        expires 7d;",
            "    }",
            "}",
            "",
        ]
    )


def deploy() -> None:
    run_local(["git", "rev-parse", "--is-inside-work-tree"])
    version, _ = update_release_docs("deploy")
    tracked = git_tracked_files()
    env = load_required_env(require_public_url=True)

    ssh = connect_ssh(env)

    try:
        remote_project = resolve_remote_path(ssh, env["remote_python"], env["remote_project"])
        service_content = build_service_content(remote_project, env["service_name"])
        nginx_content = build_nginx_content(env["public_url"], remote_project, env["app_port"])

        run_remote(ssh, f"mkdir -p {remote_quote(remote_project)}")
        sftp = ssh.open_sftp()
        try:
            upload_tracked_files(sftp, remote_project, tracked)

            push_runtime = env["push_runtime_to_server"].lower() in ("1", "true", "yes", "y")
            legacy_sync_data = env["first_sync_data"].lower() in ("1", "true", "yes", "y")

            if push_runtime:
                db_count, upload_count = upload_runtime_data(
                    sftp,
                    remote_project,
                    ROOT / "instance",
                    ROOT / "uploads",
                )
                print(
                    "ADVERTENCIA: runtime local -> servidor activado por DEPLOY_PUSH_RUNTIME_TO_SERVER. "
                    f"{db_count} base(s) y {upload_count} upload(s) copiados"
                )
            else:
                print("Seguro: deploy NO copia base de datos ni uploads locales hacia producción")
                if legacy_sync_data:
                    print("Aviso: DEPLOY_FIRST_SYNC_DATA está deprecada y ya no sube datos a producción")

            remote_service_path = posixpath.join(remote_project, f"{env['service_name']}.service")
            with sftp.file(remote_service_path, "w") as service_file:
                service_file.write(service_content)

            remote_nginx_path = posixpath.join(remote_project, f"nginx_{env['service_name']}.conf")
            with sftp.file(remote_nginx_path, "w") as nginx_file:
                nginx_file.write(nginx_content)
        finally:
            sftp.close()

        venv_path = posixpath.join(remote_project, env["remote_venv"])
        flask_app = "app:create_app"

        run_remote(ssh, f"cd {remote_quote(remote_project)} && {remote_quote(env['remote_python'])} -m venv {remote_quote(env['remote_venv'])}")
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cd {remote_quote(remote_project)}",
                    f"{remote_quote(venv_path + '/bin/pip')} install --upgrade pip",
                    f"{remote_quote(venv_path + '/bin/pip')} install -r requirements.txt",
                ]
            ),
        )
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cd {remote_quote(remote_project)}",
                    f"FLASK_APP={flask_app} {remote_quote(venv_path + '/bin/flask')} db upgrade",
                ]
            ),
        )

        service_name = env["service_name"]
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cp {remote_quote(posixpath.join(remote_project, service_name + '.service'))} /etc/systemd/system/{service_name}.service",
                    "systemctl daemon-reload",
                    f"systemctl enable {service_name}",
                    f"systemctl restart {service_name}",
                    f"systemctl is-active {service_name}",
                ]
            ),
            sudo_password=env["password"],
        )

        run_remote(
            ssh,
            " && ".join(
                [
                    "command -v nginx >/dev/null 2>&1 || (apt-get update && apt-get install -y nginx)",
                    f"cp {remote_quote(posixpath.join(remote_project, 'nginx_' + service_name + '.conf'))} /etc/nginx/sites-available/{service_name}",
                    f"ln -sfn /etc/nginx/sites-available/{service_name} /etc/nginx/sites-enabled/{service_name}",
                    "nginx -t",
                    "systemctl reload nginx",
                ]
            ),
            sudo_password=env["password"],
        )

        should_pull_runtime = env["pull_runtime_after_deploy"].lower() in ("1", "true", "yes", "y")
        if should_pull_runtime:
            sftp = ssh.open_sftp()
            try:
                db_count, uploads_count, skipped_count = sync_runtime_data_from_server(
                    sftp,
                    remote_project,
                    ROOT / "instance",
                    ROOT / "uploads",
                )
            finally:
                sftp.close()

            print(
                "Sync dev desde servidor: "
                f"{db_count} base(s) descargadas/reemplazadas, "
                f"{uploads_count} upload(s) nuevos descargados, "
                f"{skipped_count} upload(s) existentes omitidos"
            )
        else:
            print("Sync de runtime remoto->local deshabilitado por DEPLOY_PULL_RUNTIME_AFTER_DEPLOY")

        print(f"Deploy completado para versión {version}.")
    finally:
        ssh.close()


def sync_from_server_only() -> None:
    env = load_required_env(require_public_url=False)
    ssh = connect_ssh(env)

    try:
        remote_project = resolve_remote_path(ssh, env["remote_python"], env["remote_project"])
        sftp = ssh.open_sftp()
        try:
            db_count, uploads_count, skipped_count = sync_runtime_data_from_server(
                sftp,
                remote_project,
                ROOT / "instance",
                ROOT / "uploads",
            )
        finally:
            sftp.close()

        print(
            "Sync manual desde servidor completado: "
            f"{db_count} base(s) descargadas/reemplazadas, "
            f"{uploads_count} upload(s) nuevos descargados, "
            f"{skipped_count} upload(s) existentes omitidos"
        )
    finally:
        ssh.close()


def main() -> int:
    try:
        parser = argparse.ArgumentParser(description="Deploy y sincronizacion de runtime para Contable")
        parser.add_argument(
            "--sync-from-server-only",
            action="store_true",
            help="Descarga runtime desde servidor (instance y uploads) sin hacer deploy",
        )
        args = parser.parse_args()

        if args.sync_from_server_only:
            sync_from_server_only()
        else:
            deploy()
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
