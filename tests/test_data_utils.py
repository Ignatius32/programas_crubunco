"""
Unit tests for data_utils.py module
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

# Add app directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from data_utils import (
    load_old_programs, 
    load_carreras, 
    get_career_name, 
    get_unique_careers,
    get_unique_years, 
    get_unique_years_by_type,
    standardize_program_format
)

class TestDataUtils(unittest.TestCase):
    """Test cases for data_utils.py functions"""
    
    def setUp(self):
        """Setup test data"""
        # Sample program data
        self.sample_programs = [
            {
                'nombre_materia': 'Matemática I',
                'cod_carrera': 'P',
                'ano_academico': '2023',
                'ano_plan': '2019'
            },
            {
                'nombre_materia': 'Física I',
                'cod_carrera': 'P',
                'ano_academico': '2022',
                'ano_plan': '2019'
            },
            {
                'nombre_materia': 'Química',
                'cod_carrera': 'B',
                'ano_academico': '2023',
                'ano_plan': '2018'
            }
        ]
        
        # Sample careers data
        self.sample_carreras = [
            {'carrera': 'P', 'nombre': 'Profesorado de Matemática'},
            {'carrera': 'B', 'nombre': 'Licenciatura en Biología'},
            {'carrera': 'I', 'nombre': 'Ingeniería'}
        ]
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    def test_load_old_programs(self, mock_join, mock_json_load, mock_file):
        """Test loading old programs from JSON file"""
        # Mock data
        mock_app = MagicMock()
        mock_app.static_folder = 'static'
        mock_json_load.return_value = [
            {'nombre_materia': 'Test', 'codigo_carrera': 'P', 'firma_dto': 'Firma Test'}
        ]
        mock_join.return_value = 'static/programas_viejos.json'
        
        # Call function
        result = load_old_programs(mock_app)
        
        # Verify it was called with correct params
        mock_join.assert_called_with('static', 'programas_viejos.json')
        mock_file.assert_called_once_with('static/programas_viejos.json', 'r', encoding='utf-8')
        
        # Verify data transformation
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id_programa'], 'old-1')
        self.assertEqual(result[0]['cod_carrera'], 'P')
        self.assertEqual(result[0]['firma_depto'], 'Firma Test')  # Check firma_dto was renamed
        self.assertEqual(result[0]['origen'], 'Archivo histórico')
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('os.path.join')
    def test_load_carreras(self, mock_join, mock_json_load, mock_file):
        """Test loading careers from JSON file"""
        # Mock data
        mock_app = MagicMock()
        mock_app.static_folder = 'static'
        mock_json_load.return_value = self.sample_carreras
        mock_join.return_value = 'static/carreras.json'
        
        # Call function
        result = load_carreras(mock_app)
        
        # Verify it was called with correct params
        mock_join.assert_called_with('static', 'carreras.json')
        mock_file.assert_called_once_with('static/carreras.json', 'r', encoding='utf-8')
        
        # Verify sorting: Engineering programs (starting with 'I') go last
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['carrera'], 'B')  # B should come before P
        self.assertEqual(result[1]['carrera'], 'P')  # P is in the middle
        self.assertEqual(result[2]['carrera'], 'I')  # I should be last
    
    def test_get_career_name(self):
        """Test retrieving career name from code"""
        # Test with existing career code
        self.assertEqual(get_career_name('P', self.sample_carreras), 'Profesorado de Matemática')
        
        # Test with non-existing career code - should return the code itself
        self.assertEqual(get_career_name('X', self.sample_carreras), 'X')
    
    def test_get_unique_careers(self):
        """Test extracting unique careers from programs"""
        result = get_unique_careers(self.sample_programs, self.sample_carreras)
        self.assertEqual(len(result), 2)
        self.assertIn('Profesorado de Matemática', result)
        self.assertIn('Licenciatura en Biología', result)
        
        # Test with empty programs list
        self.assertEqual(len(get_unique_careers([], self.sample_carreras)), 0)
    
    def test_get_unique_years(self):
        """Test extracting unique academic years from programs"""
        result = get_unique_years(self.sample_programs)
        self.assertEqual(len(result), 2)
        self.assertEqual(result, ['2023', '2022'])  # Should be sorted newest first
        
        # Test with empty programs list
        self.assertEqual(len(get_unique_years([])), 0)
    
    def test_get_unique_years_by_type(self):
        """Test extracting unique years by type from programs"""
        # Test academic years filter
        academic_years = get_unique_years_by_type(self.sample_programs, 'academico', 'P')
        self.assertEqual(academic_years, ['2023', '2022'])
        
        # Test plan years filter
        plan_years = get_unique_years_by_type(self.sample_programs, 'cursada', 'P')
        self.assertEqual(plan_years, ['2019'])
        
        # Test with different career
        b_years = get_unique_years_by_type(self.sample_programs, 'cursada', 'B')
        self.assertEqual(b_years, ['2018'])
    
    def test_standardize_program_format(self):
        """Test standardization of program data"""
        program = {
            'id': 123,
            'codigo_carrera': 'P',
            'firma_dto': 'Firma Test'
        }
        
        standardize_program_format(program, self.sample_carreras)
        
        self.assertEqual(program['id_programa'], '123')
        self.assertEqual(program['cod_carrera'], 'P')
        self.assertEqual(program['nombre_carrera'], 'Profesorado de Matemática')
        self.assertEqual(program['firma_depto'], 'Firma Test')
        self.assertNotIn('firma_dto', program)  # Should be removed

if __name__ == '__main__':
    unittest.main()