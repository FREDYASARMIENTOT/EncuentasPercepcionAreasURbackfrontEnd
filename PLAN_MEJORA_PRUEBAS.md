Plan de mejora y corrección para la prueba integrada del portal

Objetivo:
- Asegurar que la prueba integrada valida correctamente el flujo: lectura DB -> generación Excel -> subida a SharePoint/Azure -> envío de correo final.

Pasos propuestos (prioridad alta -> baja):

1) Aislar la capa de envío de correos
   - Crear un adaptador `backend/mail_sender.py` con una interfaz `send_email(to, subject, body, attachments)`.
   - Refactorizar las partes del código que usan `smtplib` (o los scripts legacy) para invocar el adaptador.
   - Implementar una versión `DummyMailSender` para tests que registra llamadas en memoria.

2) Aislar la capa de subida a SharePoint/Azure
   - Exponer una interfaz `storage.upload_file(local_path, target_path)` y `storage.read_log(subfolder, file_name)`.
   - Implementar `AzureBlobStorage` que delegue a `azure_blob_logger.AzureBlobManager`.
   - En tests usar un `FakeStorage` que finge subida y lectura.

3) Mejorar los tests existentes
   - Reescribir tests para usar `monkeypatch` y reemplazar los adaptadores por fakes.
   - Añadir aserciones explícitas sobre llamadas al mail sender y storage (ej. `assert mail_sender.called_with(...)`).
   - Evitar dependencias a .env con credenciales reales; usar variables de entorno de CI/CD o fixtures.

4) Añadir script de espera para pruebas end-to-end locales
   - Crear `scripts/wait_for_backend.sh|ps1` que haga poll al endpoint `/api/health` hasta que responda 200.
   - Configurar la task `Run Portal Smoke Test` para ejecutar el wait script antes de pytest.

5) Integración en CI
   - Añadir job en GitHub Actions que ejecute los tests con mocks (no envía correos reales ni accede a Azure).
   - Para validar integración real, crear job opcional que use secretos seguros y se ejecute manualmente en entorno controlado.

6) Revisión y limpieza
   - Documentar en README.md cómo ejecutar los tests locales (conda envs, variables .env de ejemplo).
   - Añadir ejemplos de fixtures para inyectar `FakeStorage` y `DummyMailSender`.

Tareas abiertas:
- Implementar adaptadores `mail_sender.py` y `storage.py`.
- Refactorizar puntos de envío de correo en el código legacy o en orquestador para usar adaptador.
- Implementar fixtures y mejorar aserciones en tests.

Notas técnicas:
- Mantener `ARCHIVOS_NO_DESPLIEGUE` fuera del commit público si contienen credenciales o scripts con secretos.
- Los tests agregados usan mocking de `backend.scheduler.run_command` y `azure_blob_logger.AzureBlobManager.read_log`. Esto es suficiente para CI que no tenga acceso a Azure ni a SMTP.

Próximos pasos propuestos:
- ¿Autorizas que implemente `backend/mail_sender.py` y `backend/storage.py` y refactorice las llamadas a `smtplib` y `azure_blob_logger` en el código para depender de esos adaptadores? Con eso los tests podrán hacer aserciones explícitas sobre llamadas y evitamos enviar correos reales.
