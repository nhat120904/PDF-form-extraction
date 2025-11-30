"""
run_chandra_ocr.py
OCR and Form Field Extraction using Chandra model (https://huggingface.co/datalab-to/chandra)
Supports both PDF and Image inputs.
"""

import os
import json
import fitz  # pymupdf
from PIL import Image
import torch
from transformers import AutoModel, AutoProcessor

# Configuration
MODEL_NAME = "datalab-to/chandra"
PDF_PATH = "22 Don de nghi ho tro chi phi hoc tap.pdf"
OUTPUT_JSON = "chandra_form_fields.json"

def pdf_to_images(pdf_path, dpi=150):
    """Convert PDF pages to PIL Images."""
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append((i + 1, img))
    return images

def main():
    print(f"Loading model: {MODEL_NAME}...")
    
    # Force CPU
    device = "cpu"
    print(f"Using device: {device}")
    
    # Load model
    model = AutoModel.from_pretrained(
        MODEL_NAME, 
        trust_remote_code=True,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
        device_map=device  # Force CPU
    )
    
    processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model.eval()
    
    print(f"Processing PDF: {PDF_PATH}")
    pages = pdf_to_images(PDF_PATH)
    
    all_results = []
    
    for page_num, image in pages:
        print(f"\n--- Processing Page {page_num} ---")
        
        try:
            # Prepare input using processor
            # Chandra uses a specific prompt format
            prompt = "Extract the text content from this document image, preserving the layout."
            
            # Process image
            inputs = processor(
                images=image,
                text=prompt,
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(device) if hasattr(v, 'to') else v for k, v in inputs.items()}
            
            print("Generating (this may take several minutes on CPU)...")
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    do_sample=False
                )
            
            # Decode
            result_text = processor.decode(outputs[0], skip_special_tokens=True)
            
            print(f"Result (first 500 chars):\n{result_text[:500]}...")
            
            all_results.append({
                "page": page_num,
                "text": result_text
            })
                
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({
                "page": page_num,
                "error": str(e)
            })
    
    # Save results
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
