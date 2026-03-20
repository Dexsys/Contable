# Sistema Contable Basico - Historial de Versiones

**Aplicacion** : Sistema de Contabilidad Basico
**URL**        : http://contable.dexsys.cl
**Repositorio**: https://github.com/Dexsys/Contable

---

## [1.2026.0320] - 2026-03-20

### Agregado
- Cambio de contraseña para usuario autenticado (`POST /auth/change-password`).
- Cambio de usuario por impersonación solo para rol administrador (`POST /auth/switch-user`).
- Formulario visual de ingreso al sistema (modal de login).
- Etiqueta de versión y ambiente en la barra de sesión.

### Modificado
- Edición de movimientos en resumen migrada a formulario modal completo (sin diálogos por campo).
- Campos numéricos de ingreso y edición ahora usan máscara con separador de miles.
- Saldos destacados por signo: azul para positivos y rojo para negativos.
- Diferenciación visual del fondo por ambiente: celeste en productivo y verde agua en desarrollo.
- Script de deploy incorpora sincronización post-deploy desde servidor hacia entorno local de desarrollo (BD reemplazada y uploads sin sobreescritura).
- Nuevo modo manual de sincronización desde servidor sin deploy: `python deploy_to_server.py --sync-from-server-only`.
- Nuevo helper `sync_runtime_from_server.py` para ejecutar sincronización manual con comando directo.
- Deploy blindado para no sobrescribir producción con datos locales: por defecto no sube `instance/` ni `uploads/` al servidor.
- Variable `DEPLOY_FIRST_SYNC_DATA` marcada como deprecada para evitar inversiones de flujo de datos.
- Nueva variable explícita `DEPLOY_PUSH_RUNTIME_TO_SERVER` (por defecto `0`) para casos excepcionales de copia local->servidor.

## [1.2026.0319] - 2026-03-19

### Modificado
- Actualización de `TODO.md` con estado real del proyecto Contable.
- Priorización de pendientes para despliegue inicial en `192.168.0.89`.
- Checklist operativo para validación post-deploy (servicio, Nginx, URL y sincronización de datos).

## [1.2026.0319] - 2026-03-19

### Agregado
- Soporte de primer despliegue con sincronización de datos locales: `instance/*.db` y `uploads/`.
- Variable `DEPLOY_FIRST_SYNC_DATA` para controlar la sincronización inicial de datos.

### Modificado
- Script de deploy ahora resuelve correctamente rutas remotas con `~` (home del usuario), por ejemplo `~/Developer/Flask/Contable`.
- Ajustes de `.gitignore` para evitar respaldar archivos sensibles/locales (`env`, `*.env`, `*.local`, bases sqlite locales y uploads temporales).

### Infraestructura
- Preparación de despliegue para servidor `192.168.0.89` en ruta `~/Developer/Flask/Contable`.

## [1.2026.0319.1] - 2026-03-19
- Deploy a produccion ejecutado mediante deploy_to_server.py.
- Respaldo a GitHub ejecutado mediante backup_to_github.py.

### Agregado
- Flujo de rechazo de comprobantes con motivo obligatorio.
- Campos de rechazo en comprobantes: `rejected_by_email`, `rejected_at`, `rejection_reason`.
- Endpoint de rechazo: `POST /api/vouchers/<id>/reject`.
- Tabla de auditoría `audit_logs` con endpoint `GET /admin/audit-logs`.
- Panel web de log de auditoría para usuarios con permiso de administración.

### Modificado
- Dashboard recupera KPIs de ingresos y egresos del periodo.
- KPI superior ampliado a 6 indicadores: saldo anterior, ingresos, egresos, saldo del periodo, saldo acumulado final y número de movimientos.
- "Últimos movimientos" ahora respeta filtros de periodo (año/mes).
- Listado de comprobantes incluye motivo de rechazo cuando aplica.

### Migracion de Base de Datos
- Nueva migración `202603190008` para campos de rechazo en `vouchers` y creación de tabla `audit_logs`.

## [1.2026.0319] - 2026-03-19

### Agregado
- Control de acceso por roles (`admin`, `tesorero`, `usuario`, `visita`) en modelo de usuarios.
- Restricciones por permiso en endpoints de reportes, movimientos, depositos y comprobantes.
- Endpoints de sesión: login, logout y perfil actual (`/auth/login`, `/auth/logout`, `/auth/me`).
- Administración de usuarios y cambio de roles en `/admin/users` y `/admin/users/<id>/role`.
- Panel web de sesión (usuario/rol activo), cambio de usuario y cierre de sesión.
- Panel web de administración de usuarios habilitado solo para tesorero/administrador.

### Modificado
- Dashboard ahora oculta acciones según permisos del rol activo.
- Flujo de comprobantes limita a usuarios estándar a crear comprobantes propios.

### Migracion de Base de Datos
- Nueva migración 202603190006 para agregar columna `role` en `users` e índice asociado.
- Se asigna rol elevado inicial a `lcorales@colbun.cl` y `dexsys@gmail.com`.

## [1.2026.0318] - 2026-03-18

### Agregado
- Estructura Flask con patron factory en app.py y blueprints en routes/.
- Inicializacion de extensiones en extensions.py con SQLAlchemy + Flask-Migrate.
- Modelo base User en models.py.
- Configuracion Gunicorn en gunicorn_config.py.
- Unit file systemd contable.service.
- Configuracion de sitio Nginx nginx_contable.conf.
- Script de deploy productivo deploy_to_server.py.
- Script de respaldo a GitHub backup_to_github.py.
- Utilidad release_metadata.py para actualizar README e historial antes de backup/deploy.
- Estructura Alembic en migrations/ con revision inicial 202603180001.
- Archivos .env y .gitignore para configuracion y seguridad base.
- Modelo contable para plan de cuentas (accounts) y movimientos historicos (ledger_entries).
- Script import_excel_data.py para importar plan de cuentas e historico desde Excel.
- Endpoints API para registrar comprobantes en libro banco en linea.
- Endpoints API para apertura y rescate de depositos a plazo con trazabilidad.
- Reporte jerarquico por niveles de plan de cuentas con filtros por mes, año y rango de fechas.
- Interfaz web principal con dashboard contable y acordeon jerarquico.
- Formularios web para ingreso de movimientos y gestion de depositos a plazo.
- Endpoints auxiliares para listar cuentas y ultimos movimientos.
- Carga de imagen de respaldo en registro de movimientos contables.
- Endpoint de entrega de adjuntos en /uploads/<filename>.
- Flujo de comprobantes multi-linea con estado pendiente/aprobado.
- Regla de aprobacion por correo entre kazat@colbun.cl y lcorales@colbun.cl.
- Publicacion a contabilidad solo despues de aprobación.

### Corregido
- Se eliminaron secretos embebidos en config.py y env.

### Tecnico
- Se estandarizo versionado en formato 1.AAAA.MMDD.
- Se actualizo requirements.txt agregando paramiko y version fija de python-dotenv.
- Se agrego columna movement_type y bank_effective_date en ledger_entries.
- Se agrego tabla term_deposits para detalle operativo de inversiones y rescates.
- Se agrego columna receipt_image_path en ledger_entries para respaldos visuales.

### Modificado
- README.md actualizado con flujo de migraciones, backup y deploy productivo.
- wsgi.py mantenido como entrypoint para Gunicorn.

### Migracion de Base de Datos
- Migracion inicial creada para tabla users con indice en email.
- Migracion 202603180005 creada para tablas vouchers y voucher_lines.
- Migracion 202603180002 creada para tablas accounts y ledger_entries.
- Migracion 202603180003 creada para term_deposits y metadatos de movimiento en ledger_entries.
- Migracion 202603180004 creada para respaldo de imagen en ledger_entries.

### Eliminado
- Credenciales hardcodeadas en archivo env.

### Infraestructura
- Respaldo a GitHub ejecutado mediante backup_to_github.py.
- Deploy a produccion ejecutado mediante deploy_to_server.py.


