import unittest
import os
import json
from extract_structure import extract_fields
from fill_pdf import fill_pdf

class TestPDFProcessing(unittest.TestCase):
    def test_extract_and_fill(self):
        pdf_path = "Mau dang ky cong diem_Final_141016.pdf"
        # pdf_path = "2023- ĐƠN CHUYỂN CHƯƠNG TRÌNH ĐÀO TẠO.docx.pdf"
        # pdf_path = "22 Don de nghi ho tro chi phi hoc tap.pdf"
        json_path = "form_structure.json"
        output_path = "filled_form.pdf"
        
        # 1. Test Extraction
        fields = extract_fields(pdf_path)
        self.assertTrue(len(fields) > 0, "Should extract at least one field")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(fields, f, indent=2, ensure_ascii=False)
            
        # 2. Test Filling
        sample_data = {
#   "field_dot_1": "Phòng Công tác Sinh viên – Trường Đại học XYZ",
#   "field_gap_4": "Nguyễn Văn A",
#   "field_gap_5": "Kinh",
#   "field_gap_6": "01/01/2000",
#   "field_gap_7": "Hà Nội",
#   "field_gap_8": "INT3306 1",
#   "field_gap_9": "K66",
#   "field_gap_10": "Công nghệ Thông tin",
#   "field_gap_11": "20200001",
#   "field_dot_2": "Hà Nội",
#   "field_dot_3": "ngày 01 tháng 01 năm 2025",
#   "field_gap_12": "Đã kiểm tra và xác nhận"
# }
  "field_63": "Hà Nội, ngày 01 tháng 01 năm 2025",
  "field_64": "Học kỳ 1",
  "field_65": "2024 - 2025",
  "field_66": "Lớp tín chỉ: INT3306 1",
  "field_67": "Điểm thi hết học phần: 9.0",

  "table_0_r2_c2_p1": "SV001",
  "table_0_r4_c4_p1": "Ảnh chụp minh chứng 1",
  "table_0_r9_c2_p1": "SV009",
  "table_0_r11_c4_p1": "File minh chứng 11",

  "table_0_r2_c3_p1": "Đủ điều kiện",
  "table_0_r4_c5_p1": "Ký tên A",
  "table_0_r7_c1_p1": "Nguyễn Văn A (Row 7)",
  "table_0_r9_c3_p1": "Thi lại",
  "table_0_r11_c5_p1": "Chữ ký cán bộ 11",

  "table_0_r2_c4_p1": "MC 2",
  "table_0_r7_c2_p1": "SV007",
  "table_0_r9_c4_p1": "MC 9",
  "table_0_r2_c5_p1": "Ký tên 2",
  "table_0_r5_c1_p1": "Trần Văn B",

  "table_0_r7_c3_p1": "Đạt",
  "table_0_r9_c5_p1": "Ký tên 9",
  "table_0_r12_c1_p1": "Lê Văn C",

  "table_0_r5_c2_p1": "SV005",
  "table_0_r7_c4_p1": "MC 7",
  "table_0_r12_c2_p1": "SV012",

  "table_0_r3_c1_p1": "Nguyễn Thị D",
  "table_0_r5_c3_p1": "Không đạt",
  "table_0_r7_c5_p1": "CK 7",
  "table_0_r10_c1_p1": "Hoàng Văn E",
  "table_0_r12_c3_p1": "Đạt",

  "table_0_r1_c0_p1": "1",
  "table_0_r3_c2_p1": "SV003",
  "table_0_r5_c4_p1": "MC 5",
  "table_0_r10_c2_p1": "SV010",
  "table_0_r12_c4_p1": "MC 12",

  "table_0_r3_c3_p1": "Đủ điều kiện",
  "table_0_r5_c5_p1": "CK 5",
  "table_0_r8_c1_p1": "Phạm Thị F",
  "table_0_r10_c3_p1": "Không đạt",
  "table_0_r12_c5_p1": "CK 12",

  "table_0_r3_c4_p1": "MC Row 3",
  "table_0_r8_c2_p1": "SV008",
  "table_0_r10_c4_p1": "MC 10",

  "table_0_r3_c5_p1": "CK Row 3",
  "table_0_r6_c1_p1": "Ngô Văn G",
  "table_0_r8_c3_p1": "Thi bù",
  "table_0_r10_c5_p1": "CK 10",
  "table_0_r13_c1_p1": "Vũ Văn H",

  "table_0_r6_c2_p1": "SV006",
  "table_0_r8_c4_p1": "MC 8",
  "table_0_r13_c2_p1": "SV013",

  "table_0_r1_c5_p1": "CK 1",
  "table_0_r4_c1_p1": "Nguyễn Văn I",
  "table_0_r6_c3_p1": "Đạt",
  "table_0_r8_c5_p1": "CK 8",
  "table_0_r11_c1_p1": "Sinh viên 11",
  "table_0_r13_c3_p1": "Thi lại",

  "table_0_r4_c2_p1": "SV004",
  "table_0_r6_c4_p1": "MC 6",
  "table_0_r11_c2_p1": "SV011",
  "table_0_r13_c4_p1": "MC 13",

  "table_0_r2_c1_p1": "Row 2 Name",
  "table_0_r4_c3_p1": "Thi lại",
  "table_0_r6_c5_p1": "CK 6",
  "table_0_r9_c1_p1": "Student 9",
  "table_0_r11_c3_p1": "Đủ điều kiện",
  "table_0_r13_c5_p1": "CK cuối"
        }

        fill_pdf(pdf_path, json_path, output_path, sample_data)
        
        self.assertTrue(os.path.exists(output_path), "Output PDF should be created")
        
        # # Cleanup
        # if os.path.exists(json_path): os.remove(json_path)
        # if os.path.exists(output_path): os.remove(output_path)

if __name__ == '__main__':
    unittest.main()

