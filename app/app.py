from flask import Flask, render_template, request, send_file, jsonify, make_response
import json
import os
import requests
from io import BytesIO
from datetime import datetime
import tempfile
# Import PDF generation libraries
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListItem, ListFlowable
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from bs4 import BeautifulSoup
from dotenv import load_dotenv
# Import utility modules
from unicode_utils import normalize_text, UNICODE_REPLACEMENTS, decode_html_entities
from pdf_utils import generate_program_pdf
from data_utils import load_old_programs, load_carreras, get_career_name, get_unique_careers
from data_utils import get_unique_years, get_unique_years_by_type, init_data, standardize_program_format
import re
from html import unescape

def sanitize_filename(filename):
    """Sanitize filename for use in HTTP Content-Disposition header"""
    if not filename:
        return "programa"
    
    # Normalize Unicode characters
    filename = normalize_text(filename)
    
    # Replace problematic characters
    # Remove or replace characters that cause issues in filenames
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)  # Remove invalid filename chars
    filename = re.sub(r'[,;]', '_', filename)  # Replace commas and semicolons with underscores
    filename = re.sub(r'\s+', '_', filename)  # Replace spaces with underscores
    filename = re.sub(r'[áàäâ]', 'a', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[éèëê]', 'e', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[íìïî]', 'i', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[óòöô]', 'o', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[úùüû]', 'u', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[ñ]', 'n', filename, flags=re.IGNORECASE)
    filename = re.sub(r'[ç]', 'c', filename, flags=re.IGNORECASE)
    
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    # Ensure filename is not empty and not too long
    if not filename:
        filename = "programa"
    elif len(filename) > 100:  # Limit filename length
        filename = filename[:100]
    
    return filename

load_dotenv()  # Load environment variables

app = Flask(__name__)
app.config['API_URL'] = os.environ.get('API_URL', '')  # API URL from environment variables

# Load data at startup
OLD_PROGRAMS = []
CARRERAS = []

@app.before_first_request
def load_data():
    global OLD_PROGRAMS, CARRERAS
    OLD_PROGRAMS, CARRERAS = init_data(app)

@app.after_request
def add_header(response):
    """Add headers to prevent caching for dynamic content"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Home Page Route
@app.route('/')
def index():
    """Home page with career listing"""
    # Pass all careers from carreras.json to template
    resp = make_response(render_template('index.html', careers=CARRERAS, now=datetime.now()))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

# Career Programs Route
@app.route('/carrera/<carrera_nombre>')
def carrera_programs(carrera_nombre):
    """Show programs for a specific career"""
    # Get career name from carreras.json
    career_name = get_career_name(carrera_nombre, CARRERAS)
    
    # Get unique years from local programs for this career
    filtered_programs = [p for p in OLD_PROGRAMS if p.get('nombre_carrera') == carrera_nombre 
                        or p.get('cod_carrera') == carrera_nombre]
    years = get_unique_years(filtered_programs)
    
    # Get selected year from query parameter or default to most recent
    selected_year = request.args.get('year', years[0] if years else None)
    
    return render_template('carrera.html', 
                         carrera=carrera_nombre,
                         career_name=career_name,
                         years=years, 
                         selected_year=selected_year,
                         now=datetime.now())

# Search Programs API Route
@app.route('/api/search_programs')
def search_programs():
    """API endpoint to search programs"""
    nombre_materia = request.args.get('nombre_materia', '').strip()
    nombre_carrera = request.args.get('nombre_carrera', '').strip()
    ano_academico = request.args.get('ano_academico', '').strip()
    query = request.args.get('query', '').strip()
    
    results = []
    
    # Search in local old programs first
    for program in OLD_PROGRAMS:
        # Check if the program matches the search criteria
        matches = True
        
        if nombre_materia and nombre_materia.lower() not in program.get('nombre_materia', '').lower():
            matches = False
        
        carrera = program.get('nombre_carrera', '') or program.get('cod_carrera', '')
        if nombre_carrera:
            # Try to match either the code or the full name
            matches_career = False
            for career in CARRERAS:
                if (nombre_carrera.lower() in career['carrera'].lower() or 
                    nombre_carrera.lower() in career['nombre'].lower()):
                    if (career['carrera'] == program.get('cod_carrera', '') or 
                        career['nombre'] == program.get('nombre_carrera', '')):
                        matches_career = True
                        break
            if not matches_career:
                matches = False
        
        if ano_academico and ano_academico != program.get('ano_academico', '').strip():
            matches = False
            
        if query:
            query_lower = query.lower()
            career_name = get_career_name(program.get('cod_carrera', ''), CARRERAS)
            searchable_fields = [
                program.get('nombre_materia', ''),
                program.get('cod_carrera', ''),
                career_name,
                str(program.get('ano_academico', ''))
            ]
            if not any(query_lower in str(field).lower() for field in searchable_fields):
                matches = False
        
        if matches:
            results.append(program)
    
    # Try to search in API if configured
    api_url = app.config.get('API_URL')
    if api_url:
        try:
            # Build query parameters
            params = {}
            if nombre_materia:
                params['nombre_materia'] = nombre_materia
            if nombre_carrera:
                params['cod_carrera'] = nombre_carrera  # API uses cod_carrera
            if ano_academico:
                params['ano_academico'] = ano_academico
            if query:
                params['query'] = query
                
            # Make API request with timeout
            auth = requests.auth.HTTPDigestAuth('usuario1', 'pdf')
            response = requests.get(f"{api_url}/rest/programas", params=params, auth=auth, timeout=5)
            
            if response.status_code == 200:
                api_results = response.json()
                # Standardize format before adding to results
                for program in api_results:
                    standardize_program_format(program, CARRERAS)
                    program['origen'] = 'API actual'  # Add origin field
                results.extend(api_results)
        except Exception as e:
            print(f"API search error: {str(e)}")
    
    # Sort results by materia name and year
    results.sort(key=lambda x: (x.get('nombre_materia', ''), x.get('ano_academico', '')))
    
    return jsonify(results)

# Programs by Career and Year API Route
@app.route('/api/programs_by_career_year')
def programs_by_career_year():
    """Get programs filtered by career and year"""
    carrera = request.args.get('carrera', '').strip()
    plan_year = request.args.get('plan_year', '').strip()
    academic_year = request.args.get('academic_year', '').strip()
    
    if not carrera:
        return jsonify({"error": "Carrera parameter is required"}), 400
        
    results = []
    
    # First, search local programs
    for program in OLD_PROGRAMS:
        matches_carrera = (program.get('nombre_carrera', '') == carrera or 
                          program.get('cod_carrera', '') == carrera)
        
        matches_plan_year = True
        matches_academic_year = True
        
        if plan_year:
            matches_plan_year = (str(program.get('ano_plan', '')) == plan_year)
        if academic_year:
            matches_academic_year = (str(program.get('ano_academico', '')) == academic_year)
            
        if matches_carrera and matches_plan_year and matches_academic_year:
            results.append(program)
    
    # Then search in API if configured
    api_url = app.config.get('API_URL')
    if api_url:
        try:
            params = {'cod_carrera': carrera}
            if academic_year:
                params['ano_academico'] = academic_year
            # Note: API doesn't support ano_plan filtering, so we'll filter results
                
            auth = requests.auth.HTTPDigestAuth('usuario1', 'pdf')
            response = requests.get(f"{api_url}/rest/programas", params=params, auth=auth, timeout=5)
            
            if response.status_code == 200:
                api_results = response.json()
                # Filter by ano_plan if needed
                if plan_year:
                    api_results = [p for p in api_results if str(p.get('ano_plan', '')) == plan_year]
                
                # Standardize format and add origin
                for program in api_results:
                    standardize_program_format(program, CARRERAS)
                    program['origen'] = 'API actual'  # Add origin field
                results.extend(api_results)
        except Exception as e:
            print(f"API search error: {str(e)}")
    
    # Sort results by materia name and year
    results.sort(key=lambda x: (x.get('nombre_materia', ''), x.get('ano_academico', ''), x.get('ano_plan', '')))
    
    return jsonify(results)

# Available Years API Route
@app.route('/api/available_years/<year_type>')
def available_years(year_type):
    """Get available years for a career based on type (academico/cursada)"""
    if year_type not in ['academico', 'cursada']:
        return jsonify({"error": "Invalid year type"}), 400
        
    carrera = request.args.get('carrera', '').strip()
    if not carrera:
        return jsonify({"error": "Carrera parameter is required"}), 400
    
    years = set()
    
    # Get years from local programs
    local_years = get_unique_years_by_type(OLD_PROGRAMS, year_type, carrera)
    years.update(local_years)
    
    # Get years from API
    api_url = app.config.get('API_URL')
    if api_url:
        try:
            params = {'cod_carrera': carrera}
            auth = requests.auth.HTTPDigestAuth('usuario1', 'pdf')
            response = requests.get(f"{api_url}/rest/programas", params=params, auth=auth, timeout=5)
            
            if response.status_code == 200:
                api_programs = response.json()
                api_years = get_unique_years_by_type(api_programs, year_type, carrera)
                years.update(api_years)
        except Exception as e:
            print(f"API search error: {str(e)}")
    
    return jsonify(sorted(list(years), reverse=True))

# Download Program PDF Route
@app.route('/download/programa/<program_id>')
def download_programa(program_id):
    """Download a program PDF"""
    # Handle old programs (direct PDF download)
    if program_id.startswith('old-'):
        try:
            index = int(program_id.split('-')[1]) - 1
            if 0 <= index < len(OLD_PROGRAMS):
                program = OLD_PROGRAMS[index]
                url = program.get('url_programa')
                if url:
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        buffer = BytesIO(response.content)                        # Add codigo carrera to the filename if it exists
                        cod_carrera = program.get('cod_carrera', '')
                        codigo_str = f"_{cod_carrera}" if cod_carrera else ""
                        
                        # Sanitize filename to prevent HTTP header issues
                        base_filename = f"{program.get('nombre_materia', 'programa')}{codigo_str}_{program.get('ano_academico', '')}"
                        safe_filename = sanitize_filename(base_filename) + ".pdf"
                        
                        return send_file(
                            buffer,
                            download_name=safe_filename,
                            as_attachment=True,
                            mimetype='application/pdf'
                        )
                    else:
                        return f"Error descargando el programa: HTTP {response.status_code}", 500
                else:
                    return "Este programa no tiene URL asociada", 404
            else:
                return "Programa no encontrado", 404
        except Exception as e:
            return f"Error: {str(e)}", 500
    
    # Handle API programs (dynamically generated PDF)
    try:
        # Get program data from API
        api_url = app.config.get('API_URL')
        if not api_url:
            return "API no configurada", 500
            
        url = f"{api_url}/rest/programas/{program_id}"
        auth = requests.auth.HTTPDigestAuth('usuario1', 'pdf')
        response = requests.get(url, auth=auth, timeout=5)
        
        if response.status_code != 200:
            return f"Programa no encontrado: HTTP {response.status_code}", 404
            
        program = response.json()
        
        # Standardize program format
        standardize_program_format(program, CARRERAS)
        
        # Generate PDF using imported function
        pdf_buffer = generate_program_pdf(program)
          # Add codigo carrera to the filename if it exists
        cod_carrera = program.get('cod_carrera', '')
        codigo_str = f"_{cod_carrera}" if cod_carrera else ""
        
        # Sanitize filename to prevent HTTP header issues
        base_filename = f"{program.get('nombre_materia', 'programa')}{codigo_str}_{program.get('ano_academico', '')}"
        safe_filename = sanitize_filename(base_filename) + ".pdf"
        
        return send_file(
            pdf_buffer,
            download_name=safe_filename,
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

# Search Options API Routes
@app.route('/api/search_options')
def search_options():
    """Get available options for search form dropdowns"""
    careers = set()
    academic_years = set()

    # Get values from old programs
    for program in OLD_PROGRAMS:
        if program.get('cod_carrera'):
            careers.add(program['cod_carrera'])
        if program.get('ano_academico'):
            academic_years.add(str(program.get('ano_academico')))

    # Get values from API
    api_url = app.config.get('API_URL')
    if api_url:
        try:
            auth = requests.auth.HTTPDigestAuth('usuario1', 'pdf')
            response = requests.get(f"{api_url}/rest/programas", auth=auth, timeout=5)

            if response.status_code == 200:
                api_programs = response.json()
                for program in api_programs:
                    if program.get('cod_carrera'):
                        careers.add(program['cod_carrera'])
                    if program.get('ano_academico'):
                        academic_years.add(str(program.get('ano_academico')))
        except Exception as e:
            print(f"API search error: {str(e)}")

    # Convert career codes to full names and create option objects
    career_options = []
    for code in sorted(careers):
        name = get_career_name(code, CARRERAS)
        career_options.append({
            'code': code,
            'name': name
        })

    return jsonify({
        'careers': career_options,
        'academic_years': sorted(list(academic_years), reverse=True)
    })

if __name__ == '__main__':
    app.run(debug=True)