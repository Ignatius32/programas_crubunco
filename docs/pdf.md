# Generación de PDFs de programas

La app soporta dos modos:

1) Programas históricos (id `old-*`): descarga directa
- Se toma `url_programa` y se hace streaming del PDF.
- Se compone el nombre de archivo como `<materia>_<cod_carrera>_<año>.pdf` y se sanitiza.

2) Programas actuales (API): render dinámico con ReportLab
- Se obtiene `/rest/programas/<id>` de `API_URL` con Digest Auth.
- Se normalizan campos (`id`->`id_programa`, `codigo_carrera`->`cod_carrera`, `firma_dto`->`firma_depto`).
- Se renderiza con:
  - `generate_program_pdf(programa)`: prepara documento A4 y metadata.
  - `programa_header_footer`: logo, encabezado institucional, firmas (doc/depto/SAC) y número de página.
  - `generate_program_content`: bloquea contenido por secciones (fundamentación, objetivos, contenidos, bibliografía, metodología, evaluación, distribución horaria, cronograma, correlativas, etc.).
  - `process_content`: soporta texto plano y HTML con tablas y listas; usa BeautifulSoup.
  - `process_html_table` / `process_complex_html_table`: manejo de colspan/rowspan, estilos básicos, fondos y negritas.

## Sanitización de nombres de archivo

- `sanitize_filename` aplica:
  - Normalización Unicode (via `normalize_text`).
  - Reemplazo de caracteres inválidos en filenames.
  - Limitación de longitud y colapso de guiones bajos.

## Normalización de contenido

- `unicode_utils.normalize_text`: reemplazos de caracteres problemáticos (Windows-1252, NBSP, guiones, comillas, etc.).
- `unicode_utils.decode_html_entities`: decodifica entidades HTML previas a render.

## Estilos y tipografía

- Fuentes: Helvetica/Helvetica-Bold.
- Títulos y campos con `ParagraphStyle` personalizados.
- Tablas con `Table`, `TableStyle`, ajuste de anchos mínimos y grid.
