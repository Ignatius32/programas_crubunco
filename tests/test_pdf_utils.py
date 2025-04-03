"""
Unit tests for pdf_utils.py module
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
from bs4 import BeautifulSoup

# Add app directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# Import ReportLab components needed for tests
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table

from pdf_utils import (
    process_content,
    process_plain_text,
    normalize_unicode,
    process_html_content
)

class TestPDFUtils(unittest.TestCase):
    """Test cases for pdf_utils.py functions"""
    
    def setUp(self):
        """Setup common test data"""
        # Get a style to use for testing
        self.styles = getSampleStyleSheet()
        self.normal_style = self.styles['Normal']
        
        # Set a reasonable document width for testing
        self.doc_width = 500
    
    def test_normalize_unicode(self):
        """Test Unicode normalization utility"""
        # This is mainly a wrapper for normalize_text
        special_text = '\u2022 Bullet point'
        result = normalize_unicode(special_text)
        self.assertEqual(result, '• Bullet point')
    
    def test_process_plain_text_simple(self):
        """Test processing simple plain text"""
        # Test basic text processing
        text = "This is a sample paragraph."
        elements = process_plain_text(text, self.normal_style)
        
        # Should return one paragraph
        self.assertEqual(len(elements), 1)
        self.assertIsInstance(elements[0], Paragraph)
        self.assertEqual(elements[0].text, "This is a sample paragraph.")
    
    def test_process_plain_text_with_bullet_points(self):
        """Test processing text with bullet points"""
        # Text with bullet points
        text = "Introduction:\n• First point\n• Second point\nConclusion"
        elements = process_plain_text(text, self.normal_style)
        
        # Should have 3 elements: intro paragraph, bullet list, conclusion paragraph
        self.assertEqual(len(elements), 3)
        
        # First element is a paragraph
        self.assertIsInstance(elements[0], Paragraph)
        self.assertEqual(elements[0].text, "Introduction:")
        
        # Last element is also a paragraph
        self.assertIsInstance(elements[2], Paragraph)
        self.assertEqual(elements[2].text, "Conclusion")
    
    def test_process_content_plain_text(self):
        """Test processing content as plain text"""
        content = "Test paragraph 1\nTest paragraph 2"
        elements = process_content(content, self.doc_width, self.normal_style, is_html=False)
        
        # Should have 2 paragraphs
        self.assertEqual(len(elements), 2)
        self.assertIsInstance(elements[0], Paragraph)
        self.assertIsInstance(elements[1], Paragraph)
    
    @patch('pdf_utils.BeautifulSoup')
    @patch('pdf_utils.process_html_table')
    def test_process_content_html(self, mock_process_table, mock_bs):
        """Test processing content as HTML"""
        # Create a mock soup with a paragraph and table
        mock_soup = MagicMock()
        mock_p = MagicMock()
        mock_p.name = 'p'
        mock_p.get_text.return_value = "Test paragraph"
        
        mock_table = MagicMock()
        mock_table.name = 'table'
        
        mock_soup.body.children = [mock_p, mock_table]
        mock_bs.return_value = mock_soup
        
        # Mock the table processing function
        mock_process_table.return_value = [Table([['']])]
        
        # Process HTML content
        elements = process_content("<p>Test paragraph</p><table></table>", 
                                 self.doc_width, self.normal_style, is_html=True)
        
        # Should have processed both elements (paragraph and table)
        self.assertTrue(mock_process_table.called)
        self.assertGreater(len(elements), 0)
    
    def test_empty_content(self):
        """Test handling of empty content"""
        # Empty string
        self.assertEqual(len(process_content("", self.doc_width, self.normal_style)), 0)
        
        # Whitespace only
        self.assertEqual(len(process_content("   ", self.doc_width, self.normal_style)), 0)
        
        # None value
        self.assertEqual(len(process_content(None, self.doc_width, self.normal_style)), 0)
    
    @patch('pdf_utils.normalize_text')
    @patch('pdf_utils.decode_html_entities')
    def test_process_html_content_simple(self, mock_decode, mock_normalize):
        """Test processing simple HTML content"""
        # Mock normalize and decode to return the input
        mock_normalize.side_effect = lambda x: x
        mock_decode.side_effect = lambda x: x
        
        html = "<p>Test paragraph</p>"
        elements = process_html_content(html, self.doc_width, self.normal_style)
        
        # Should have at least one element
        self.assertGreater(len(elements), 0)
        
        # Verify normalization and decoding were called
        mock_normalize.assert_called()
        mock_decode.assert_called()
        
    def test_process_html_content_complex(self):
        """Test processing complex HTML content with tables and lists"""
        html = """
        <div>
          <p>Introduction</p>
          <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Value 1</td><td>Value 2</td></tr>
          </table>
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
        </div>
        """
        
        # This doesn't test the actual output, just that it processes without errors
        elements = process_html_content(html, self.doc_width, self.normal_style)
        self.assertGreater(len(elements), 0)
    
    def test_process_html_content_error_handling(self):
        """Test error handling in HTML processing"""
        # Create a mock that raises an exception
        with patch('pdf_utils.BeautifulSoup') as mock_bs:
            mock_bs.side_effect = Exception("Test exception")
            
            # Should not crash but return a paragraph with the content
            elements = process_html_content("Test content", self.doc_width, self.normal_style)
            self.assertEqual(len(elements), 1)
            self.assertIsInstance(elements[0], Paragraph)

if __name__ == '__main__':
    unittest.main()