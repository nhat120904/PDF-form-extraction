import os
import fitz  # pymupdf
from PIL import Image
import torch
from transformers import AutoModel, AutoTokenizer, TextStreamer
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode

# Configuration
MODEL_NAME = "5CD-AI/Vintern-1B-v3_5"
PDF_PATH = "phiếu điều chỉnh điểm.pdf"
MAX_NUM_TILES = 1 # Use 1 for fastest CPU inference

# --- Image Preprocessing (Standard) ---
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height
    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])
    target_aspect_ratio = find_closest_aspect_ratio(aspect_ratio, target_ratios, orig_width, orig_height, image_size)
    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]
    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images

def load_image(image, input_size=448, max_num=12):
    image = image.convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = [transform(image) for image in images]
    pixel_values = torch.stack(pixel_values)
    return pixel_values

def pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
        break 
    return images

def main():
    # FORCE CPU for reliability on Mac (avoiding MPS float16 issues with this model)
    device = "cpu"
    dtype = torch.float32
    print(f"Using device: {device}")

    print("Loading model...")
    try:
        model = AutoModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            use_flash_attn=False,
        ).eval().to(device)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True, use_fast=False)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    print(f"Processing PDF: {PDF_PATH}")
    images = pdf_to_images(PDF_PATH)
    
    for i, image in enumerate(images):
        print(f"\n--- Page {i+1} Inference ---")
        
        pixel_values = load_image(image, max_num=MAX_NUM_TILES).to(dtype).to(device)
        
        question = '<image>\nHãy trích xuất các trường thông tin cần điền trong biểu mẫu này dưới dạng JSON. Chỉ bao gồm các trường trống cần điền.'
        
        print("Generating on CPU (please wait, this may take 1-2 minutes)...")
        
        try:
            response, _ = model.chat(
                tokenizer, 
                pixel_values, 
                question, 
                dict(max_new_tokens=512, do_sample=False),
                history=None, 
                return_history=True
            )
            print(f"\nResult:\n{response}")
            
        except Exception as e:
            print(f"\nInference error: {e}")

if __name__ == "__main__":
    main()
