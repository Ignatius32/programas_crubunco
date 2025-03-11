from flask import Flask, render_template, request, send_file, jsonify, make_response
import json
import os
import requests
from io import BytesIO
from datetime import datetime
import tempfile
# Import the same PDF generation libraries from the original app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListItem, ListFlowable
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

app = Flask(__name__)
app.config['API_URL'] = os.environ.get('API_URL', '')  # API URL from environment variables

# Load data at startup
OLD_PROGRAMS = []
PLANES_ESTUDIO = []
CARRERAS = []

@app.before_first_request
def load_data():
    global OLD_PROGRAMS, PLANES_ESTUDIO, CARRERAS
    OLD_PROGRAMS = load_old_programs()
    PLANES_ESTUDIO = load_planes_estudio()
    CARRERAS = load_carreras()

# Function to load old programs from JSON file
def load_old_programs():
    try:
        json_path = os.path.join(app.static_folder, 'programas_viejos.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            old_programs = json.load(file)
            
        for i, program in enumerate(old_programs):
            program['id_programa'] = f"old-{i+1}"
            program['cod_carrera'] = program.get('codigo_carrera', '')
            program['origen'] = 'Archivo histórico'  # Add origin field
            # Standardize signature field names
            if 'firma_dto' in program:
                program['firma_depto'] = program.pop('firma_dto')
            
        return old_programs
    except Exception as e:
        print(f"Error loading old programs: {str(e)}")
        return []

# Function to load planes de estudio from JSON file
def load_planes_estudio():
    try:
        json_path = os.path.join(app.static_folder, 'planes_estudio.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            planes = json.load(file)
        # Filter only planes that have a URL
        return [plan for plan in planes if plan.get('url_planEstudio')]
    except Exception as e:
        print(f"Error loading planes de estudio: {str(e)}")
        return []

# Function to load careers data from JSON file
def load_carreras():
    try:
        json_path = os.path.join(app.static_folder, 'carreras.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            carreras = json.load(file)
            # Custom sort: engineering programs (starting with 'I') go last
            return sorted(carreras, key=lambda x: (x['carrera'].startswith('I'), x['carrera']))
    except Exception as e:
        print(f"Error loading careers: {str(e)}")
        return []

# Function to get career name from code
def get_career_name(career_code):
    for carrera in CARRERAS:
        if carrera['carrera'] == career_code:
            return carrera['nombre']
    return career_code

# Function to extract unique careers from programs
def get_unique_careers(programs):
    careers = set()
    for program in programs:
        # Get career code from either cod_carrera or codigo_carrera
        career_code = program.get('cod_carrera', program.get('codigo_carrera', ''))
        
        # Get full career name from careers.json
        if career_code:
            career_name = get_career_name(career_code)
            careers.add(career_name)
    
    return sorted(list(careers))

# Function to extract unique academic years from programs
def get_unique_years(programs):
    years = set()
    for program in programs:
        year = program.get('ano_academico', '')
        if year:
            years.add(str(year))
    
    return sorted(list(years), reverse=True)  # Most recent years first

# Function to extract unique years from programs based on type
def get_unique_years_by_type(programs, year_type, carrera):
    years = set()
    filtered_programs = [p for p in programs if p.get('cod_carrera') == carrera]
    
    for program in filtered_programs:
        if year_type == 'academico':
            year = program.get('ano_academico', '')
        else:  # year_type == 'cursada'
            year = program.get('ano_plan', '')
        
        if year:
            years.add(str(year))
    
    return sorted(list(years), reverse=True)  # Most recent years first

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
    career_name = get_career_name(carrera_nombre)
    
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
        
        if ano_academico and ano_academico != program.get('ano_academico', ''):
            matches = False
            
        if query:
            query_lower = query.lower()
            career_name = get_career_name(program.get('cod_carrera', ''))
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
                    if 'id' in program and 'id_programa' not in program:
                        program['id_programa'] = str(program['id'])
                    if 'codigo_carrera' in program and 'cod_carrera' not in program:
                        program['cod_carrera'] = program['codigo_carrera']
                    if 'nombre_carrera' not in program:
                        program['nombre_carrera'] = get_career_name(program['cod_carrera'])
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
                    if 'id' in program and 'id_programa' not in program:
                        program['id_programa'] = str(program['id'])
                    if 'codigo_carrera' in program and 'cod_carrera' not in program:
                        program['cod_carrera'] = program['codigo_carrera']
                    if 'nombre_carrera' not in program:
                        program['nombre_carrera'] = get_career_name(program['cod_carrera'])
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

# Search Planes de Estudio API Route
@app.route('/api/search_planes')
def search_planes():
    """Search planes de estudio"""
    carrera = request.args.get('carrera', '').strip()
    vigente = request.args.get('vigente', '').strip()
    
    results = []
    
    for plan in PLANES_ESTUDIO:
        matches = True
        
        if carrera and plan.get('carrera') != carrera:
            matches = False
        
        if vigente and vigente != plan.get('vigente', ''):
            matches = False
        
        if matches and plan.get('url_planEstudio'):
            results.append(plan)
    
    # Sort results so vigente='si' appears first
    results.sort(key=lambda x: (x.get('vigente', '') != 'si', x.get('carrera', ''), x.get('anio_entrada_vigencia', '')))
    
    return jsonify(results)

# Get Planes de Estudio Options API Route
@app.route('/api/planes_options')
def planes_options():
    """Get available options for planes de estudio search form dropdowns"""
    # Get unique careers and vigencia states from planes de estudio
    careers = set()
    vigencia_states = set()
    
    for plan in PLANES_ESTUDIO:
        if plan.get('carrera'):
            careers.add(plan['carrera'])
        if plan.get('vigente'):
            vigencia_states.add(plan['vigente'])
    
    # Convert career codes to full names and create option objects
    career_options = []
    for code in sorted(careers):
        name = get_career_name(code)
        career_options.append({
            'code': code,
            'name': name
        })
    
    return jsonify({
        'careers': career_options,
        'vigencia_states': sorted(list(vigencia_states))
    })

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
                        buffer = BytesIO(response.content)
                        # Add codigo carrera to the filename if it exists
                        cod_carrera = program.get('cod_carrera', '')
                        codigo_str = f"_{cod_carrera}" if cod_carrera else ""
                        return send_file(
                            buffer,
                            download_name=f"{program.get('nombre_materia', 'programa')}{codigo_str}_{program.get('ano_academico', '')}.pdf",
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
        
        # Standardize signature field names
        if 'firma_dto' in program:
            program['firma_depto'] = program.pop('firma_dto')
        
        # Generate PDF using existing function
        pdf_buffer = generate_program_pdf(program)
        
        # Add codigo carrera to the filename if it exists
        cod_carrera = program.get('cod_carrera', '')
        codigo_str = f"_{cod_carrera}" if cod_carrera else ""
        
        return send_file(
            pdf_buffer,
            download_name=f"{program.get('nombre_materia', 'programa')}{codigo_str}_{program.get('ano_academico', '')}.pdf",
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

# Download Plan de Estudios Route
@app.route('/download/plan/<path:plan_version_siu>')
def download_plan(plan_version_siu):
    """Download a plan de estudios PDF"""
    try:
        # Clean up any URL encoding in the parameter
        plan_version_siu = plan_version_siu.strip()
        
        # Find matching plan by exact plan_version_SIU match
        plan = next((p for p in PLANES_ESTUDIO if p['plan_version_SIU'] == plan_version_siu), None)
        if not plan or not plan.get('url_planEstudio'):
            return "Plan no encontrado o URL no disponible", 404
            
        url = plan['url_planEstudio']
        # Handle spaces and special characters in URL
        url = url.replace(' ', '%20')
        
        # Add base URL path if URL is relative
        base_url = get_base_url_path()
        if url.startswith('/'):
            url = f"https://archivo.crub.uncoma.edu.ar{url}"
            
        response = requests.get(url, stream=True, verify=False)  # Added verify=False for self-signed certs
        
        if response.status_code != 200:
            print(f"Error downloading plan - URL: {url}, Status: {response.status_code}")
            return f"Error descargando el plan: HTTP {response.status_code}", 500
            
        buffer = BytesIO(response.content)
        nombre_carrera = plan.get('nombre', '').strip() or plan.get('carrera', 'de_estudio')
        nombre_archivo = f"Plan_{nombre_carrera}_{plan_version_siu}.pdf"
        
        return send_file(
            buffer,
            download_name=nombre_archivo,
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error downloading plan: {str(e)}")  # Added logging
        return f"Error: {str(e)}", 500

# Table style for HTML content
table_style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('TOPPADDING', (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
])

def process_formatted_text(element):
    """
    Recursively process HTML elements to preserve formatting like bold, italic, etc.
    """
    if element.name is None:  # It's a NavigableString
        return element.string or ''
    
    # Start with an empty result
    result = ''
    
    # Process child elements
    for child in element.children:
        if child.name == 'strong' or child.name == 'b':
            result += f"<b>{process_formatted_text(child)}</b>"
        elif child.name == 'em' or child.name == 'i':
            result += f"<i>{process_formatted_text(child)}</i>"
        elif child.name == 'u':
            result += f"<u>{process_formatted_text(child)}</u>"
        elif child.name == 'br':
            result += "<br/>"
        elif child.name == 'a':
            href = child.get('href', '#')
            result += f"<a href='{href}'><u>{process_formatted_text(child)}</u></a>"
        elif child.name in ['ul', 'ol', 'li', 'p', 'div', 'span']:
            # For container elements, just process their content
            result += process_formatted_text(child)
        else:
            # For other elements or text nodes
            if hasattr(child, 'string') and child.string:
                result += child.string
            elif isinstance(child, str):
                result += child
            else:
                result += process_formatted_text(child)
    
    return result

def process_html_content(content, doc_width, normal_style):
    # Handle empty content
    if not content:
        return []
    
    # First, replace problematic Unicode characters with their HTML equivalents
    # Common Unicode quotation marks and other special characters
    unicode_replacements = {
        '\u0091': "'",  # Left single quotation mark
        '\u0092': "'",  # Right single quotation mark
        '\u0093': '"',  # Left double quotation mark
        '\u0094': '"',  # Right double quotation mark
        '\u0095': '•',  # Bullet
        '\u0096': '–',  # En dash
        '\u0097': '—',  # Em dash
        '\u00AB': '«',  # Left-pointing double angle quotation mark
        '\u00BB': '»',  # Right-pointing double angle quotation mark
        '\u201C': '"',  # Left double quotation mark
        '\u201D': '"',  # Right double quotation mark
        '\u2018': ''',  # Left single quotation mark
        '\u2019': ''',  # Right single quotation mark
    }
    
    # Replace Unicode characters
    for unicode_char, replacement in unicode_replacements.items():
        if unicode_char in content:
            content = content.replace(unicode_char, replacement)
    
    # Check if we need to convert raw text formatting to HTML
    if '<' not in content:
        # Import re for regex operations
        import re
        
        # Apply common formatting patterns for academic/technical content
        
        # 1. Convert markdown-style italics to HTML
        # Replace *text* with <i>text</i> but only if * is not part of a word
        content = re.sub(r'(?<!\w)\*([^\*]+)\*(?!\w)', r'<i>\1</i>', content)
        # Replace _text_ with <i>text</i> but only if _ is not part of a word
        content = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<i>\1</i>', content)
        
        # 2. Italicize technical terms commonly found in language education
        # Find "TO + verb" patterns (common in language teaching)
        content = re.sub(r'\bTO\s+(BE|DO|HAVE)\b', r'<i>TO \1</i>', content)
        
        # 3. Find domain-specific terms that should be italicized
        technical_terms = [
            'carry out', 'measure out', 'shall', 'must', 'should', 
            'will', 'could', 'may', 'might', 'ing', 'maxima verosimilitud',
            'maxima verosimilidad'
        ]
        
        for term in technical_terms:
            # Make sure we're not matching within other words
            term_pattern = r'\b' + re.escape(term) + r'\b'
            content = re.sub(term_pattern, f'<i>{term}</i>', content, flags=re.IGNORECASE)
        
        # Check if we have bullet points (• or – are common bullet characters)
        bullet_chars = ['\u0095', '\u0096', '•', '–']
        has_bullets = any(bullet in content for bullet in bullet_chars)
        
        if has_bullets:
            # Convert bullet points to HTML list
            # First split by newlines to preserve paragraph structure
            paragraphs = content.split('\n')
            html_parts = []
            
            in_list = False
            for para in paragraphs:
                para_strip = para.strip()
                is_bullet_point = any(para_strip.startswith(bullet) for bullet in bullet_chars)
                
                if is_bullet_point:
                    # Start a new list if not already in one
                    if not in_list:
                        html_parts.append('<ul>')
                        in_list = True
                    
                    # Clean up the bullet point and add as list item
                    item = para_strip
                    for bullet in bullet_chars:
                        if item.startswith(bullet):
                            item = item.replace(bullet, '', 1).strip()
                            break
                    html_parts.append(f'<li>{item}</li>')
                else:
                    # Close the list if we were in one
                    if in_list:
                        html_parts.append('</ul>')
                        in_list = False
                    
                    # Add as regular paragraph if not empty
                    if para.strip():
                        html_parts.append(f'<p>{para.strip()}</p>')
            
            # Close any open list
            if in_list:
                html_parts.append('</ul>')
            
            html_content = ''.join(html_parts)
            soup = BeautifulSoup(html_content, 'html.parser')
        else:
            # If it's plain text without bullets, just create paragraphs from newlines
            paragraphs = content.split('\n')
            elements = []
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), normal_style))
            return elements
    else:
        # Content already has HTML tags
        soup = BeautifulSoup(content, 'html.parser')
            
    try:
        # ...existing processing code...
        elements = []
        
        # Process tables first
        tables = soup.find_all('table')
        if tables:
            # ...existing table processing code...
            for table in tables:
                rows = []
                
                headers = table.find('thead')
                if headers:
                    header_row = []
                    for th in headers.find_all(['th', 'td']):
                        header_row.append(Paragraph(th.get_text().strip(), normal_style))
                    if header_row:
                        rows.append(header_row)
                
                for tr in table.find_all('tr'):
                    if tr.parent.name == 'thead':
                        continue
                            
                    row = []
                    for td in tr.find_all(['td', 'th']):
                        # Use process_formatted_text to handle rich text
                        cell_text = process_formatted_text(td)
                        row.append(Paragraph(cell_text, normal_style))
                    
                    if row:
                        rows.append(row)
                
                if rows:
                    col_count = max([len(row) for row in rows])
                    col_width = doc_width / col_count
                    
                    tbl = Table(rows, colWidths=[col_width] * col_count)
                    tbl.setStyle(table_style)
                    elements.append(tbl)
                    elements.append(Spacer(1, 0.1*inch))
            return elements
        
        # Process lists (both HTML lists and unicode bullet lists)
        ul_elements = soup.find_all(['ul', 'ol'])
        if ul_elements:
            for ul in ul_elements:
                list_items = []
                for li in ul.find_all('li'):
                    # Properly handle rich text formatting in list items
                    text = process_formatted_text(li)
                    list_items.append(ListItem(Paragraph(text, normal_style)))
                
                # Check if it's an ordered list
                is_ordered = ul.name == 'ol'
                bullet_type = 'decimal' if is_ordered else 'bullet'
                
                list_flowable = ListFlowable(
                    list_items,
                    bulletType=bullet_type,
                    leftIndent=20,
                    spaceBefore=6,
                    spaceAfter=6
                )
                elements.append(list_flowable)
            
            # After processing lists, look for paragraphs outside lists
            for p in soup.find_all('p'):
                if not any(p.find_parents(['ul', 'ol', 'li'])):
                    text = process_formatted_text(p)
                    if text.strip():
                        elements.append(Paragraph(text, normal_style))
                        
            # If we have elements, return them; otherwise continue with other checks
            if elements:
                return elements
        
        # Process paragraphs with formatting
        p_elements = soup.find_all('p')
        if p_elements:
            for p in p_elements:
                text = process_formatted_text(p)
                if text.strip():
                    elements.append(Paragraph(text, normal_style))
            
            # If we have paragraph elements, return them
            if elements:
                return elements
        
        # If no specific elements found, check for unprocessed text
        # We need to handle both the bullet points and preserve formatting
        text = soup.get_text()
        
        # Check for bullet points in remaining text
        bullet_chars = ['\u0095', '\u0096', '•', '–']  # Include all bullet types
        has_remaining_bullets = any(bullet in text for bullet in bullet_chars)
        
        if has_remaining_bullets:
            # ...existing bullet point processing code...
            current_paragraphs = []
            list_items = []
            in_list = False
            
            # Split by lines and process each
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line is a bullet point
                is_bullet = any(line.startswith(bullet) for bullet in bullet_chars)
                
                if is_bullet:
                    # If we have text waiting to be output, do it now
                    if current_paragraphs and not in_list:
                        for para in current_paragraphs:
                            elements.append(Paragraph(para, normal_style))
                        current_paragraphs = []
                    
                    # Start a new list if needed
                    if not in_list:
                        in_list = True
                    
                    # Clean up the bullet point and add as list item
                    for bullet in bullet_chars:
                        if line.startswith(bullet):
                            item = line.replace(bullet, '', 1).strip()
                            list_items.append(ListItem(Paragraph(item, normal_style)))
                            break
                else:
                    # Not a bullet point
                    if in_list:
                        # End the current list
                        if list_items:
                            list_flowable = ListFlowable(
                                list_items,
                                bulletType='bullet',
                                leftIndent=20,
                                spaceBefore=6,
                                spaceAfter=6
                            )
                            elements.append(list_flowable)
                            list_items = []
                        in_list = False
                    
                    # Add as regular paragraph
                    current_paragraphs.append(line)
            
            # Process any remaining content
            if in_list and list_items:
                list_flowable = ListFlowable(
                    list_items,
                    bulletType='bullet',
                    leftIndent=20,
                    spaceBefore=6,
                    spaceAfter=6
                )
                elements.append(list_flowable)
            
            if current_paragraphs:
                for para in current_paragraphs:
                    elements.append(Paragraph(para, normal_style))
            
            return elements
        
        # If we got here, process the whole text by paragraphs
        text = process_formatted_text(soup)
        
        # Handle non-HTML formatting: convert simple newlines to paragraphs
        paragraphs = []
        if '\n' in text:
            for para in text.split('\n'):
                if para.strip():
                    paragraphs.append(para.strip())
        else:
            paragraphs = [text]
            
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para.strip(), normal_style))
                
        return elements
    except Exception as e:
        print(f"Error procesando HTML: {str(e)}")
        return [Paragraph(content, normal_style)]

def programa_header_footer(canvas, doc, programa):
    canvas.saveState()
    
    # Get the path to the logo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(current_dir, 'static', 'img', 'logounco.webp')
    
    # Draw the logo if it exists
    if (os.path.exists(logo_path)):
        logo_width = 35*mm
        logo_height = 35*mm
        canvas.drawImage(logo_path, doc.leftMargin, doc.pagesize[1] - 38*mm, 
                        width=logo_width, height=logo_height, preserveAspectRatio=True,
                        anchor='n')
    
    # Add centered header text aligned with logo's top margin
    # Using grey color with normal line spacing
    canvas.setFillColorRGB(0.5, 0.5, 0.5)  # Medium grey color for watermark effect
    
    canvas.setFont('Helvetica-Bold', 9)
    header_x = doc.pagesize[0] / 2  # Center of page
    header_y = doc.pagesize[1] - 10*mm  # Higher position (matching logo's top margin)
    canvas.drawCentredString(header_x, header_y, "Secretaría Académica")
    
    canvas.setFont('Helvetica', 9)
    canvas.drawCentredString(header_x, header_y - 12, "Centro Regional Universitario Bariloche")
    canvas.drawCentredString(header_x, header_y - 24, "Universidad Nacional del Comahue")
    
    # Add subtle line divider below header text
    canvas.setLineWidth(0.5)
    canvas.setStrokeColorRGB(0.7, 0.7, 0.7)  # Light grey line
    line_y = header_y - 32  # Position line below the header text
    canvas.line(doc.leftMargin + 50, line_y, doc.pagesize[0] - doc.leftMargin - 50, line_y)
    
    # Reset fill color to black for footer content
    canvas.setFillColorRGB(0, 0, 0)
    canvas.setStrokeColorRGB(0, 0, 0)  # Reset stroke color too
    
    canvas.setFont('Helvetica', 6)  # Smaller font size for signatures
    # Calculate positions for signatures at the bottom
    firma_x = 2*mm  # Left alignment
    
    # First determine how many firma lines we'll have
    lines_count = 0
    if programa.get('firma_doc', ''): lines_count += 1
    if programa.get('firma_depto', ''): lines_count += 1
    if programa.get('firma_sac', ''): lines_count += 1
    
    # Calculate initial y position to fit all lines
    footer_y = 10 + (lines_count * 4)  # 2 points buffer from bottom + 4pt spacing per line
    
    firma_doc = programa.get('firma_doc', '')
    if firma_doc:
        canvas.drawString(firma_x, footer_y, f"{firma_doc}")
        footer_y -= 8  # Minimal spacing between lines
    
    firma_depto = programa.get('firma_depto', '')
    if firma_depto:
        canvas.drawString(firma_x, footer_y, f"{firma_depto}")
        footer_y -= 8  # Minimal spacing between lines
    
    firma_sac = programa.get('firma_sac', '')
    if firma_sac:
        canvas.drawString(firma_x, footer_y, f"{firma_sac}")
    
    canvas.restoreState()

def generate_program_pdf(programa):
    """Generate a PDF for a program from API data"""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=6,
        alignment=1,
        keepWithNext=True
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leading=14,
        wordWrap='LTR',  # Left-to-right word wrap
        allowWidows=0,   # Prevent widowed lines
        allowOrphans=0   # Prevent orphaned lines
    )
    
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leading=14,
        leftIndent=0,
        fontName='Helvetica-Bold'
    )
    
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=20*mm,     # Keep top margin for header
        bottomMargin=15*mm,   # Reduced bottom margin
        leftMargin=25*mm,    # Keep left margin for readability
        rightMargin=25*mm,   # Keep right margin for readability
        allowSplitting=1,    # Allow more aggressive content splitting
        displayDocTitle=True, # Better PDF metadata
        splitLongWords=1,    # Allow long words to split
        pageCompression=1    # Compress the PDF
    )
    
    # Generate program elements using the helper function
    programa_elements = generate_program_content(programa, title_style, field_style, normal_style)
    
    # Create header/footer function for this program
    def make_header_footer_function(prog):
        return lambda canvas, doc: programa_header_footer(canvas, doc, prog)
    
    header_footer_fn = make_header_footer_function(programa)
    doc.build(programa_elements, onFirstPage=header_footer_fn, onLaterPages=header_footer_fn)
    
    pdf_buffer.seek(0)
    return pdf_buffer

def generate_program_content(programa, title_style, field_style, normal_style):
    """Helper function to generate the content elements for a program PDF"""
    programa_elements = []
    
    # Create a justified style for content sections
    justified_style = ParagraphStyle(
        'JustifiedContent',
        parent=normal_style,
        alignment=4,  # 4 = Justified
        spaceAfter=6,
        leading=14
    )
    
    programa_elements.append(Spacer(1, 0.35*inch))
    
    # Header sections (unchanged)
    programa_elements.append(Spacer(1, 0.35*inch))  # Reduced from 0.45 for initial spacing
    
    # Replace PROGRAMA title with AÑO ACADÉMICO: ano_academico
    ano_academico = programa.get('ano_academico', '')
    programa_elements.append(Paragraph(f"AÑO ACADÉMICO: {ano_academico}", title_style))
    programa_elements.append(Spacer(1, 0.03*inch))  # Reduced from 0.05
    
    # Reordered fields according to the requested format
    # Add department first if it exists
    depto = programa.get('depto', '')
    if depto and depto.strip():
        programa_elements.append(Paragraph(f"DEPARTAMENTO: {depto}", field_style))
        programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Program with code
    nombre_materia = programa.get('nombre_materia', '')
    cod_guarani = programa.get('cod_guarani', '')
    if nombre_materia and nombre_materia.strip():
        optativa = programa.get('optativa', '')
        optativa_text = "(OPT)" if optativa and optativa.lower() in ["si", "sí"] else ""
        programa_elements.append(Paragraph(f"PROGRAMA DE CÁTEDRA: {nombre_materia} {optativa_text}", field_style))
        if cod_guarani and cod_guarani.strip():
            programa_elements.append(Paragraph(f"(Cod. Guaraní: {cod_guarani})", normal_style))
        programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Optativa - only show if it's "Si" or "Sí"
    optativa = programa.get('optativa', '')
    if optativa and optativa.strip().lower() in ["si", "sí"]:
        programa_elements.append(Paragraph(f"OPTATIVA: {optativa}", field_style))
        programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Career info
    carrera = programa.get('nombre_carrera', '')
    cod_carrera = programa.get('cod_carrera', '')
    if carrera and carrera.strip():
        programa_elements.append(Paragraph(f"CARRERA A LA QUE PERTENECE Y/O SE OFRECE:", field_style))
        career_text = carrera
        if cod_carrera and cod_carrera.strip():
            career_text += f" - ({cod_carrera})"
        programa_elements.append(Paragraph(career_text, normal_style))
        programa_elements.append(Spacer(1, 0.08*inch))  # Reduced from 0.15 after correlativas
    
    # Process fields that should only be shown if they have non-empty values
    fields = [
        ('ÁREA', 'area'),
        ('ORIENTACIÓN', 'orientacion'),
        ('PLAN DE ESTUDIOS ORD.', 'plan_ordenanzas')
    ]
    
    for label, field in fields:
        value = programa.get(field, '')
        if value and value.strip():
            programa_elements.append(Paragraph(f"{label}: {value}", field_style))
            programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Handle TRAYECTO (PEF) separately - only show if not "N/C"
    trayecto = programa.get('trayecto', '')
    if trayecto and trayecto.strip() and trayecto.strip().upper() != "N/C":
        programa_elements.append(Paragraph(f"TRAYECTO (PEF): {trayecto}", field_style))
        programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Process numerical fields - only show if they have non-zero values
    fields = [
        ('CARGA HORARIA SEMANAL SEGÚN PLAN DE ESTUDIOS', 'horas_semanales'),
        ('CARGA HORARIA TOTAL', 'horas_totales')
    ]
    
    for label, field in fields:
        value = programa.get(field, '')
        try:
            # Try to convert to float to handle both string and numeric values
            num_value = float(str(value).replace(',', '.'))
            if num_value > 0:
                programa_elements.append(Paragraph(f"{label}: {value}", field_style))
                programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
        except (ValueError, TypeError):
            # If conversion fails but we have a non-empty string, show it
            if value and str(value).strip():
                programa_elements.append(Paragraph(f"{label}: {value}", field_style))
                programa_elements.append(Spacer(1, 0.03*inch))  # Reduced spacing after basic info
    
    # Add RÉGIMEN if it exists
    regimen = programa.get('periodo_dictado', '')
    if regimen and regimen.strip():
        programa_elements.append(Paragraph(f"RÉGIMEN: {regimen}", field_style))
        programa_elements.append(Spacer(1, 0.08*inch))  # Reduced from 0.15 after correlativas
    
    # Add equipo de cátedra
    programa_elements.append(Paragraph(f"EQUIPO DE CÁTEDRA:", field_style))
    
    # Only add responsible person info if we have at least one of the fields
    apellido_resp = programa.get('apellido_resp', '').strip()
    nombre_resp = programa.get('nombre_resp', '').strip()
    cargo_resp = programa.get('cargo_resp', '').strip()
    
    if any([apellido_resp, nombre_resp, cargo_resp]):
        equipo_parts = []
        if apellido_resp or nombre_resp:
            name_parts = [p for p in [apellido_resp, nombre_resp] if p]
            equipo_parts.append(", ".join(name_parts))
        if cargo_resp:
            equipo_parts.append(cargo_resp)
        equipo = " - ".join(equipo_parts)
        programa_elements.append(Paragraph(equipo, normal_style))
    
    # Add additional team members if they exist
    if programa.get('equipo_catedra'):
        programa_elements.append(Paragraph(programa.get('equipo_catedra', ''), normal_style))
    programa_elements.append(Spacer(1, 0.08*inch))  # Reduced from 0.15 after correlativas
    
    # Add correlativas section
    programa_elements.append(Paragraph("ASIGNATURAS CORRELATIVAS (según plan de estudios):", field_style))
    programa_elements.append(Spacer(1, 0.03*inch))  # Reduced from 0.05
    
    # Para cursar section
    programa_elements.append(Paragraph("- PARA CURSAR:", normal_style))
    correlativas_cursar = programa.get('correlativas_para_cursar', '').split('\n')
    has_cursar = False
    for corr in correlativas_cursar:
        if corr.strip():
            programa_elements.append(Paragraph(corr.strip(), normal_style))
            has_cursar = True
    if not has_cursar:
        programa_elements.append(Paragraph("No posee correlativas para cursar", normal_style))
    
    programa_elements.append(Spacer(1, 0.03*inch))  # Reduced from 0.05
    
    # Para rendir section
    programa_elements.append(Paragraph("- PARA RENDIR EXAMEN FINAL:", normal_style))
    correlativas_aprobar = programa.get('correlativas_para_aprobar', '').split('\n')
    has_aprobar = False
    for corr in correlativas_aprobar:
        if corr.strip():
            programa_elements.append(Paragraph(corr.strip(), normal_style))
            has_aprobar = True
    if not has_aprobar:
        programa_elements.append(Paragraph("No posee correlativas para rendir", normal_style))
    
    programa_elements.append(Spacer(1, 0.08*inch))  # Reduced from 0.15 after correlativas
    
    # Process main content sections with justified text
    sections = [
        ('FUNDAMENTACIÓN', 'fundamentacion'),
        ('OBJETIVOS', 'objetivos'),
        ('CONTENIDOS SEGÚN PLAN DE ESTUDIOS', 'contenidos_minimos'),
        ('CONTENIDO PROGRAMA ANALÍTICO', 'programa_analitico'),
        ('BIBLIOGRAFÍA BÁSICA Y DE CONSULTA', 'bibliografia'),
        ('PROPUESTA METODOLÓGICA MODALIDAD PRESENCIAL', 'propuesta_metodologica'),
        ('EVALUACIÓN Y CONDICIONES DE ACREDITACIÓN', 'evaluacion_acreditacion'),
    ]
    
    doc_width = A4[0] - 2*25*mm
    for label, field in sections:
        content = programa.get(field)
        if content and content.strip():
            programa_elements.append(Paragraph(f"{label}:", field_style))
            html_elements = process_html_content(content, doc_width, justified_style)
            programa_elements.extend(html_elements)
            programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add distribution horaria section
    programa_elements.append(Paragraph("DISTRIBUCIÓN HORARIA:", field_style))
    
    # Hours display (use justified style for descriptive text)
    for label, field in [
        ('Horas teóricas', 'horas_teoricas'),
        ('Horas prácticas', 'horas_practicas'),
        ('Horas teórico-prácticas', 'horas_teoricopracticas')
    ]:
        value = programa.get(field, '')
        try:
            num_value = float(str(value).replace(',', '.'))
            if num_value > 0:
                extra_text = " (solo para LENB y LBIB)" if field == 'horas_teoricopracticas' else ""
                programa_elements.append(Paragraph(f"{label}: {value}{extra_text}", normal_style))
        except (ValueError, TypeError):
            if value and str(value).strip():
                extra_text = " (solo para LENB y LBIB)" if field == 'horas_teoricopracticas' else ""
                programa_elements.append(Paragraph(f"{label}: {value}{extra_text}", normal_style))
    
    # Add additional distribution info with justified text
    if programa.get('distribucion_horaria'):
        html_elements = process_html_content(programa.get('distribucion_horaria', ''), doc_width, justified_style)
        programa_elements.extend(html_elements)
    programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add cronograma with justified text if it exists
    cronograma = programa.get('cronograma_tentativo', '')
    if cronograma and cronograma.strip():
        programa_elements.append(Paragraph("CRONOGRAMA TENTATIVO:", field_style))
        html_elements = process_html_content(cronograma, doc_width, justified_style)
        programa_elements.extend(html_elements)
    
    return programa_elements

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
        name = get_career_name(code)
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