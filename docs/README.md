# Programas CRUB UNCo – Documentación

Bienvenido a la documentación del Buscador de Programas Académicos del CRUB (UNCo). Este proyecto es una aplicación Flask que permite:

- Explorar programas por carrera y año
- Buscar programas por materia/carrera/año
- Descargar programas en PDF desde un archivo histórico o generarlos dinámicamente desde una API

## Estructura general

- app/app.py: Aplicación Flask, rutas, lógica de negocio y generación de PDFs
- app/unicode_utils.py: Utilidades de Unicode para normalizar/decodificar contenido
- app/wsgi.py: Entrada WSGI para despliegues con prefijo (/programas) y logging
- app/templates/*.html: Vistas Jinja2 (index, carrera)
- app/static/js/search.js: Lógica de búsqueda y render del cliente
- app/static/*.json: Datos locales (carreras, planes, programas históricos)
- requirements.txt: Dependencias

## Cómo ejecutar en desarrollo

1) Crear entorno y paquetes

- Python 3.12+
- Instalar dependencias desde requirements.txt

2) Ejecutar el servidor

- FLASK_APP=app/app.py (o usar --app)
- flask run --port 5001

3) Variables de entorno

- API_URL: URL base de la API actual (opcional). Si está definida, la app combinará resultados locales con la API.

Más detalles en docs/guia_ejecucion.md.

## Rutas principales (UI)

- GET /: Página de inicio con pestañas de Carreras y Buscar.
- GET /carrera/<carrera_codigo>: Lista programas de la carrera por año.

## Endpoints (API interna)

- GET /api/search_options: Opciones para combos (carreras, años académicos).
- GET /api/search_programs: Busca programas por nombre_materia, nombre_carrera (código o nombre), ano_academico, query.
- GET /api/programs_by_career_year: Filtra por carrera y (opcional) academic_year y plan_year.
- GET /api/available_years/<academico|cursada>?carrera=...: Años disponibles por carrera.
- GET /download/programa/<id_programa>: Descarga un PDF (histórico directo o generado desde API).

Ver docs/endpoints.md para parámetros, ejemplos y respuestas.

## Datos y esquemas

- Historico: app/static/programas_viejos.json
  - Campos: ano_academico, codigo_carrera, nombre_materia, url_programa
  - La app estandariza a: id_programa, cod_carrera, nombre_carrera, origen
- Carreras: app/static/carreras.json
  - Campos: carrera (código), nombre, plan_version_SIU, ordenanzas_resoluciones
- Planes: app/static/planes_estudio.json

Ver docs/datos.md para detalles de transformación y mapeos.

## Generación de PDF

- Ruta: /download/programa/<id>
- Históricos (old-*): descarga directa desde url_programa
- API actual: obtiene JSON, normaliza campos (ej. firma_dto -> firma_depto), renderiza PDF con ReportLab
- Normalización de contenido: unicode_utils.normalize_text + decode_html_entities
- Soporte de contenido HTML/tablas/listas en secciones largas

Detalles en docs/pdf.md.

## Arquitectura y flujo

- Capa de datos: JSON locales + API remota (opcional)
- Capa de servicio: filtros y normalización (app.py)
- Capa de presentación: Jinja2 + Bootstrap + JS
- Despliegue: app/wsgi.py con middleware de prefijo (/programas) y logging a archivo

Ver docs/arquitectura.md para diagrama y responsabilidades.

## Preguntas frecuentes

- ¿Necesito API_URL? No, la app funciona en modo solo-local con los JSON. Con API_URL agrega resultados "API actual".
- ¿Cómo se arma el nombre del archivo PDF? Ver docs/pdf.md (sanitización, códigos, año).
- ¿Por qué aparecen años duplicados? La app mergea años de local y API.

---

Para contribuir o reportar issues, abrir PRs o issues en este repo.
