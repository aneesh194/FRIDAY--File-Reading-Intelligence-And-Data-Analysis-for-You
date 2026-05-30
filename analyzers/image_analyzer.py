import os
import time
try:
    import cv2
    from PIL import Image
except ImportError:
    pass

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

# Module-level singleton — initialized once, reused for all images
_ocr_instance = None

def _get_ocr():
    """Returns the shared PaddleOCR instance, creating it on first use."""
    global _ocr_instance
    if _ocr_instance is None and PaddleOCR is not None:
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    return _ocr_instance

try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    BLIP_AVAILABLE = True
except ImportError:
    BLIP_AVAILABLE = False

from ai.ai_engine import ask_ai


def extract_ocr_text(file_path):
    """
    Silently extracts OCR text from a single image file using the shared OCR instance.
    Does NOT call the AI or print anything — used for batch processing.
    Returns the extracted text string, or empty string on failure.
    """
    ocr = _get_ocr()
    if ocr is None:
        return "[OCR not available — paddleocr not installed]"
    try:
        result = ocr.ocr(file_path, cls=True)
        if result and result[0]:
            lines = [line[1][0] for line in result[0] if line and len(line) > 1]
            return "\n".join(lines)
        return "[No text detected in this image]"
    except Exception as e:
        return f"[OCR error: {e}]"


def get_blip_caption(file_path):
    if not BLIP_AVAILABLE:
        return "[Local Image Captioning disabled. Transformers/Torch not installed yet.]"
        
    try:
        # Silence HuggingFace and PyTorch warnings/logs
        import logging
        import contextlib
        import gc
        
        logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
        logging.getLogger("transformers").setLevel(logging.ERROR)
        
        # Make sure D: drive is used for cache since C: is out of space
        cache_dir = "models/hf_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load weights dynamically for this request, so it doesn't linger in RAM
        with open(os.devnull, "w") as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                processor = BlipProcessor.from_pretrained(
                    "Salesforce/blip-image-captioning-base",
                    cache_dir=cache_dir
                )
                model = BlipForConditionalGeneration.from_pretrained(
                    "Salesforce/blip-image-captioning-base",
                    cache_dir=cache_dir
                )
            
        raw_image = Image.open(file_path).convert('RGB')
        inputs = processor(raw_image, return_tensors="pt")
        # Generate caption
        out = model.generate(**inputs, max_new_tokens=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        
        # Immediately delete and run garbage collection to free 1.5GB RAM for DeepSeek
        del model
        del processor
        gc.collect()
        
        return caption
    except Exception as e:
        return f"[Failed to generate local caption: {e}]"

def analyze_image(file_path):
    if not os.path.exists(file_path):
        return f"Error: Image file not found at {file_path}"

    if PaddleOCR is None:
        return "Error: paddleocr is not installed. Please install it to use image analysis."

    print(f"\n[FRIDAY AI] 📸 Commencing Image Analysis on: {os.path.basename(file_path)}", flush=True)
    time.sleep(0.8)
    img_info_str = ""
    try:
        # Pillow for basic info
        print("[FRIDAY AI] 🔍 Extracting image dimensions, channels, and brightness...", flush=True)
        time.sleep(0.8)
        pil_img = Image.open(file_path)
        img_info_str = f"Image Size: {pil_img.size}, Mode: {pil_img.mode}, Format: {pil_img.format}\n"
        
        # OpenCV for deep image processing
        cv_img = cv2.imread(file_path)
        if cv_img is not None:
            import numpy as np
            img_info_str += f"OpenCV Shape: {cv_img.shape}\n"
            
            # Analyze brightness
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            img_info_str += f"Average Brightness: {brightness:.2f} (0=Pitch Black, 255=Pure White)\n"
            
            # Analyze colors
            b, g, r = cv2.split(cv_img)
            img_info_str += f"Color Channel Intensities -> Red: {np.mean(r):.2f}, Green: {np.mean(g):.2f}, Blue: {np.mean(b):.2f}\n"
            
    except Exception as e:
        img_info_str = f"Note: Pillow/OpenCV analysis failed ({e})\n"

    try:
        # Initialize OCR
        print("[FRIDAY AI] 👁️ Running Optical Character Recognition (OCR) to extract text...", flush=True)
        time.sleep(0.8)
        ocr = _get_ocr()
        result = ocr.ocr(file_path, cls=True) if ocr else None

        extracted_text = []
        if result and result[0]:
            for line in result[0]:
                extracted_text.append(line[1][0])

        full_text = "\n".join(extracted_text)
        
        # Run BLIP Image Captioning to describe what the AI "sees"
        print("[FRIDAY AI] 🤖 Running BLIP neural model to describe visual scene details...", flush=True)
        time.sleep(0.8)
        image_description = get_blip_caption(file_path)
        
        if not full_text.strip():
            full_text = "[No text found]"
            prompt = f"""
Please analyze this image based on its technical metadata and visual scene description.
No readable text was found in the image.

<metadata>
{img_info_str}
</metadata>

<visual_scene_description>
{image_description}
</visual_scene_description>

Provide a detailed summary of what is visually depicted in this image based on the visual scene description, and explain its format and qualities based on the metadata.
"""
        else:
            prompt = f"""
Please analyze and summarize the following text which was extracted from an image via OCR.
Also, review the visual scene description and technical properties of the image.

<metadata>
{img_info_str}
</metadata>

<visual_scene_description>
{image_description}
</visual_scene_description>

<text>
{full_text}
</text>

Provide a structured summary of the key text information, and briefly note what the image visually depicts.
"""
        # Print standard metadata reports immediately
        print("--- Image Processing Metadata ---")
        print(img_info_str)
        print("--- Extracted Text ---")
        print(full_text)
        print("--- Visual Scene Description ---")
        print(image_description)
        print("\n--- AI Analysis ---\n", flush=True)
        
        from ai.ai_engine import ask_ai_stream
        return ask_ai_stream(prompt, save_to_memory=False, include_history=False)

    except Exception as e:
        return f"Error during image analysis: {str(e)}"
