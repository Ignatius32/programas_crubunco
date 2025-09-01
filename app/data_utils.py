"""
Data loading and manipulation utilities for the programa application.
"""
import json
import os
from flask import Flask

# Global data storage
OLD_PROGRAMS = []
CARRERAS = []

def load_old_programs(app):
    """Load old programs from JSON file"""
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

def load_carreras(app):
    """Load careers data from JSON file"""
    try:
        json_path = os.path.join(app.static_folder, 'carreras.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            carreras = json.load(file)
            # Custom sort: engineering programs (starting with 'I') go last
            return sorted(carreras, key=lambda x: (x['carrera'].startswith('I'), x['carrera']))
    except Exception as e:
        print(f"Error loading careers: {str(e)}")
        return []

def get_career_name(career_code, carreras):
    """Get career name from code"""
    for carrera in carreras:
        if carrera['carrera'] == career_code:
            return carrera['nombre']
    return career_code

def get_unique_careers(programs, carreras):
    """Extract unique careers from programs"""
    careers = set()
    for program in programs:
        # Get career code from either cod_carrera or codigo_carrera
        career_code = program.get('cod_carrera', program.get('codigo_carrera', ''))
        
        # Get full career name from careers.json
        if career_code:
            career_name = get_career_name(career_code, carreras)
            careers.add(career_name)
    
    return sorted(list(careers))

def get_unique_years(programs):
    """Extract unique academic years from programs"""
    years = set()
    for program in programs:
        year = program.get('ano_academico', '')
        if year:
            years.add(str(year))
    
    return sorted(list(years), reverse=True)  # Most recent years first

def get_unique_years_by_type(programs, year_type, carrera):
    """Extract unique years from programs based on type"""
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

def init_data(app):
    """Initialize global data"""
    global OLD_PROGRAMS, CARRERAS
    OLD_PROGRAMS = load_old_programs(app)
    CARRERAS = load_carreras(app)
    return OLD_PROGRAMS, CARRERAS

# API data related functions
def standardize_program_format(program, carreras):
    """Standardize program data format"""
    if 'id' in program and 'id_programa' not in program:
        program['id_programa'] = str(program['id'])
    if 'codigo_carrera' in program and 'cod_carrera' not in program:
        program['cod_carrera'] = program['codigo_carrera']
    if 'nombre_carrera' not in program:
        program['nombre_carrera'] = get_career_name(program['cod_carrera'], carreras)
    if 'firma_dto' in program:
        program['firma_depto'] = program.pop('firma_dto')
    return program