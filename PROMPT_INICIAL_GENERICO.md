# Prompt Maestro: Deploy Inicial Flask + SQLAlchemy + Alembic

Usa este prompt para pedirle a un agente que prepare un sistema Flask genericamente, con base de datos gestionada por migraciones, servicio systemd, y flujo de respaldo/deploy productivo.

---

Actua como un ingeniero DevOps + Backend Senior. Tu objetivo es dejar un proyecto Flask listo para produccion y mantenible.

## Contexto del proyecto

- Nombre de la app: {{APP_NAME}}
- Ruta local del proyecto: {{LOCAL_PROJECT_PATH}}
- Ruta remota en servidor: {{REMOTE_PROJECT_PATH}}
- Usuario SSH: {{SSH_USER}}
- Host SSH: {{SSH_HOST}}
- Puerto SSH: {{SSH_PORT}}
- Nombre de servicio systemd: {{SERVICE_NAME}} (por ejemplo: contable)
- Dominio publico: {{PUBLIC_URL}}
- Version inicial: {{INITIAL_VERSION}} (ejemplo: 1.2026.0317)

## Objetivos obligatorios

1. Estructurar una app Flask en patron factory (`create_app`) con Blueprints.
2. Integrar SQLAlchemy y Flask-Migrate (Alembic) para control de esquema.
3. Eliminar dependencias de `db.create_all()` para produccion.
4. Crear migracion inicial funcional para una base vacia.
5. Configurar `wsgi.py` y `gunicorn_config.py`.
6. Crear servicio systemd dinamico usando el nombre de app/servicio.
7. Crear `.env` con variables necesarias (sin hardcodear secretos en codigo).
8. Crear/actualizar `README.md` y `historial.md`.
9. Crear script de respaldo a GitHub y script de deploy a servidor.
10. En deploy, antes de copiar/reiniciar:
- actualizar `historial.md` y `README.md`;
- instalar/actualizar el servicio systemd en `/etc/systemd/system`;
- hacer `daemon-reload`, `enable` y `restart`.
11. Configurar Nginx del sitio:
- crear archivo de sitio Nginx para el dominio de la app;
- copiar a `/etc/nginx/sites-available/<app>`;
- crear enlace en `/etc/nginx/sites-enabled/<app>`;
- validar con `nginx -t` y recargar Nginx.

## Entregables minimos

Genera o actualiza estos archivos:

- `app.py` (factory Flask)
- `extensions.py`
- `models.py`
- `routes/*`
- `migrations/*` (init + primera revision)
- `wsgi.py`
- `gunicorn_config.py`
- `requirements.txt`
- `.env`
- `.gitignore`
- `README.md`
- `historial.md`
- `{{SERVICE_NAME}}.service`
- `deploy_to_server.py`
- `backup_to_github.py`

## Reglas de implementacion

1. No usar secretos hardcodeados en codigo Python.
2. Si necesitas password SSH, leer desde `.env` (`DEPLOY_SSH_PASSWORD`).
3. El deploy debe:
- cargar `.env` automaticamente;
- copiar archivos versionados por Git (`git ls-files`);
- crear venv remoto (`python3 -m venv .venv`);
- instalar requirements en venv remoto;
- ejecutar `flask db upgrade` remoto;
- instalar el unit file en `/etc/systemd/system/{{SERVICE_NAME}}.service`;
- `systemctl daemon-reload`;
- `systemctl enable {{SERVICE_NAME}}`;
- `systemctl restart {{SERVICE_NAME}}`;
- validar `systemctl is-active {{SERVICE_NAME}}`;
- instalar y validar Nginx (`sites-available`, `sites-enabled`, `nginx -t`, `systemctl reload nginx`).
4. El respaldo GitHub debe:
- actualizar `README.md` y `historial.md` antes del commit;
- hacer `git add`, `git commit`, `git push origin main`.
5. Mantener versionado con formato `1.AAAA.MMDD`.

## Contenido esperado de .env

Incluye al menos:

- `SECRET_KEY=`
- `DATABASE_URL=`
- `UPLOAD_FOLDER=`
- `FLASK_APP=app:create_app`
- `DEPLOY_SSH_PASSWORD=`
- `DEPLOY_SERVICE_NAME={{SERVICE_NAME}}`
- `DEPLOY_PYTHON=python3`
- `DEPLOY_REMOTE_VENV=.venv`

## Contenido esperado de requirements.txt

Debe incluir al menos:

- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Alembic
- Gunicorn
- (otros segun modelos/forms)

## Contenido esperado del service file

Crear `{{SERVICE_NAME}}.service` con:

- `WorkingDirectory={{REMOTE_PROJECT_PATH}}`
- `Environment="PATH={{REMOTE_PROJECT_PATH}}/.venv/bin"`
- `ExecStart={{REMOTE_PROJECT_PATH}}/.venv/bin/gunicorn --config {{REMOTE_PROJECT_PATH}}/gunicorn_config.py wsgi:app`
- `Restart=always`
- `WantedBy=multi-user.target`

## Checklist de validacion final

Ejecuta y reporta resultados:

1. `python -m py_compile` en scripts clave.
2. `flask db upgrade` local OK.
3. Respaldo GitHub OK (`origin/main` actualizado).
4. Deploy remoto OK.
5. `systemctl is-active {{SERVICE_NAME}}` devuelve `active`.
6. URL publica responde.

## Formato de salida que debes entregar

1. Resumen ejecutivo (3-8 lineas).
2. Lista de archivos creados/modificados.
3. Comandos ejecutados importantes.
4. Resultados de validacion.
5. Riesgos pendientes y siguientes pasos.

Si detectas bloqueos, propon solucion concreta y continua hasta dejar el sistema operativo.
