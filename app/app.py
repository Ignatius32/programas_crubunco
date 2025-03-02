from flask import Flask, render_template, request, send_file, jsonify
import json
import os
import requests
from io import BytesIO
from datetime import datetime
import tempfile
# Import the same PDF generation libraries from the original app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
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
            return json.load(file)
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

# Home Page Route
@app.route('/')
def index():
    """Home page with career listing"""
    # Pass all careers from carreras.json to template
    return render_template('index.html', careers=CARRERAS, now=datetime.now())

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
                        return send_file(
                            buffer,
                            download_name=f"{program.get('nombre_materia', 'programa')}_{program.get('ano_academico', '')}.pdf",
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
        
        return send_file(
            pdf_buffer,
            download_name=f"{program.get('nombre_materia', 'programa')}_{program.get('ano_academico', '')}.pdf",
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
        # Find matching plan by exact plan_version_SIU match
        plan = next((p for p in PLANES_ESTUDIO if p['plan_version_SIU'] == plan_version_siu), None)
        if not plan or not plan.get('url_planEstudio'):
            return "Plan no encontrado o URL no disponible", 404
            
        url = plan['url_planEstudio']
        response = requests.get(url, stream=True)
        
        if response.status_code != 200:
            return f"Error descargando el plan: HTTP {response.status_code}", 500
            
        buffer = BytesIO(response.content)
        nombre_archivo = f"Plan_{plan.get('nombre', 'de_estudio')}_{plan_version_siu}.pdf"
        
        return send_file(
            buffer,
            download_name=nombre_archivo,
            as_attachment=True,
            mimetype='application/pdf'
        )
    except Exception as e:
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
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
])

def process_html_content(content, doc_width, normal_style):
    if not content or '<' not in content:
        return [Paragraph(content, normal_style)]
            
    try:
        soup = BeautifulSoup(content, 'html.parser')
        elements = []
        
        tables = soup.find_all('table')
        if tables:
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
                        cell_text = td.get_text().strip()
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
        
        clean_text = soup.get_text('\n', strip=True)
        paragraphs = clean_text.split('\n')
        for para in paragraphs:
            if para.strip():
                elements.append(Paragraph(para.strip(), normal_style))
        
        return elements
    except Exception as e:
        print(f"Error procesando HTML: {str(e)}")
        return [Paragraph(content, normal_style)]

def programa_header_footer(canvas, doc, programa):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 12)
    header_y = doc.pagesize[1] - inch/4
    canvas.drawString(doc.leftMargin, header_y, "PROGRAMA CRUB")
    
    canvas.setStrokeColorRGB(0, 0, 0)
    canvas.setLineWidth(1.5)
    canvas.line(doc.leftMargin, header_y - 8, 
              doc.pagesize[0] - doc.rightMargin, header_y - 8)
    
    canvas.setFont('Helvetica', 8)
    footer_y = doc.bottomMargin - 30
    
    # Add signatures in specific order
    firma_doc = programa.get('firma_doc', '')
    if firma_doc:
        canvas.drawString(doc.leftMargin, footer_y, f"Firma Docente: {firma_doc}")
        footer_y -= 15
    
    firma_depto = programa.get('firma_depto', '')
    if firma_depto:
        canvas.drawString(doc.leftMargin, footer_y, f"Firma Departamento: {firma_depto}")
        footer_y -= 15
    
    firma_sac = programa.get('firma_sac', '')
    if firma_sac:
        canvas.drawString(doc.leftMargin, footer_y, f"Firma SAC: {firma_sac}")
    
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
        fontSize=10,
        spaceAfter=4,
        leading=12
    )
    
    field_style = ParagraphStyle(
        'FieldStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leading=12,
        leftIndent=0,
        fontName='Helvetica-Bold'
    )
    
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        topMargin=50,
        bottomMargin=90,
        leftMargin=inch,
        rightMargin=inch
    )
    
    programa_elements = []
    
    programa_elements.append(Spacer(1, 0.25*inch))
    programa_elements.append(Paragraph("PROGRAMA", title_style))
    programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add program fields
    fields = [
        ('MATERIA', 'nombre_materia'),
        ('AÑO ACADÉMICO', 'ano_academico'),
        ('DEPARTAMENTO', 'depto'),
        ('PROGRAMA DE CÁTEDRA', lambda p: f"{p.get('nombre_materia', '')} (Cod. Guaraní: {p.get('cod_guarani', '')})"),
        ('OPTATIVA', 'optativa'),
        ('CARRERA A LA QUE PERTENECE Y/O SE OFRECE', lambda p: f"{p.get('nombre_carrera', '')} ({p.get('cod_carrera', '')})"),
        ('ÁREA', 'area'),
        ('ORIENTACIÓN', 'orientacion'),
        ('PLAN DE ESTUDIOS ORD.', 'plan_ordenanzas'),
        ('TRAYECTO (PEF)', 'trayecto'),
        ('CARGA HORARIA SEMANAL SEGÚN PLAN DE ESTUDIOS', 'horas_semanales'),
        ('CARGA HORARIA TOTAL', 'horas_totales'),
        ('RÉGIMEN', 'periodo_dictado')
    ]
    
    doc_width = letter[0] - 2*inch
    
    for label, field in fields:
        value = field(programa) if callable(field) else programa.get(field, '')
        if value:
            programa_elements.append(Paragraph(f"{label}: {value}", field_style))
            programa_elements.append(Spacer(1, 0.05*inch))
    
    # Add equipo de cátedra
    equipo = f"{programa.get('apellido_resp', '')}, {programa.get('nombre_resp', '')} – {programa.get('cargo_resp', '')}"
    programa_elements.append(Paragraph(f"EQUIPO DE CÁTEDRA: {equipo}", field_style))
    
    if programa.get('equipo_catedra'):
        programa_elements.append(Paragraph(programa.get('equipo_catedra', ''), normal_style))
    programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add correlativas section
    programa_elements.append(Paragraph("ASIGNATURAS CORRELATIVAS (según plan de estudios):", field_style))
    programa_elements.append(Spacer(1, 0.05*inch))
    
    programa_elements.append(Paragraph("PARA CURSAR:", normal_style))
    correlativas_cursar = programa.get('correlativas_para_cursar', '').split('\n')
    for corr in correlativas_cursar:
        if corr.strip():
            programa_elements.append(Paragraph(corr.strip(), normal_style))
    
    programa_elements.append(Spacer(1, 0.05*inch))
    programa_elements.append(Paragraph("PARA RENDIR EXAMEN FINAL:", normal_style))
    correlativas_aprobar = programa.get('correlativas_para_aprobar', '').split('\n')
    for corr in correlativas_aprobar:
        if corr.strip():
            programa_elements.append(Paragraph(corr.strip(), normal_style))
    programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add content sections
    sections = [
        ('FUNDAMENTACIÓN', 'fundamentacion'),
        ('OBJETIVOS', 'objetivos'),
        ('CONTENIDOS SEGÚN PLAN DE ESTUDIOS', 'contenidos_minimos'),
        ('CONTENIDO PROGRAMA ANALÍTICO', 'programa_analitico'),
        ('BIBLIOGRAFÍA BÁSICA Y DE CONSULTA', 'bibliografia'),
        ('PROPUESTA METODOLÓGICA MODALIDAD PRESENCIAL', 'propuesta_metodologica'),
        ('EVALUACIÓN Y CONDICIONES DE ACREDITACIÓN', 'evaluacion_acreditacion'),
    ]
    
    for label, field in sections:
        content = programa.get(field)
        if content:
            programa_elements.append(Paragraph(f"{label}:", field_style))
            programa_elements.append(Spacer(1, 0.05*inch))
            html_elements = process_html_content(content, doc_width, normal_style)
            programa_elements.extend(html_elements)
            programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add distribution horaria section
    programa_elements.append(Paragraph("DISTRIBUCIÓN HORARIA:", field_style))
    programa_elements.append(Paragraph(f"Horas teóricas: {programa.get('horas_teoricas', '')}", normal_style))
    programa_elements.append(Paragraph(f"Horas prácticas: {programa.get('horas_practicas', '')}", normal_style))
    programa_elements.append(Paragraph(
        f"Horas teórico-prácticas: {programa.get('horas_teoricopracticas', '')} (solo para LENB y LBIB)", 
        normal_style
    ))
    
    if programa.get('distribucion_horaria'):
        html_elements = process_html_content(programa.get('distribucion_horaria', ''), doc_width, normal_style)
        programa_elements.extend(html_elements)
    programa_elements.append(Spacer(1, 0.1*inch))
    
    # Add cronograma if exists
    if programa.get('cronograma_tentativo'):
        programa_elements.append(Paragraph("CRONOGRAMA TENTATIVO:", field_style))
        programa_elements.append(Spacer(1, 0.05*inch))
        html_elements = process_html_content(programa.get('cronograma_tentativo', ''), doc_width, normal_style)
        programa_elements.extend(html_elements)
    
    def make_header_footer_function(prog):
        return lambda canvas, doc: programa_header_footer(canvas, doc, prog)
    
    header_footer_fn = make_header_footer_function(programa)
    doc.build(programa_elements, onFirstPage=header_footer_fn, onLaterPages=header_footer_fn)
    
    pdf_buffer.seek(0)
    return pdf_buffer

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