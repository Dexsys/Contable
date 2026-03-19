from __future__ import annotations

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


def load_required_env() -> dict[str, str]:
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
        "public_url": os.getenv("DEPLOY_PUBLIC_URL", "").strip(),
        "app_port": os.getenv("DEPLOY_APP_PORT", "5200").strip(),
    }
    for required in ("host", "user", "password", "remote_project", "public_url"):
        if not env[required]:
            raise RuntimeError(f"Variable requerida no definida en .env: {required}")
    return env


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
    env = load_required_env()

    service_content = build_service_content(env["remote_project"], env["service_name"])
    nginx_content = build_nginx_content(env["public_url"], env["remote_project"], env["app_port"])

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=env["host"],
        port=int(env["port"]),
        username=env["user"],
        password=env["password"],
        timeout=20,
    )

    try:
        run_remote(ssh, f"mkdir -p {remote_quote(env['remote_project'])}")
        sftp = ssh.open_sftp()
        try:
            upload_tracked_files(sftp, env["remote_project"], tracked)

            remote_service_path = posixpath.join(env["remote_project"], f"{env['service_name']}.service")
            with sftp.file(remote_service_path, "w") as service_file:
                service_file.write(service_content)

            remote_nginx_path = posixpath.join(env["remote_project"], f"nginx_{env['service_name']}.conf")
            with sftp.file(remote_nginx_path, "w") as nginx_file:
                nginx_file.write(nginx_content)
        finally:
            sftp.close()

        venv_path = posixpath.join(env["remote_project"], env["remote_venv"])
        flask_app = "app:create_app"

        run_remote(ssh, f"cd {remote_quote(env['remote_project'])} && {remote_quote(env['remote_python'])} -m venv {remote_quote(env['remote_venv'])}")
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cd {remote_quote(env['remote_project'])}",
                    f"{remote_quote(venv_path + '/bin/pip')} install --upgrade pip",
                    f"{remote_quote(venv_path + '/bin/pip')} install -r requirements.txt",
                ]
            ),
        )
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cd {remote_quote(env['remote_project'])}",
                    f"FLASK_APP={flask_app} {remote_quote(venv_path + '/bin/flask')} db upgrade",
                ]
            ),
        )

        service_name = env["service_name"]
        run_remote(
            ssh,
            " && ".join(
                [
                    f"cp {remote_quote(posixpath.join(env['remote_project'], service_name + '.service'))} /etc/systemd/system/{service_name}.service",
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
                    f"cp {remote_quote(posixpath.join(env['remote_project'], 'nginx_' + service_name + '.conf'))} /etc/nginx/sites-available/{service_name}",
                    f"ln -sfn /etc/nginx/sites-available/{service_name} /etc/nginx/sites-enabled/{service_name}",
                    "nginx -t",
                    "systemctl reload nginx",
                ]
            ),
            sudo_password=env["password"],
        )

        print(f"Deploy completado para versión {version}.")
    finally:
        ssh.close()


def main() -> int:
    try:
        deploy()
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
