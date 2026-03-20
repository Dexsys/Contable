# Sistema Contable Basico

Aplicación Flask con patrón factory, SQLAlchemy y migraciones Alembic para operación productiva con Gunicorn + systemd + Nginx.

## Estado

- Version: 1.2026.0320
- Ultima actualizacion: 2026-03-20
- URL: http://contable.dexsys.cl
- Repositorio: https://github.com/Dexsys/Contable.git

## Ultimos cambios

- Edición de movimientos con formulario modal (sin prompts por campo).
- Colores de saldos por signo: azul positivos y rojo negativos.
- Máscaras con separador de miles para campos numéricos en ingreso/edición.
- Cambio de usuario restringido a rol administrador.
- Cambio de contraseña para usuario autenticado.
- Diferenciación visual de ambiente (producción/desarrollo) y versión en barra de sesión.

## Arquitectura

- app.py: fábrica Flask (`create_app`) y registro de blueprints.
- extensions.py: inicialización compartida de SQLAlchemy y Flask-Migrate.
- models.py: modelos de datos.
- routes/: blueprints (`main`, `auth`, `admin`).
- migrations/: historial Alembic y revisión inicial.
- wsgi.py: punto de entrada para Gunicorn.
- gunicorn_config.py: configuración de workers y timeouts.

## Requisitos

- Python 3.11+
- pip actualizado
- Dependencias de requirements.txt

## Instalacion local

1. Crear entorno virtual:

   python -m venv .venv

2. Activar entorno virtual:

   .venv\Scripts\activate

3. Instalar dependencias:

   pip install -r requirements.txt

4. Configurar variables:

   Copiar y completar .env con credenciales reales.

## Ejecucion local

Con el entorno activo:

1. Aplicar esquema de base de datos:

   flask db upgrade

2. Iniciar aplicación:

   flask --app app:create_app run --port 5200

## Migraciones

- Esquema gestionado con Flask-Migrate/Alembic.
- Migración inicial: migrations/versions/20260318_0001_initial_schema.py
- Migración contable: migrations/versions/20260318_0002_accounts_and_ledger.py

Comandos habituales:

- flask db migrate -m "descripcion"
- flask db upgrade
- flask db downgrade -1

## Importacion desde Excel (plan + historico)

Fuente esperada:

- Hoja de plan de cuentas con columnas tipo: Cuenta, Descripcion Cuenta
- Hoja historica con columnas tipo: Fecha, Glosa, Cargo/Egreso, Abono/Ingreso, Cuenta

Comando recomendado:

- python import_excel_data.py --file "Contabilidad Simplificada.xlsx" --reset

Opciones:

- --plan-sheet "NombreHojaPlan"
- --ledger-sheet "NombreHojaHistorico"
- --only-plan
- --only-ledger

Resultado:

- Tabla accounts poblada con estructura jerarquica por codigo.
- Tabla ledger_entries poblada con movimientos historicos y trazabilidad de hoja/fila origen.

## API contable operativa

### Control de acceso por roles (RBAC)

Roles disponibles:

- `admin`: acceso total + administración de usuarios y cambio de roles.
- `tesorero`: acceso total + administración de usuarios y cambio de roles.
- `usuario`: solo reportes + registro de gastos/comprobantes.
- `visita`: solo reportes.

Regla fija de privilegios:

- `lcorales@colbun.cl` y `dexsys@gmail.com` mantienen acceso elevado para gestionar usuarios y roles.

Sesión y usuarios:

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`

Administración de usuarios (solo tesorero/admin):

- `GET /admin/users`
- `PATCH /admin/users/<id>/role`

### Flujo de comprobantes con aprobacion previa

- Un comprobante puede tener multiples lineas bajo un mismo ingreso (`/api/vouchers`).
- Estado inicial: `pending_approval`.
- Solo al aprobar (`/api/vouchers/<id>/approve`) se publican sus lineas en contabilidad (`ledger_entries`).
- Regla de aprobadores:
  - Si presenta `kazat@colbun.cl`, aprueba `lcorales@colbun.cl`.
  - Si presenta `lcorales@colbun.cl`, aprueba `kazat@colbun.cl`.
  - Si presenta otra persona, puede aprobar cualquiera de los dos.

Endpoints:

- `POST /api/vouchers`
- `GET /api/vouchers?status=pending_approval`
- `POST /api/vouchers/<id>/approve`
- `POST /api/vouchers/<id>/reject` (requiere motivo de rechazo)

Auditoria:

- `GET /admin/audit-logs` (solo admin/tesorero)


Flujo esperado:

- Cada comprobante nuevo (ingreso/egreso) debe registrarse en la API y queda reflejado en libro banco.
- Los reportes resumen usan jerarquia de codigo de cuenta (nivel 1, 2, 3... hasta el ultimo nivel).

Endpoints principales:

- POST /api/entries
   - Registra movimientos directos (ingreso, egreso, asiento general).
   - Campos recomendados: date, description, amount, kind, account_code.
   - Soporta multipart/form-data con archivo de respaldo en receipt_image.

- POST /api/term-deposits/open
   - Registra apertura de deposito a plazo y crea movimiento banco asociado.

- POST /api/term-deposits/<code>/rescue
   - Registra rescate de deposito a plazo y crea movimiento banco asociado.

- GET /api/term-deposits
   - Lista detalle de depositos a plazo.

- GET /api/reports/bank-summary
   - Entrega resumen jerarquico por plan de cuentas.
   - Filtros soportados: year, month, start_date, end_date.
- Opcion de menu Comprobantes con ingreso multi-linea y aprobacion.
- Filtros de resumen simplificados a Año y Mes.
   - include_entries=1 agrega detalle por cuenta para vista tipo acordeon.

## Interfaz web

Ruta principal:

- /

Incluye:

- KPI de ingresos, egresos, saldo y cantidad de movimientos.
- Filtros por año, mes y rango de fechas.
- Resumen jerarquico del plan de cuentas en formato acordeon.
- Formulario de registro de movimientos (ingreso/egreso).
- Formularios para apertura y rescate de depositos a plazo.
- Tabla de ultimos movimientos cargados.
- Visualizacion de respaldo por imagen adjunta en movimientos.

Archivos UI:

- templates/dashboard.html
- static/css/dashboard.css
- static/js/dashboard.js

Ejemplo de filtro mensual:

- GET /api/reports/bank-summary?year=2026&month=3

Ejemplo por rango:

- GET /api/reports/bank-summary?start_date=2026-01-01&end_date=2026-03-31

## Despliegue a servidor

Script principal:

- python deploy_to_server.py

El script realiza:

- Carga automática de .env
- Actualización previa de README.md e historial.md
- Copia de archivos versionados con git ls-files
- Creación/actualización de venv remoto
- Instalación de requirements en remoto
- Ejecución de flask db upgrade remoto
- Instalación del unit file en /etc/systemd/system/contable.service
- daemon-reload, enable, restart y validación de servicio
- Instalación/validación de sitio Nginx en sites-available/sites-enabled
- En primer despliegue, sincroniza base local (`instance/*.db`) y archivos de `uploads/`.

Objetivo actual de despliegue inicial:

- Servidor: `192.168.0.89`
- Ruta remota: `~/Developer/Flask/Contable`

Variables recomendadas en `.env` para este caso:

- `DEPLOY_SSH_HOST=192.168.0.89`
- `DEPLOY_REMOTE_PROJECT_PATH=~/Developer/Flask/Contable`
- `DEPLOY_FIRST_SYNC_DATA=1`

## Respaldo a GitHub

Script principal:

- python backup_to_github.py

El script realiza:

- Actualización previa de README.md e historial.md
- git add -A
- git commit
- git push origin main

Configuración inicial del remoto (primera vez):

- git init
- git branch -M main
- git remote add origin https://github.com/Dexsys/Contable.git

## Variables requeridas en .env

Mínimas:

- SECRET_KEY=
- DATABASE_URL=
- UPLOAD_FOLDER=
- FLASK_APP=app:create_app
- DEPLOY_SSH_HOST=
- DEPLOY_SSH_PORT=22
- DEPLOY_SSH_USER=
- DEPLOY_SSH_PASSWORD=
- DEPLOY_REMOTE_PROJECT_PATH=
- DEPLOY_PUBLIC_URL=
- DEPLOY_SERVICE_NAME=contable
- DEPLOY_PYTHON=python3
- DEPLOY_REMOTE_VENV=.venv

## Servicio systemd

Plantilla local:

- contable.service

Valores esperados:

- WorkingDirectory=/ruta/remota/proyecto
- Environment="PATH=/ruta/remota/proyecto/.venv/bin"
- ExecStart=/ruta/remota/proyecto/.venv/bin/gunicorn --config /ruta/remota/proyecto/gunicorn_config.py wsgi:app
- Restart=always
- WantedBy=multi-user.target

## Historial

- Ver historial de versiones en historial.md

