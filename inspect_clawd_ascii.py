from PIL import Image
import os
import sys

def preview_clawd_ascii():
    img_path = 'd:/Project FRIDAY/clawd-2/spritesheet.webp'
    if not os.path.exists(img_path):
        print("Error: spritesheet.webp not found!")
        return

    img = Image.open(img_path).convert("RGBA")
    
    # Let's crop frame (row 0, col 0)
    # Cell size is 192 x 208
    cell_w, cell_h = 192, 208
    x_start = 0 * cell_w
    y_start = 0 * cell_h
    frame = img.crop((x_start, y_start, x_start + cell_w, y_start + cell_h))
    
    # Downsample to terminal friendly size
    # 24 columns wide, 11 rows tall (maintaining 192x208 aspect ratio closely in characters)
    target_w = 26
    target_h = 11
    resized = frame.resize((target_w, target_h), Image.Resampling.NEAREST)
    
    # ASCII chars
    ramp = "M#W$@o+:-. "
    
    pixels = resized.load()
    print("--- ASCII Frame Row 0, Col 0 ---")
    for y in range(target_h):
        line = ""
        for x in range(target_w):
            r, g, b, a = pixels[x, y]
            if a < 128:
                line += " "
            else:
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                idx = int((lum / 255.0) * (len(ramp) - 1))
                line += ramp[idx]
        print(line)

if __name__ == "__main__":
    preview_clawd_ascii()
