import pdfplumber
import json
import re

def is_dot_char(char):
    return char['text'] in ['.', '…', '_']

def extract_fields(pdf_path):
    fields = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_fields = []
            table_bboxes = []
            
            # --- STRATEGY 1: TABLE EXTRACTION ---
            tables = page.find_tables()
            for t_idx, table in enumerate(tables):
                table_bboxes.append(table.bbox)
                data = table.extract()
                if not data: continue
                
                header = data[0]
                header = [h.replace('\n', ' ').strip() if h else f"Col_{i}" for i, h in enumerate(header)]
                cols = len(header)
                cells = table.cells
                
                if len(cells) == len(data) * cols:
                    for r in range(1, len(data)):
                        for c in range(cols):
                            cell_text = data[r][c]
                            cell_rect = cells[r * cols + c]
                            if cell_text is None or cell_text.strip() == "":
                                page_fields.append({
                                    "id": f"table_{t_idx}_r{r}_c{c}_p{page_num+1}",
                                    "page": page_num + 1,
                                    "label": f"{header[c]} (Row {r})",
                                    "rect": list(cell_rect),
                                    "type": "table_cell"
                                })

            # --- STRATEGY 2: DOT GUIDE EXTRACTION ---
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
                            if bbox: dot_fields.append({"rect": bbox})
                            current_field_chars = [char]
                    else:
                        current_field_chars = [char]
                else:
                    if current_field_chars:
                        bbox = get_field_bbox(current_field_chars)
                        if bbox: dot_fields.append({"rect": bbox})
                        current_field_chars = []
            
            if current_field_chars:
                bbox = get_field_bbox(current_field_chars)
                if bbox: dot_fields.append({"rect": bbox})

            # Add dot fields (filtering small noise)
            for df in dot_fields:
                rect = df['rect']
                if (rect[2] - rect[0]) < 15: continue
                page_fields.append({
                    "id": f"field_dot_{len(fields) + len(page_fields) + 1}",
                    "page": page_num + 1,
                    "rect": rect,
                    "type": "text_line"
                })

            # --- STRATEGY 3: WHITESPACE GAP EXTRACTION (New) ---
            # Only run if we didn't find many dot fields (heuristic to avoid double counting on good forms)
            # Or run it complementary. Let's run it complementary but exclude areas already covered.
            
            # IMPORTANT: Use keep_blank_chars=False to find true gaps
            words = page.extract_words(keep_blank_chars=False)
            # Sort words by Top then Left
            words.sort(key=lambda w: (round(w['top'], 1), w['x0']))
            
            # Group words into lines
            lines = []
            if words:
                current_line = [words[0]]
                for w in words[1:]:
                    last_w = current_line[-1]
                    # Same line threshold: 5px vertical difference
                    if abs(w['top'] - last_w['top']) < 5:
                        current_line.append(w)
                    else:
                        lines.append(current_line)
                        current_line = [w]
                lines.append(current_line)
            
            for line in lines:
                for i, word in enumerate(line):
                    text = word['text']
                    
                    # Check if word looks like a label (ends with colon)
                    # Or common keywords: "Kính gửi", "Họ và tên", "Lớp", "Khoa"
                    # "tên:" is a common ending in split words like "Họ và tên:" -> "tên:"
                    is_label = text.endswith(':') or \
                               text in ["Lớp", "Khoa", "Khóa", "Kính gửi"] or \
                               (i > 0 and line[i-1]['text'] == "Họ" and text == "tên") # Handle "Họ tên" without colon? 
                               # Actually "Họ và tên:" is usually split "Họ", "và", "tên:"
                    
                    if is_label:
                        # Found a potential label end. Look for gap to the right.
                        x_start = word['x1'] + 2 # Start after label
                        y_top = word['top']
                        y_bottom = word['bottom']
                        
                        # Determine end of field
                        x_end = page.width - 50 # Default to end of page minus margin
                        
                        # If there is another word on the same line to the right, stop there
                        if i + 1 < len(line):
                            next_word = line[i+1]
                            # Only treat as gap if significant space > 20px
                            gap = next_word['x0'] - word['x1']
                            if gap > 20: # Threshold 20px
                                x_end = next_word['x0'] - 5
                            else:
                                # Gap too small, probably just next word in sentence
                                # Unless it is the last label?
                                continue
                        
                        # Define bbox
                        gap_rect = [x_start, y_top, x_end, y_bottom]
                        
                        # Check overlap with existing fields (table or dots)
                        overlap = False
                        mid_x, mid_y = (x_start + x_end)/2, (y_top + y_bottom)/2
                        
                        for existing in page_fields:
                            er = existing['rect']
                            # Simple overlap check
                            if (er[0] <= mid_x <= er[2]) and (er[1] <= mid_y <= er[3]):
                                overlap = True
                                break
                        
                        if not overlap:
                            # Construct label from previous words in line
                            # E.g. "Họ", "và", "tên:" -> Label "Họ và tên"
                            label_parts = [word['text']]
                            j = i - 1
                            while j >= 0:
                                prev = line[j]
                                # Check distance between words. If > 30px, assume separate label/field
                                if prev['x1'] < word['x0'] - 40: 
                                    break
                                # If we hit another label-like thing (ends with colon), stop but include it if it's part of this label?
                                # No, labels usually don't contain internal colons.
                                if prev['text'].endswith(':'): 
                                    break
                                
                                label_parts.insert(0, prev['text'])
                                # Move pivot
                                word = prev 
                                j -= 1
                            
                            full_label = " ".join(label_parts).replace(':', '').strip()
                            
                            # Create new field
                            page_fields.append({
                                "id": f"field_gap_{len(fields) + len(page_fields) + 1}",
                                "page": page_num + 1,
                                "label": full_label,
                                "rect": gap_rect,
                                "type": "text_line_gap"
                            })

            # --- FORMATTING & LABELING ---
            page_fields.sort(key=lambda f: (f['rect'][1], f['rect'][0]))
            
            for field in page_fields:
                # If Gap Field, label is already set
                if field.get('label'):
                    fields.append(format_field(field))
                    continue
                
                # For Dot Fields, extract label from left
                field_rect = field['rect']
                x0 = field_rect[0]
                y_mid = (field_rect[1] + field_rect[3]) / 2
                
                left_limit = 0
                for other_field in page_fields:
                    if other_field == field: continue
                    other_rect = other_field['rect']
                    other_y_mid = (other_rect[1] + other_rect[3]) / 2
                    if abs(other_y_mid - y_mid) < 10:
                        if other_rect[2] < x0 and other_rect[2] > left_limit:
                            left_limit = other_rect[2]
                
                # Extract label chars
                label_chars = []
                for char in chars:
                    char_y_mid = (char['top'] + char['bottom']) / 2
                    if abs(char_y_mid - y_mid) < 5:
                        if char['x0'] >= left_limit and char['x1'] <= x0 + 2:
                            if not is_dot_char(char):
                                label_chars.append(char)
                
                label_chars.sort(key=lambda c: c['x0'])
                label_text = "".join([c['text'] for c in label_chars]).strip()
                if label_text.endswith(":"): label_text = label_text[:-1].strip()
                
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
    pdf_path = "22 Don de nghi ho tro chi phi hoc tap.pdf" # Target this file
    output_file = 'form_structure.json'
    
    print(f"Extracting from: {pdf_path}")
    fields = extract_fields(pdf_path)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fields, f, indent=2, ensure_ascii=False)
    print(f"Extracted {len(fields)} fields to {output_file}")
