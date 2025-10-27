# Arquitectura y flujo

## Componentes

- Flask app (`app/app.py`): rutas, carga de datos, búsqueda, endpoints, generación de PDFs.
- Utilidades Unicode (`app/unicode_utils.py`): normalización y decodificación consistente.
- WSGI (`app/wsgi.py`): arranque en producción, middleware de prefijo `/programas`, logging robusto a archivo.
- Plantillas (`app/templates/*.html`): UI con Bootstrap, render del lado servidor.
- Frontend JS (`app/static/js/search.js`): consumo de endpoints y render dinámico de resultados.
- Datos locales (`app/static/*.json`): carreras, planes, programas históricos.

## Flujo de arranque

1. `load_dotenv` carga variables de entorno (API_URL).
2. `before_first_request` llama `load_old_programs` y `load_carreras`.
3. Se exponen rutas UI y endpoints API.

## Carga y normalización de datos

- `load_old_programs()`
  - Lee `static/programas_viejos.json`.
  - Inserta `id_programa` como `old-<n>`.
  - Copia `codigo_carrera` -> `cod_carrera`.
  - Estandariza firmas (`firma_dto` -> `firma_depto` si existiera).
  - Marca `origen = "Archivo histórico"`.

- `load_carreras()`
  - Lee `static/carreras.json`.
  - Ordena alfabéticamente, dejando carreras que empiezan con "I" al final.

- API remota (opcional)
  - Se consulta si `API_URL` está definida.
  - Autenticación: HTTP Digest con usuario `usuario1` y password `pdf`.
  - Se normalizan campos: `id` -> `id_programa`, `codigo_carrera` -> `cod_carrera`, y se deriva `nombre_carrera` con `get_career_name`.
  - Marca `origen = "API actual"`.

## Endpoints y uso

- UI
  - `/` muestra Carreras y Búsqueda.
  - `/carrera/<codigo>` lista programas, filtra por `academic_year` (querystring).

- API
  - `/api/search_options`: combos iniciales.
  - `/api/search_programs`: filtros detallados + `query` libre.
  - `/api/programs_by_career_year`: por carrera y años.
  - `/api/available_years/<tipo>`: años por carrera, combinando local+API.
  - `/download/programa/<id>`: descarga directa (old-*) o PDF generado.

## Generación de PDFs

- `generate_program_pdf(programa)` y `generate_program_content(...)` construyen el documento.
- Cabecera y pie: `programa_header_footer` (logo, encabezado institucional, firmas, paginado).
- Contenido largo con HTML/tablas/listas: `process_content`, `process_html_table`, `process_complex_html_table`.
- Limpieza de texto: `normalize_text` y `decode_html_entities`.

## Middleware de prefijo

- `PrefixMiddleware` reescribe `PATH_INFO` cuando la app vive bajo `/programas`.
- Ajusta también `SCRIPT_NAME` y loguea request/response.

## Errores y consideraciones

- Timeouts de API: 5s y manejo por try/except, la app sigue funcionando con datos locales.
- Sanitización de nombres de archivo: `sanitize_filename` evita headers inválidos.
- Cache-control: `after_request` fuerza no-cache para contenido dinámico.
