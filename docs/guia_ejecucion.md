# Guía de ejecución y despliegue

## Requisitos

- Python 3.12+
- Paquetes en `requirements.txt`

## Desarrollo local

1. Crear y activar un entorno virtual
2. Instalar dependencias
3. Ejecutar:
   - `flask --app app/app.py run --port 5001`
4. Abrir `http://127.0.0.1:5001/`

Variables opcionales:
- `API_URL=https://<host-api>` para combinar resultados locales con la API.

## Producción (WSGI)

- Punto de entrada: `app/wsgi.py`
- Middleware de prefijo: sirve bajo `/programas` si el servidor (Nginx/Apache) lo publica ahí.
- Logging: intenta `/var/www/programas/logs/programas.log`, luego `/tmp/programas.log` y por último `./programas.log`.

### Notas

- Configurar variable de entorno `API_URL` en el entorno del servicio.
- El middleware reescribe `PATH_INFO` y `SCRIPT_NAME` para que los enlaces funcionen bajo prefijo.
- La app impone headers de no-cache en contenido dinámico.
