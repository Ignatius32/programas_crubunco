"""
Unit tests for unicode_utils.py module
"""
import sys
import os
import unittest

# Add app directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from unicode_utils import normalize_text, decode_html_entities, UNICODE_REPLACEMENTS

class TestUnicodeUtils(unittest.TestCase):
    """Test cases for unicode_utils.py functions"""
    
    def test_normalize_text(self):
        """Test Unicode text normalization"""
        # Test with different Unicode characters
        test_cases = [
            # Original text -> Expected result
            ('\u2022 Bullet point', '• Bullet point'),  # Unicode bullet
            ('\u00A0 Non-breaking space', ' Non-breaking space'),  # NBSP
            ('Em\u2014dash', 'Em—dash'),  # Em dash
            ('En\u2013dash', 'En–dash'),  # En dash
            ('Smart "quotes"', 'Smart "quotes"'),  # Smart quotes should stay as is
            ('Normal text', 'Normal text')  # Normal text should not change
        ]
        
        for original, expected in test_cases:
            self.assertEqual(normalize_text(original), expected)
        
        # Test with None input
        self.assertEqual(normalize_text(None), '')
        
        # Test with multiple replacements in same string
        text = 'Bullet\u2022 and dash\u2013 test'
        expected = 'Bullet• and dash– test'
        self.assertEqual(normalize_text(text), expected)
    
    def test_decode_html_entities(self):
        """Test HTML entity decoding"""
        test_cases = [
            # Original text -> Expected result
            ('&lt;tag&gt;', '<tag>'),  # Common HTML entities
            ('&amp;', '&'),  # Ampersand
            ('&quot;quoted text&quot;', '"quoted text"'),  # Quotes
            ('&aacute;', 'á'),  # Accent
            ('&#39;apostrophe&#39;', "'apostrophe'"),  # Numeric entity
            ('&#x27;hex entity&#x27;', "'hex entity'"),  # Hex entity
            ('No entities here', 'No entities here')  # No change needed
        ]
        
        for original, expected in test_cases:
            self.assertEqual(decode_html_entities(original), expected)
            
        # Test with None input
        self.assertEqual(decode_html_entities(None), '')
    
    def test_unicode_replacements_integrity(self):
        """Test that UNICODE_REPLACEMENTS contains expected mappings"""
        # Test a few important mappings
        self.assertIn('\u2022', UNICODE_REPLACEMENTS)  # Bullet
        self.assertIn('\u00A0', UNICODE_REPLACEMENTS)  # NBSP
        self.assertIn('\u2013', UNICODE_REPLACEMENTS)  # En dash
        self.assertIn('\u2014', UNICODE_REPLACEMENTS)  # Em dash
        
        # Check their expected values
        self.assertEqual(UNICODE_REPLACEMENTS['\u2022'], '•')  # Bullet
        self.assertEqual(UNICODE_REPLACEMENTS['\u00A0'], ' ')  # NBSP
        self.assertEqual(UNICODE_REPLACEMENTS['\u2013'], '–')  # En dash
        self.assertEqual(UNICODE_REPLACEMENTS['\u2014'], '—')  # Em dash

if __name__ == '__main__':
    unittest.main()