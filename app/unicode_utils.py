"""
Utility module for handling Unicode character replacements in the application.
Contains a mapping of problematic Unicode characters to their safer replacements.
"""

# Dictionary of Unicode character replacements
UNICODE_REPLACEMENTS = {
    # Latin-1 Supplement characters
    '\u00A0': ' ',      # Non-breaking space
    '\u00AB': '«',      # Left-pointing double angle quotation mark
    '\u00BB': '»',      # Right-pointing double angle quotation mark
    
    # Windows-1252 specific characters
    '\u0080': '€',      # Euro sign
    '\u0082': '‚',      # Single low-9 quotation mark
    '\u0083': 'ƒ',      # Latin small f with hook
    '\u0084': '„',      # Double low-9 quotation mark
    '\u0085': '…',      # Horizontal ellipsis
    '\u0086': '†',      # Dagger
    '\u0087': '‡',      # Double dagger
    '\u0088': 'ˆ',      # Modifier letter circumflex accent
    '\u0089': '‰',      # Per mille sign
    '\u008A': 'Š',      # Latin capital letter S with caron
    '\u008B': '‹',      # Single left-pointing angle quotation
    '\u008C': 'Œ',      # Latin capital ligature OE
    '\u008E': 'Ž',      # Latin capital letter Z with caron
    '\u0091': ''',      # Left single quotation mark
    '\u0092': ''',      # Right single quotation mark
    '\u0093': '"',      # Left double quotation mark
    '\u0094': '"',      # Right double quotation mark
    '\u0095': '•',      # Bullet
    '\u0096': '–',      # En dash
    '\u0097': '—',      # Em dash
    '\u0098': '˜',      # Small tilde
    '\u0099': '™',      # Trade mark sign
    '\u009A': 'š',      # Latin small letter s with caron
    '\u009B': '›',      # Single right-pointing angle quotation
    '\u009C': 'œ',      # Latin small ligature oe
    '\u009E': 'ž',      # Latin small letter z with caron
    '\u009F': 'Ÿ',      # Latin capital letter Y with diaeresis
    
    # General Punctuation
    '\u2010': '-',      # Hyphen
    '\u2011': '-',      # Non-breaking hyphen
    '\u2012': '-',      # Figure dash
    '\u2013': '–',      # En dash
    '\u2014': '—',      # Em dash
    '\u2015': '―',      # Horizontal bar
    '\u2018': ''',      # Left single quotation mark
    '\u2019': ''',      # Right single quotation mark
    '\u201A': '‚',      # Single low-9 quotation mark
    '\u201B': '‛',      # Single high-reversed-9 quotation mark
    '\u201C': '"',      # Left double quotation mark
    '\u201D': '"',      # Right double quotation mark
    '\u201E': '„',      # Double low-9 quotation mark
    '\u201F': '‟',      # Double high-reversed-9 quotation mark
    '\u2020': '†',      # Dagger
    '\u2021': '‡',      # Double dagger
    '\u2022': '•',      # Bullet
    '\u2026': '…',      # Horizontal ellipsis
    '\u2028': ' ',      # Line separator
    '\u2029': ' ',      # Paragraph separator
    '\u2039': '‹',      # Single left-pointing angle quotation
    '\u203A': '›',      # Single right-pointing angle quotation
    '\u2212': '-',      # Minus sign
    
    # Various symbols
    '\u2713': '✓',      # Check mark
    '\u2714': '✔',      # Heavy check mark
    '\u2716': '✖',      # Heavy multiplication X
    '\u2717': '✗',      # Ballot X
    '\u2718': '✘',      # Heavy ballot X
    '\u271A': '✚',      # Heavy Greek cross
    '\u271B': '✛',      # Open center cross
    '\u271C': '✜',      # Heavy open center cross
    
    # BOM character
    '\uFEFF': '',       # Zero width no-break space (BOM)
}

def normalize_text(text):
    """
    Normalize Unicode characters in a text string by replacing problematic characters
    with their appropriate substitutions.
    
    Args:
        text (str): The text to normalize
        
    Returns:
        str: The normalized text with problematic Unicode characters replaced
    """
    if not text:
        return text
        
    # Apply all replacements
    for char, replacement in UNICODE_REPLACEMENTS.items():
        if char in text:
            text = text.replace(char, replacement)
    
    return text