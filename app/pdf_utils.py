"""
PDF generation and content processing utilities for programa PDF files.
"""
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListItem, ListFlowable
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from bs4 import BeautifulSoup
import re
from unicode_utils import normalize_text, UNICODE_REPLACEMENTS, decode_html_entities

# Table style for HTML content
TABLE_STYLE = TableStyle([
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

def process_content(content, doc_width, style, is_html=False):
    """Process content text into paragraphs, handling HTML and bullet points"""
    elementos = []
    
    if not content or not content.strip():
        return elementos
    
    # Clean up Unicode characters that might appear as squares
    content = normalize_unicode(content)

    # Handle HTML content properly with tables
    if is_html:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Process all elements in order to maintain document structure
        # Instead of processing all tables and then text, we'll process elements in order
        for element in soup.body.children if soup.body else soup.children:
            if isinstance(element, str):
                # It's a text node
                text = element.strip()
                if text:
                    # Process Unicode in text nodes
                    text = normalize_text(text)
                    # Decode HTML entities
                    text = decode_html_entities(text)
                    # Process bullet points and regular paragraphs
                    elementos.extend(process_plain_text(text, style))
            elif element.name == 'table':
                # Process table - use specialized handler
                table_elements = process_html_table(element, doc_width, style)
                elementos.extend(table_elements)
                elementos.append(Spacer(1, 0.1*inch))
            elif element.name == 'p':
                # Process paragraphs directly
                paragraph_text = element.get_text().strip()
                if paragraph_text:
                    # Process Unicode in paragraphs
                    paragraph_text = normalize_text(paragraph_text)
                    # Decode HTML entities
                    paragraph_text = decode_html_entities(paragraph_text)
                    elementos.append(Paragraph(paragraph_text, style))
            elif element.name == 'div':
                # Process div containers (which might contain tables)
                for child in element.children:
                    if isinstance(child, str):
                        text = child.strip()
                        if text:
                            text = normalize_text(text)
                            text = decode_html_entities(text)
                            elementos.extend(process_plain_text(text, style))
                    elif child.name == 'table':
                        table_elements = process_html_table(child, doc_width, style)
                        elementos.extend(table_elements)
                        elementos.append(Spacer(1, 0.1*inch))
                    elif child.name == 'p':
                        paragraph_text = child.get_text().strip()
                        if paragraph_text:
                            paragraph_text = normalize_text(paragraph_text)
                            paragraph_text = decode_html_entities(paragraph_text)
                            elementos.append(Paragraph(paragraph_text, style))
            elif element.name in ['ul', 'ol']:
                # Process lists directly
                list_items = []
                for li in element.find_all('li'):
                    item_text = li.get_text().strip()
                    # Process Unicode in list items
                    item_text = normalize_text(item_text)
                    # Decode HTML entities
                    item_text = decode_html_entities(item_text)
                    list_items.append(ListItem(Paragraph(item_text, style)))
                
                if list_items:
                    elementos.append(ListFlowable(
                        list_items,
                        bulletType='1' if element.name == 'ol' else 'bullet',
                        leftIndent=20,
                        spaceBefore=6,
                        spaceAfter=6
                    ))

        return elementos

    # If not HTML or no tables found, continue with normal processing
    # Get text with preserved newlines
    if is_html:
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text('\n', strip=True)
        # Decode HTML entities
        text = decode_html_entities(text)
    else:
        text = content

    # Process plain text content (with or without bullet points)
    return process_plain_text(text, style)

def process_html_table(table_element, doc_width, style):
    """
    Process an HTML table into a ReportLab Table, properly handling colspans and rowspans.
    This function is specifically designed to handle complex tables with merged cells.
    """
    # Initialize data structure to track the grid and cell spans
    rows = table_element.find_all('tr', recursive=True)
    
    # Calculate max columns by examining colspans in all rows
    max_cols = 0
    for row in rows:
        cols = 0
        for cell in row.find_all(['td', 'th']):
            colspan = int(cell.get('colspan', 1))
            cols += colspan
        max_cols = max(max_cols, cols)
    
    # Safety check - if no valid columns or rows found, return empty paragraph
    if max_cols == 0 or not rows:
        return [Paragraph("", style)]
    
    # Initialize table grid with None (empty cells)
    grid = [[None for _ in range(max_cols)] for _ in range(len(rows))]
    
    # First pass: populate grid with cell content and track spans
    for row_idx, row in enumerate(rows):
        col_idx = 0
        
        # Skip columns that are already occupied by rowspans
        while col_idx < max_cols and grid[row_idx][col_idx] is not None:
            col_idx += 1
        
        for cell in row.find_all(['td', 'th']):
            # Skip if we've gone beyond our grid (safety check)
            if col_idx >= max_cols:
                break
                
            # Get cell attributes
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            # Process cell content
            cell_text = cell.get_text().strip()
            cell_text = normalize_text(cell_text)
            cell_text = decode_html_entities(cell_text)
            
            # Check for bold text
            is_bold = False
            if cell.find(['b', 'strong']):
                is_bold = True
            elif 'style' in cell.attrs:
                style_text = cell['style'].lower()
                if 'font-weight:700' in style_text or 'font-weight:bold' in style_text or 'font-weight: 700' in style_text:
                    is_bold = True
            
            # Check for background color (we'll use this for styling)
            bg_color = None
            if 'style' in cell.attrs:
                style_text = cell['style'].lower()
                bg_match = re.search(r'background-color\s*:\s*(#[a-f0-9]{6}|#[a-f0-9]{3}|rgba?\([^)]+\)|[a-z]+)', style_text)
                if bg_match:
                    color_text = bg_match.group(1)
                    # Convert basic colors to ReportLab colors
                    if color_text == '#999999' or color_text == '#999':
                        bg_color = colors.Color(0.6, 0.6, 0.6)  # Equivalent to #999999
                    elif color_text == '#b2b2b2':
                        bg_color = colors.Color(0.7, 0.7, 0.7)  # Equivalent to #b2b2b2
                    elif color_text.startswith('#'):
                        try:
                            # Handle hex colors
                            if len(color_text) == 4:  # #RGB format
                                r = int(color_text[1] + color_text[1], 16) / 255
                                g = int(color_text[2] + color_text[2], 16) / 255
                                b = int(color_text[3] + color_text[3], 16) / 255
                            else:  # #RRGGBB format
                                r = int(color_text[1:3], 16) / 255
                                g = int(color_text[3:5], 16) / 255
                                b = int(color_text[5:7], 16) / 255
                            bg_color = colors.Color(r, g, b)
                        except ValueError:
                            # If color parsing fails, default to light grey
                            bg_color = colors.lightgrey
            
            # Create cell style based on formatting
            cell_style = ParagraphStyle(
                'TableCell',
                parent=style,
                fontSize=9,
                leading=10,
                wordWrap='CJK',
                alignment=1,  # Center alignment
                fontName='Helvetica-Bold' if is_bold else 'Helvetica'
            )
            
            # Create cell content as Paragraph
            cell_content = Paragraph(cell_text, cell_style)
            
            # Store the cell in the grid with its formatting information
            grid[row_idx][col_idx] = {
                'content': cell_content,
                'colspan': colspan,
                'rowspan': rowspan,
                'bg_color': bg_color,
                'is_bold': is_bold
            }
            
            # Mark spanned cells with references to the main cell
            for r in range(rowspan):
                for c in range(colspan):
                    if r == 0 and c == 0:
                        continue  # Skip the main cell which we just filled
                    
                    # Check if within grid bounds
                    if (row_idx + r < len(grid)) and (col_idx + c < max_cols):
                        grid[row_idx + r][col_idx + c] = 'SPAN'  # Mark as a spanned cell
            
            # Move to next available column
            col_idx += colspan
            
            # Skip any columns that are already filled
            while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                col_idx += 1
    
    # Convert grid to data format for ReportLab Table
    table_data = []
    for row in grid:
        table_row = []
        for cell in row:
            if cell is None:
                # Empty cell
                table_row.append('')
            elif cell == 'SPAN':
                # This position is part of a span, will be handled by ReportLab's span mechanism
                table_row.append('')
            else:
                # Regular cell with content
                table_row.append(cell['content'])
        table_data.append(table_row)
    
    # Calculate column widths with safety check and minimum width
    min_col_width = 20  # minimum width in points
    # Ensure we don't divide by zero and maintain minimum width
    if max_cols > 0:
        col_width = max(min_col_width, doc_width / max_cols)
    else:
        col_width = min_col_width
    col_widths = [col_width] * max_cols
    
    # Create the table
    table = Table(table_data, colWidths=col_widths)
    
    # Prepare table style commands
    style_commands = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    
    # Process spans and background colors
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if isinstance(cell, dict):  # Only process actual cells, not spans or None
                # Handle background color
                if cell['bg_color']:
                    span_end_row = row_idx + cell['rowspan'] - 1
                    span_end_col = col_idx + cell['colspan'] - 1
                    style_commands.append(
                        ('BACKGROUND', (col_idx, row_idx), (span_end_col, span_end_row), cell['bg_color'])
                    )
                
                # Handle colspan/rowspan
                if cell['colspan'] > 1 or cell['rowspan'] > 1:
                    span_end_row = row_idx + cell['rowspan'] - 1
                    span_end_col = col_idx + cell['colspan'] - 1
                    style_commands.append(
                        ('SPAN', (col_idx, row_idx), (span_end_col, span_end_row))
                    )
                
                # Apply bold font if needed
                if cell['is_bold']:
                    span_end_row = row_idx + cell['rowspan'] - 1
                    span_end_col = col_idx + cell['colspan'] - 1
                    style_commands.append(
                        ('FONTNAME', (col_idx, row_idx), (span_end_col, span_end_row), 'Helvetica-Bold')
                    )
    
    # Apply all styles to the table
    table.setStyle(TableStyle(style_commands))
    
    return [table]

def normalize_unicode(text):
    """Normalize Unicode characters to improve rendering"""
    # Use the centralized normalize_text function from unicode_utils
    return normalize_text(text)

def process_plain_text(text, style):
    """Process plain text, preserving bullet points, Unicode characters and their original order"""
    elementos = []
    
    # Decode HTML entities
    text = decode_html_entities(text)
    
    # Expanded list of bullet characters to detect
    bullet_chars = [
        '\u0095',  # Bullet (Windows-1252)
        '\u0096',  # En dash (Windows-1252)
        '\u0097',  # Em dash (Windows-1252)
        '\u2022',  # Bullet
        '\u2023',  # Triangular bullet
        '\u25E6',  # White bullet
        '\u2043',  # Hyphen bullet
        '\u2219',  # Bullet operator
        '\u25D8',  # Inverse bullet
        '\u25CB',  # White circle
        '\u25CF',  # Black circle
        '\u25AA',  # Black small square
        '\u25AB',  # White small square
        '\u25A0',  # Black square
        '\u25A1',  # White square
        '\u2212',  # Minus sign
        '\u002D',  # Hyphen-minus
        '\u2014',  # Em dash
        '\u2013',  # En dash
        '\u2010',  # Hyphen
        '\u2026',  # Ellipsis
        '•', '–', '-', '*', '>'  # Common bullet characters
    ]
    
    # Check if text contains line breaks
    if '\n' in text:
        paragraphs = text.split('\n')
    else:
        paragraphs = [text]
    
    current_list_items = []
    in_list = False
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Check if this paragraph is a bullet point
        is_bullet = any(para.startswith(bullet) for bullet in bullet_chars)
        
        if is_bullet:
            # If we weren't in a list before, start one now
            if not in_list:
                in_list = True
            
            # Remove the bullet character and add to list items
            for bullet in bullet_chars:
                if para.startswith(bullet):
                    # Keep the item text as is after removing the bullet
                    item_text = para[len(bullet):].strip()
                    current_list_items.append(ListItem(Paragraph(item_text, style)))
                    break
        else:
            # If we were in a list, finalize it before continuing
            if in_list and current_list_items:
                elementos.append(ListFlowable(
                    current_list_items,
                    bulletType='bullet',
                    start='•',
                    bulletFontName='Helvetica',
                    bulletFontSize=10,
                    leftIndent=20,
                    bulletOffsetY=2
                ))
                current_list_items = []
                in_list = False
            
            # Add regular paragraph preserving all Unicode characters
            elementos.append(Paragraph(para, style))
    
    # Don't forget to add any remaining list items
    if in_list and current_list_items:
        elementos.append(ListFlowable(
            current_list_items,
            bulletType='bullet',
            start='•',
            bulletFontName='Helvetica',
            bulletFontSize=10,
            leftIndent=20,
            bulletOffsetY=2
        ))
    
    return elementos

def process_complex_html_table(table_element, doc_width, style):
    """
    Process complex HTML tables with colspan, rowspan, and background colors
    """
    # First, analyze the table structure
    rows = table_element.find_all('tr', recursive=True)
    
    # Calculate the maximum number of columns by examining all rows
    max_cols = 0
    for row in rows:
        cols = 0
        for cell in row.find_all(['td', 'th'], recursive=False):
            colspan = int(cell.get('colspan', 1))
            cols += colspan
        max_cols = max(max_cols, cols)
    
    # Safety check - if no valid columns found, return empty table with minimal formatting
    if max_cols == 0:
        return [Paragraph("", style)]
    
    # Initialize the table data structure with empty cells
    table_data = []
    row_spans = {}  # Track cells with rowspan
    
    # Process each row
    for row_idx, row in enumerate(rows):
        row_data = [''] * max_cols  # Initialize with empty cells
        col_idx = 0
        
        # Handle continued rowspans from previous rows
        for span_col, (content, remaining_rows) in list(row_spans.items()):
            row_data[span_col] = content if row_idx == 0 else ''
            
            if remaining_rows > 1:
                # Update for the next row
                row_spans[span_col] = (content, remaining_rows - 1)
            else:
                # Remove completed span
                del row_spans[span_col]
        
        # Process cells in the current row
        for cell in row.find_all(['td', 'th'], recursive=False):
            # Skip positions already filled by row spans
            while col_idx < len(row_data) and row_data[col_idx] != '':
                col_idx += 1
            
            if col_idx >= len(row_data):
                break  # Safety check
            
            # Get cell attributes
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            
            # Process cell content
            cell_text = cell.get_text().strip()
            cell_text = normalize_text(cell_text)
            cell_text = decode_html_entities(cell_text)
            
            # Determine if cell content is bold
            is_bold = bool(cell.find('b') or cell.find('strong'))
            if 'style' in cell.attrs:
                style_attr = cell['style'].lower()
                if 'font-weight:700' in style_attr or 'font-weight:bold' in style_attr:
                    is_bold = True
            
            # Create cell style
            cell_style = ParagraphStyle(
                'TableCell',
                parent=style,
                fontSize=9,
                leading=10,
                wordWrap='CJK',
                alignment=1,  # Center
                fontName='Helvetica-Bold' if is_bold else 'Helvetica'
            )
            
            # Create cell content
            cell_content = Paragraph(cell_text, cell_style)
            
            # Place the cell in the current position
            row_data[col_idx] = cell_content
            
            # Handle colspan - mark positions as used
            for i in range(1, colspan):
                if col_idx + i < len(row_data):
                    row_data[col_idx + i] = ''
            
            # Handle rowspan - store for future rows
            if rowspan > 1:
                for r in range(1, rowspan):
                    if row_idx + r not in row_spans:
                        row_spans[row_idx + r] = {}
                    for c in range(colspan):
                        if col_idx + c < len(row_data):
                            row_spans[row_idx + r][col_idx + c] = (cell_content, rowspan - 1)
            
            # Move to the next position, accounting for colspan
            col_idx += colspan
        
        # Add the processed row to the table data
        table_data.append(row_data)
    
    # Create ReportLab table with safety check for max_cols
    # Set column widths proportionally with minimum width
    min_col_width = 20  # minimum width in points to prevent too narrow columns
    # Ensure we don't divide by zero and maintain minimum width
    col_width = max(min_col_width, doc_width / max_cols if max_cols > 0 else min_col_width)
    col_widths = [col_width] * max_cols
    
    # Create table with appropriate styling
    table = Table(table_data, colWidths=col_widths)
    
    # Apply styling
    table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    
    # Apply the style to the table
    table.setStyle(TableStyle(table_style))
    
    return [table]

def process_html_content(content, doc_width, normal_style):
    # Handle empty content
    if not content:
        return []
    
    # First, replace problematic Unicode characters with their HTML equivalents
    # Use the centralized unicode replacements from unicode_utils
    content = normalize_text(content)
    content = decode_html_entities(content)
            
    try:
        soup = BeautifulSoup(content, 'html.parser')
        elements = []
        
        # Process all top-level elements in their original order to maintain the structure
        for element in soup.children:
            if isinstance(element, str):
                # Handle pure text nodes (like titles between tables)
                text = element.strip()
                if text:
                    # Process Unicode in pure text nodes
                    text = normalize_text(text)
                    elements.append(Paragraph(text, normal_style))
            elif element.name == 'table':
                # Process table using our complex table processor
                table_elements = process_complex_html_table(element, doc_width, normal_style)
                elements.extend(table_elements)
                elements.append(Spacer(1, 0.1*inch))
            elif element.name in ['ul', 'ol']:
                # Process lists
                list_items = []
                for li in element.find_all('li'):
                    text = li.get_text().strip()
                    # Process Unicode in list items
                    text = normalize_text(text)
                    list_items.append(ListItem(Paragraph(text, normal_style)))
                
                list_flowable = ListFlowable(
                    list_items,
                    bulletType='1' if element.name == 'ol' else 'bullet',
                    leftIndent=20,
                    spaceBefore=6,
                    spaceAfter=6
                )
                elements.append(list_flowable)
            elif element.name == 'p':
                # Process paragraphs
                text = element.get_text().strip()
                if text:
                    # Process Unicode in paragraphs
                    text = normalize_text(text)
                    elements.append(Paragraph(text, normal_style))
            elif element.name == 'div':
                # Process div which may contain tables or other content
                for child in element.children:
                    if isinstance(child, str):
                        text = child.strip()
                        if text:
                            text = normalize_text(text)
                            elements.append(Paragraph(text, normal_style))
                    elif child.name == 'table':
                        table_elements = process_complex_html_table(child, doc_width, normal_style)
                        elements.extend(table_elements)
                        elements.append(Spacer(1, 0.1*inch))
                    elif child.name == 'p':
                        text = child.get_text().strip()
                        if text:
                            text = normalize_text(text)
                            elements.append(Paragraph(text, normal_style))
            elif element.string and element.string.strip():
                # Process any other elements with text content
                text = element.string.strip()
                if text:
                    # Process Unicode in other elements
                    text = normalize_text(text)
                    elements.append(Paragraph(text, normal_style))
        
        # If no elements were processed but we have content, handle it as plain text
        if not elements and soup.get_text().strip():
            text = soup.get_text().strip()
            # Process Unicode in plain text
            text = normalize_text(text)
            paragraphs = text.split('\n')
            for para in paragraphs:
                if para.strip():
                    elements.append(Paragraph(para.strip(), normal_style))
        
        return elements
    except Exception as e:
        print(f"Error procesando HTML: {str(e)}")
        # In case of any error, try to clean the content and return it as plain text
        content = normalize_text(content)
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

    # Add page number in the bottom right corner
    canvas.setFont('Helvetica', 6)  # Very small font for page number
    canvas.setFillColorRGB(0.5, 0.5, 0.5)  # Grey color for page number
    # Calculate position for right alignment, 2mm from right margin (reduced from 5mm)
    page_num_x = doc.pagesize[0] - doc.rightMargin - 2*mm
    canvas.drawRightString(page_num_x, 5, str(doc.page))

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
    
    # Create document title for metadata
    nombre_materia = programa.get('nombre_materia', 'Programa')
    cod_carrera = programa.get('cod_carrera', '')
    ano_academico = programa.get('ano_academico', '')
    
    # Build a descriptive document title
    doc_title = f"CRUB UNCo - {nombre_materia} {cod_carrera} {ano_academico}"
    
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
        pageCompression=1,   # Compress the PDF
        title=doc_title,     # Add document title
        author="Centro Regional Universitario Bariloche - UNCo",  # Add author
        subject=f"Programa de {nombre_materia} - {ano_academico}",  # Add subject
        creator="Sistema de Programas - CRUB UNCo"  # Add creator
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

    # Create justified style for content
    justified_style = ParagraphStyle(
        'JustifiedContent',
        parent=normal_style,
        alignment=4,  # 4 = Justified
        spaceAfter=6,
        leading=14
    )

    # Initial spacing
    programa_elements.append(Spacer(1, 0.35*inch))

    # Basic program metadata
    ano_academico = programa.get('ano_academico', '')
    programa_elements.append(Paragraph(f"AÑO ACADÉMICO: {ano_academico}", title_style))
    programa_elements.append(Spacer(1, 0.03*inch))

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
            elementos = process_content(content, doc_width, justified_style, is_html=False)
            programa_elements.extend(elementos)
            programa_elements.append(Spacer(1, 0.1*inch))

    # Distribution horaria (HTML content)
    programa_elements.append(Paragraph("DISTRIBUCIÓN HORARIA:", field_style))

    # Hours display (use justified style for descriptive text)
    for label, field in [
        ('Horas teóricas', 'horas_teoricas'),
        ('Horas prácticas', 'horas_practicas'),
        ('Horas teórico-prácticas', 'horas_teoricopracticas')
    ]:
        value = programa.get(field, '')
        if value and str(value).strip():
            extra_text = " (solo para LENB y LBIB)" if field == 'horas_teoricopracticas' else ""
            programa_elements.append(Paragraph(f"{label}: {value}{extra_text}", normal_style))

    # Process HTML content for distribución horaria
    if programa.get('distribucion_horaria'):
        elementos = process_content(programa.get('distribucion_horaria'), doc_width, justified_style, is_html=True)
        programa_elements.extend(elementos)
    programa_elements.append(Spacer(1, 0.1*inch))

    # Process HTML content for cronograma if it exists
    cronograma = programa.get('cronograma_tentativo', '')
    if cronograma and cronograma.strip():
        programa_elements.append(Paragraph("CRONOGRAMA TENTATIVO:", field_style))
        elementos = process_content(cronograma, doc_width, justified_style, is_html=True)
        programa_elements.extend(elementos)

    return programa_elements