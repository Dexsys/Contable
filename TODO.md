# TODO - Mejoras de Seguridad y Robustez (Recetas)

## Control de respaldo
- Ultima revision prebackup: 2026-03-18


## Control de despliegue
- Ultima revision predeploy: 2026-03-18


## Objetivo de negocio
- Solo usuarios registrados y aprobados pueden ver Comprobantes como la contabilidad.
- Registro de usuarios requiere aprobacion de administrador, para lo cual cuando se registra se debe notificar al administrador (dexsys@gmail.com) enviando la identidad del solicitantes..
- Endurecer seguridad base para produccion.

## Fase 1 - Control de acceso (alta prioridad)
- [ ] Restringir vistas publicas de cantabilidad y sus datos:
  - Proteger la ruta principal y sugerencias con autenticacion.
  - Si el usuario no esta autenticado, redirigir a login.
  - Revisar rutas en `routes/main.py` para aplicar `login_required` donde corresponda.
- [ ] Restringir detalle de contabilidad a usuarios autenticados.
- [ ] Plan de cuentas solo la puedo modificar yo (dexsys@gmail.com u rol administrador).

## Fase 2 - Aprobacion de usuarios (alta prioridad)
- [ ] Agregar campo `is_active` (o `is_approved`) al modelo de usuario.
- [ ] Crear migracion Alembic para el nuevo campo y valor por defecto seguro (`False`).
- [ ] Ajustar registro en `routes/auth.py`:
  - Primer usuario del sistema: admin activo automaticamente.
  - Resto de usuarios: crear como inactivos/pendientes.
- [ ] Ajustar login:
  - Si usuario no esta aprobado, bloquear inicio de sesion y mostrar mensaje claro.
- [ ] Crear modulo admin para aprobacion/rechazo de usuarios pendientes.
- [ ] Agregar vista en dashboard admin con:
  - Pendientes de aprobacion.
  - Acciones Aprobar/Rechazar.

## Fase 3 - Seguridad de autenticacion (alta prioridad)
- [ ] Limite de intentos de login (rate limit) por IP/email.
- [ ] Bloqueo temporal tras multiples intentos fallidos.
- [ ] Endurecer cookies de sesion:
  - `SESSION_COOKIE_HTTPONLY=True`
  - `SESSION_COOKIE_SECURE=True` (produccion)
  - `SESSION_COOKIE_SAMESITE='Lax'` o `Strict`
- [ ] Tiempo de expiracion de sesion y politica de remember me.
- [ ] Agregar validacion de password fuerte en registro.

## Fase 4 - Seguridad de aplicacion (media prioridad)
- [ ] Revisar CSRF en todos los formularios y endpoints sensibles.
- [ ] Validar y sanear entradas de texto en comentarios y contenido libre.
- [ ] Validar subida de archivos:
  - Extensiones permitidas.
  - Tamano maximo.
  - Rechazar archivos ejecutables.
- [ ] Evitar exposicion de trazas internas en produccion (`debug=False`).
- [ ] Manejo de errores 403/404/500 con paginas amigables.

## Fase 5 - Seguridad operativa (media prioridad)
- [ ] Mover secretos a variables de entorno seguras.
- [ ] No guardar credenciales reales en archivos versionados.
- [ ] Agregar revision automatica de dependencias vulnerables.
- [ ] Politica de backups de BD + prueba de restauracion.

## Fase 6 - Auditoria y observabilidad (media prioridad)
- [ ] Registrar eventos de seguridad:
  - Intentos de login fallidos.
  - Aprobacion/rechazo de usuarios.
  - Cambios de rol.
- [ ] Logs con rotacion y retencion definida.
- [ ] Alertas basicas por errores criticos de autenticacion.

## Cambios tecnicos sugeridos (resumen)
- [ ] `apps/`: es la ruta principal de la apps. 
- [ ] `models.py`: nuevo campo de aprobacion de usuario.
- [ ] `routes/auth.py`: bloquear login de no aprobados + registro pendiente.
- [ ] `routes/admin.py`: aprobar/rechazar usuarios.
- [ ] `routes/main.py`: exigir autenticacion para ver recetas.
- [ ] `templates/`: mensajes de estado para usuarios pendientes.
- [ ] `migrations/`: revision Alembic para usuarios aprobados.

## Criterios de aceptacion
- [ ] Un usuario nuevo no puede iniciar sesion hasta ser aprobado.
- [ ] Un usuario no registrado no puede ver listado ni detalle de recetas.
- [ ] Admin puede aprobar/rechazar usuarios desde panel.
- [ ] Todo cambio de esquema se implementa via Alembic.
- [ ] Configuracion de seguridad minima aplicada en produccion.

## Orden recomendado de implementacion
1. Aprobacion de usuarios (modelo + migracion + login).
2. Restriccion de acceso a recetas para no autenticados.
3. Pantalla admin de aprobacion de usuarios.
4. Endurecimiento de sesiones/cookies y rate limit.
5. Auditoria de logs y pruebas de seguridad.
