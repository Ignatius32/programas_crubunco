# Buscador de Programas Académicos

Esta aplicación web permite buscar, consultar y descargar programas académicos del Centro Regional Universitario Bariloche (Universidad Nacional del Comahue).

## Descripción

El Buscador de Programas Académicos es una herramienta diseñada para facilitar el acceso a los programas de cátedra de las diferentes carreras ofrecidas por el Centro Regional Universitario Bariloche (CRUB). Permite a estudiantes, docentes y personal administrativo buscar programas por carrera, materia y año académico, y descargarlos en formato PDF.

## Características principales

- **Exploración por carreras**: Acceso directo a programas organizados por carrera
- **Búsqueda avanzada**: Filtrado por nombre de materia, carrera y año académico
- **Generación de PDFs**: Visualización y descarga de programas en formato PDF
- **Interfaz responsiva**: Diseño adaptable para dispositivos móviles y de escritorio

## Requisitos previos

- Python 3.7 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar este repositorio:
   ```
   git clone [URL del repositorio]
   cd programas_crubunco
   ```

2. Crear y activar un entorno virtual (recomendado):
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Configurar las variables de entorno:
   - Crear un archivo `.env` en la raíz del proyecto
   - Definir la URL de la API (si es necesario):
     ```
     API_URL=http://url-de-api
     ```

## Ejecución

### Para desarrollo

```
flask run --debug
```
O alternativamente:
```
python app/app.py
```

### Para producción

Se recomienda usar un servidor WSGI como Gunicorn:

```
gunicorn app.wsgi:application
```

## Despliegue con Docker

### Usando la imagen precompilada

```bash
# Descargar y ejecutar la última versión de la imagen
docker pull ghcr.io/Ignatius32/programas_crubunco:latest
docker run -d \
  -p 8000:8000 \
  -v /path/to/logs:/var/www/programas/logs \
  -e API_URL=your_api_url \
  ghcr.io/Ignatius32/programas_crubunco:latest
```

### Construcción local

1. Construir la imagen:
   ```bash
   docker build -t programas_crubunco .
   ```

2. Ejecutar el contenedor:
   ```bash
   docker run -d \
     -p 8000:8000 \
     -v /path/to/logs:/var/www/programas/logs \
     -e API_URL=your_api_url \
     programas_crubunco
   ```

### Variables de entorno

- `API_URL`: URL de la API externa (si es necesaria)
- `FLASK_ENV`: Entorno de Flask (por defecto: production)

### Volúmenes recomendados

- `/var/www/programas/logs`: Logs de la aplicación
- `/app/app/static`: Archivos estáticos (opcional)

La aplicación estará disponible en http://localhost:8000

## Estructura del proyecto

```
programas_crubunco/
├── requirements.txt       # Dependencias del proyecto
├── app/                   # Directorio principal de la aplicación
│   ├── app.py             # Aplicación Flask principal
│   ├── unicode_utils.py   # Utilidades para manejo de caracteres Unicode
│   ├── wsgi.py            # Punto de entrada para servidores WSGI
│   ├── static/            # Archivos estáticos
│   │   ├── carreras.json  # Datos de las carreras
│   │   ├── planes_estudio.json  # Datos de planes de estudio
│   │   ├── programas_viejos.json  # Datos históricos de programas
│   │   ├── css/           # Hojas de estilo
│   │   ├── img/           # Imágenes
│   │   └── js/            # Scripts JavaScript
│   └── templates/         # Plantillas HTML
│       ├── carrera.html   # Página de programas por carrera
│       └── index.html     # Página principal
```

## Funcionalidades

### Página principal (index.html)
- Vista de carreras disponibles
- Formulario de búsqueda de programas

### Página de carrera (carrera.html)
- Listado de programas para una carrera específica
- Filtrado por año académico

### Generación de PDFs
La aplicación genera PDFs estandarizados para cada programa académico, que incluyen:
- Información básica del programa (nombre, código, año académico)
- Contenido del programa (fundamentación, objetivos, contenidos mínimos, etc.)
- Bibliografía y metodología
- Evaluación y acreditación
- Distribución horaria y cronograma tentativo

## Contribuciones

Si desea contribuir a este proyecto, por favor:
1. Haga un fork del repositorio
2. Cree una rama para su funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Confirme sus cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Suba la rama (`git push origin feature/nueva-funcionalidad`)
5. Cree un Pull Request

## Licencia

#TODO

## Contacto

Para dudas o sugerencias relacionadas con el buscador de programas, contacte con la [Secretaría Académica del CRUB](mailto:secretaria.academica@crub.uncoma.edu.ar).