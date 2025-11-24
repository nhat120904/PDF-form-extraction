import pdfplumber
import json

def is_dot_char(char):
    return char['text'] in ['.', '…', '_']

def extract_fields(pdf_path):
    fields = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_fields = []
            table_bboxes = []
            
            # 1. Table Extraction (First Pass)
            # We want to know where tables are, but we will be smarter about
            # creating fields inside them.
            tables = page.find_tables()
            for t_idx, table in enumerate(tables):
                table_bboxes.append(table.bbox)
                data = table.extract()
                if not data: continue
                
                header = data[0]
                header = [h.replace('\n', ' ').strip() if h else f"Col_{i}" for i, h in enumerate(header)]
                cols = len(header)
                
                # Map cells to fields IF they are empty
                # If a cell is NOT empty, we might still want to extract fields inside it later (step 2)
                # so we don't just blindly create a 'table_cell' field for everything.
                
                # Use table.rows to ensure correct mapping between data and cells
                if hasattr(table, 'rows'):
                    for r in range(1, len(data)):
                        if r >= len(table.rows): continue
                        row_cells = table.rows[r].cells
                        
                        for c in range(cols):
                            if c >= len(row_cells): continue
                            
                            cell_text = data[r][c]
                            cell_rect = row_cells[c]
                            
                            # If cell is effectively empty, it's a field to be filled
                            if cell_text is None or cell_text.strip() == "":
                                page_fields.append({
                                    "id": f"table_{t_idx}_r{r}_c{c}_p{page_num+1}",
                                    "page": page_num + 1,
                                    "label": f"{header[c]} (Row {r})",
                                    "rect": list(cell_rect),
                                    "type": "table_cell"
                                })

            # 2. Dot Field Extraction (Global)
            chars = page.chars
            current_field_chars = []
            dot_fields = []
            
            for char in chars:
                if is_dot_char(char):
                    if current_field_chars:
                        last_char = current_field_chars[-1]
                        if (char['x0'] - last_char['x1'] < 5) and (abs(char['top'] - last_char['top']) < 5):
                            current_field_chars.append(char)
                        else:
                            bbox = get_field_bbox(current_field_chars)
                            if bbox:
                                dot_fields.append({"rect": bbox})
                            current_field_chars = [char]
                    else:
                        current_field_chars = [char]
                else:
                    if current_field_chars:
                        bbox = get_field_bbox(current_field_chars)
                        if bbox:
                            dot_fields.append({"rect": bbox})
                        current_field_chars = []
            
            if current_field_chars:
                bbox = get_field_bbox(current_field_chars)
                if bbox:
                    dot_fields.append({"rect": bbox})

            # 3. Process Dot Fields
            for df in dot_fields:
                rect = df['rect']
                width = rect[2] - rect[0]
                if width < 15: continue # Ignore noise
                
                # Treat dot fields inside tables as text lines
                page_fields.append({
                    "id": f"field_{len(fields) + len(page_fields) + 1}",
                    "page": page_num + 1,
                    "rect": rect,
                    "type": "text_line" # Even if inside table
                })

            # 4. Label Extraction
            # Sort fields
            page_fields.sort(key=lambda f: (f['rect'][1], f['rect'][0]))
            
            for field in page_fields:
                if field.get('label') and not field['label'].startswith("Col_"): 
                    # Already labeled meaningfully
                    fields.append(format_field(field))
                    continue
                
                # For fields inside tables (dot lines), the label is likely IN the same cell, to the left.
                # Or if it's a table_cell field, the label is the header (already handled).
                
                # Find label for text line
                field_rect = field['rect']
                x0 = field_rect[0]
                y_mid = (field_rect[1] + field_rect[3]) / 2
                
                left_limit = 0
                
                # Look for nearest field on the left
                for other_field in page_fields:
                    if other_field == field: continue
                    other_rect = other_field['rect']
                    other_y_mid = (other_rect[1] + other_rect[3]) / 2
                    
                    if abs(other_y_mid - y_mid) < 10:
                        if other_rect[2] < x0 and other_rect[2] > left_limit:
                            left_limit = other_rect[2]
                
                # Extract text
                label_chars = []
                for char in chars:
                    char_y_mid = (char['top'] + char['bottom']) / 2
                    if abs(char_y_mid - y_mid) < 5: # Vertical align
                        if char['x0'] >= left_limit and char['x1'] <= x0 + 2: # Horizontal range
                            if not is_dot_char(char):
                                label_chars.append(char)
                
                label_chars.sort(key=lambda c: c['x0'])
                label_text = "".join([c['text'] for c in label_chars]).strip()
                
                # Cleanup label
                if label_text.endswith(":"): label_text = label_text[:-1].strip()
                
                if not label_text and field.get('label'):
                    # Keep existing label (e.g. from table header)
                    pass
                else:
                    field['label'] = label_text

                fields.append(format_field(field))

    return fields

def get_field_bbox(field_chars):
    if not field_chars: return None
    return [
        min(c['x0'] for c in field_chars),
        min(c['top'] for c in field_chars),
        max(c['x1'] for c in field_chars),
        max(c['bottom'] for c in field_chars)
    ]

def format_field(field):
    return {
        "id": field['id'],
        "page": field['page'],
        "label": field['label'],
        "type": field.get('type', 'text_line'),
        "bbox": {
            "x": field['rect'][0],
            "y": field['rect'][1],
            "width": field['rect'][2] - field['rect'][0],
            "height": field['rect'][3] - field['rect'][1]
        }
    }

if __name__ == "__main__":
    pdf_path = "Mau dang ky cong diem_Final_141016.pdf"
    fields = extract_fields(pdf_path)
    output_file = 'form_structure.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fields, f, indent=2, ensure_ascii=False)
    print(f"Extracted {len(fields)} fields from {pdf_path} to {output_file}")

