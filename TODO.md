# TODO - Proyecto Contable

## Control de respaldo
- Ultima revision prebackup: 2026-03-19

## Control de despliegue
- Ultima revision predeploy: 2026-03-19
- Objetivo remoto: 192.168.0.89:~/Developer/Flask/Contable

## Estado actual (completado)
- [x] Flujo de comprobantes con aprobación y rechazo con motivo.
- [x] KPIs de cabecera restaurados (incluye ingresos y egresos del periodo).
- [x] Filtro de "Ultimos movimientos" por año/mes.
- [x] Auditoría base implementada (`audit_logs`, login/logout, movimientos, comprobantes, cambio de rol).
- [x] Endpoint admin de auditoría (`/admin/audit-logs`).
- [x] Migración `202603190008` creada y aplicada localmente.
- [x] Respaldo a GitHub en `origin/main`.
- [x] `.gitignore` ajustado para evitar subir sensibles/locales.

## Alta prioridad (pendiente inmediato)
- [ ] Completar `DEPLOY_SSH_PASSWORD` en `.env` (actualmente vacío).
- [ ] Ejecutar deploy inicial con `python deploy_to_server.py`.
- [ ] Validar en servidor:
  - [ ] `systemctl is-active contable` = `active`
  - [ ] `nginx -t` sin errores
  - [ ] aplicación respondiendo en la URL pública
- [ ] Verificar copia inicial de datos:
  - [ ] Base local en `instance/*.db` sincronizada al servidor
  - [ ] Archivos de `uploads/` sincronizados al servidor

## Seguridad y robustez (siguiente fase)
- [ ] Aplicar rate limit a login por IP/email.
- [ ] Bloqueo temporal por intentos fallidos.
- [ ] Endurecer cookies de sesión en producción (`HTTPONLY`, `SECURE`, `SAMESITE`).
- [ ] Revisar CSRF en formularios sensibles.
- [ ] Definir rotación y retención de logs de auditoría.
- [ ] Revisar notificación de eventos críticos (fallos de login, cambios de rol).

## Datos y operaciones
- [ ] Definir política de backup automático de BD en servidor.
- [ ] Agregar prueba de restauración de backup (al menos mensual).
- [ ] Documentar procedimiento de rollback rápido ante fallo de deploy.

## Criterios de cierre de esta iteración
- [ ] Deploy inicial completado en `192.168.0.89`.
- [ ] Servicio `contable` activo y persistente tras reinicio.
- [ ] Sitio operativo por Nginx.
- [ ] Datos históricos y uploads disponibles en producción.
