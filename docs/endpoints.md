# Endpoints de la aplicación

Base: `http(s)://<host>[:puerto]` (en producción puede estar bajo `/programas`).

## UI

- GET `/`
  - Renderiza `index.html` con lista de carreras y pestaña de búsqueda.
- GET `/carrera/<carrera>`
  - Renderiza `carrera.html`.
  - Querystring opcional: `academic_year=<YYYY>`.

## API JSON

- GET `/api/search_options`
  - Respuesta:
    - `careers`: [{ code, name }]
    - `academic_years`: ["2024", "2023", ...]

- GET `/api/search_programs`
  - Parámetros:
    - `nombre_materia` (str, opcional)
    - `nombre_carrera` (str, opcional; acepta código o parte del nombre)
    - `ano_academico` (str, opcional)
    - `query` (str, opcional; busca en varios campos)
  - Respuesta: lista de programas combinando local y API, con campos típicos:
    - `id_programa` (str)
    - `cod_carrera` (str)
    - `nombre_carrera` (str)
    - `nombre_materia` (str)
    - `ano_academico` (str)
    - `ano_plan` (str|num, si lo provee la API)
    - `origen` ("Archivo histórico" | "API actual")

- GET `/api/programs_by_career_year`
  - Parámetros:
    - `carrera` (str, requerido; puede ser código o nombre exacto local)
    - `plan_year` (str, opcional)
    - `academic_year` (str, opcional)
  - Respuesta: lista de programas con mismo formato que arriba.

- GET `/api/available_years/<year_type>`
  - `year_type`: `academico` o `cursada` (usa `ano_academico` o `ano_plan`).
  - Query:
    - `carrera` (str, requerido)
  - Respuesta: ["2024", "2023", ...] ordenado desc.

- GET `/download/programa/<program_id>`
  - Si `program_id` empieza con `old-`: descarga el PDF desde `url_programa`.
  - Si no: consulta la API `/rest/programas/<id>`, normaliza campos y genera un PDF.
  - Nombre del archivo: `<NOMBRE_MATERIA>_<COD_CARRERA>_<AÑO>.pdf` con sanitización.

## Códigos de error

- 400: parámetros inválidos o faltantes (por ejemplo, `carrera` requerido).
- 404: recurso no encontrado (programa inexistente).
- 500: errores internos o API no configurada al intentar generar PDF con datos de API.

## Autenticación hacia API externa

- Digest Auth: usuario `usuario1`, password `pdf`.
- Timeout: 5 segundos.
