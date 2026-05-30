import os
from PIL import Image, ImageDraw, ImageFont

def create_test_files():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(base_dir, "uploads")
    
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    # 1. Create a test log file
    log_path = os.path.join(uploads_dir, "server.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("""2026-05-17 10:00:01 INFO Server started normally.
2026-05-17 10:05:22 WARNING High memory usage detected.
2026-05-17 10:15:30 ERROR Database connection failed. Timeout.
2026-05-17 10:16:00 CRITICAL Service crashed.""")
    print(f"Created log file: {log_path}")

    # 2. Create a test python script
    code_path = os.path.join(uploads_dir, "sample_script.py")
    with open(code_path, "w", encoding="utf-8") as f:
        f.write("""def calculate_total(prices, tax_rate):
    # Calculates total price including tax
    total = sum(prices)
    return total + (total * tax_rate)

print(calculate_total([10.5, 20.0, 5.0], 0.05))
""")
    print(f"Created code file: {code_path}")

    # 3. Create a test document text file (PDF requires external library to generate)
    doc_path = os.path.join(uploads_dir, "meeting_notes.txt")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("""Project Kickoff Meeting
Date: May 17, 2026
Attendees: Alice, Bob, Charlie

Key Decisions:
- We will use Python for the backend.
- The UI will be built with React.
- Deployment will be on AWS.

Action Items:
- Alice to set up the repository.
- Bob to draft the database schema.""")
    print(f"Created document file: {doc_path}")

    # 4. Create a test image using Pillow
    img_path = os.path.join(uploads_dir, "invoice.png")
    try:
        img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        # Using default font
        d.text((10,10), "INVOICE #12345", fill=(0,0,0))
        d.text((10,40), "Item: Web Development Services", fill=(0,0,0))
        d.text((10,70), "Total Amount: $5,000.00", fill=(0,0,0))
        d.text((10,100), "Thank you for your business!", fill=(0,0,0))
        img.save(img_path)
        print(f"Created image file: {img_path}")
    except Exception as e:
        print(f"Could not create image file. Ensure Pillow is installed. Error: {e}")

if __name__ == "__main__":
    create_test_files()
