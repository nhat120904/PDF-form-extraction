import fitz
import json
import os

def fill_pdf(pdf_path, json_structure_path, output_path, data_dict):
    with open(json_structure_path, 'r', encoding='utf-8') as f:
        fields = json.load(f)
    
    doc = fitz.open(pdf_path)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    if not os.path.exists(font_path):
         font_path = "/System/Library/Fonts/Helvetica.ttc"
    
    for field in fields:
        field_id = field['id']
        page_num = field['page'] - 1
        bbox = field['bbox']
        field_type = field.get('type', 'text_line')
        
        # Auto-fill logic for test (if ID not in data_dict but label matches)
        text_to_insert = data_dict.get(field_id)
        if not text_to_insert:
             # Fallback: Try to find by label for testing
             for key, val in data_dict.items():
                 if key in field['label']:
                     text_to_insert = val
                     break
        
        if text_to_insert:
            page = doc[page_num]
            
            if field_type == 'table_cell':
                # Insert into cell
                rect = fitz.Rect(bbox['x'], bbox['y'], bbox['x'] + bbox['width'], bbox['y'] + bbox['height'])
                try:
                     page.insert_textbox(
                        rect, 
                        text_to_insert, 
                        fontsize=11, 
                        fontname="arial", 
                        fontfile=font_path,
                        color=(0, 0, 1)
                    )
                except: pass
            else: 
                # Text line (dots)
                fontsize = bbox['height'] * 0.8
                baseline_y = bbox['y'] + bbox['height'] - 2
                point = fitz.Point(bbox['x'], baseline_y)
                try:
                    page.insert_text(
                        point, 
                        text_to_insert, 
                        fontsize=fontsize, 
                        fontname="arial", 
                        fontfile=font_path,
                        color=(0, 0, 1) 
                    )
                except: pass

    doc.save(output_path)
    print(f"Saved filled PDF to {output_path}")

if __name__ == "__main__":
    pdf_path = "Mau dang ky cong diem_Final_141016.pdf"
    json_path = "form_structure.json"
    output_path = "filled_form.pdf"
    
    sample_data = {
        "Mã SV mới": "123456",
        "Lớp": "K60 KDQT",
        "Chuyên ngành": "Kinh doanh quốc tế",
        "field_1": "Nguyễn Văn A"
    }
    
    fill_pdf(pdf_path, json_path, output_path, sample_data)

