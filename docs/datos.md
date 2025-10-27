# Datos y esquemas

## programas_viejos.json (histórico)

- Origen: archivos PDF hospedados en `archivo.crub.uncoma.edu.ar`.
- Estructura básica por item:
  - `ano_academico` (str)
  - `codigo_carrera` (str)
  - `nombre_materia` (str)
  - `url_programa` (str)
- Transformaciones al cargar en la app:
  - `id_programa`: `old-<n>` (índice + 1)
  - `cod_carrera`: copia de `codigo_carrera`
  - `origen`: `Archivo histórico`
  - `firma_dto` -> `firma_depto` si existiese

## carreras.json

- Estructura por item:
  - `plan_version_SIU` (str)
  - `carrera` (str) código (ej: "LBIB")
  - `nombre` (str) nombre completo
  - `ordenanzas_resoluciones` (str)
- Uso:
  - Mapear código -> nombre vía `get_career_name`.
  - Renderizar cards de carreras en `index.html`.

## planes_estudio.json

- Información de planes, no usada por endpoints actuales, pero útil para documentación de carreras/planes.
- Campos típicos: `plan_version_SIU`, `carrera`, `nombre`, `anio_entrada_vigencia`, `vigente`, `url_planEstudio`, etc.

## Respuesta típica de la API externa

- Campos comunes esperados por la app al normalizar:
  - `id` -> `id_programa`
  - `codigo_carrera` -> `cod_carrera`
  - `nombre_carrera` (si no viene, se deriva con `get_career_name`)
  - `ano_academico`, `ano_plan`, `nombre_materia`, `cod_guarani`, etc.

## Consideraciones de datos

- Años: se exponen ordenados desc; se combinan local+API.
- Filtrado por carrera: acepta tanto código (ICIB) como nombre exacto local.
- Campos opcionales: muchas claves pueden faltar en históricos; el código maneja ausencias.
