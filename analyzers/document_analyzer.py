import os
import time
import fitz  # PyMuPDF
from utils.file_reader import read_file
from ai.ai_engine import ask_ai


def analyze_document(path):
    print(f"\n[FRIDAY AI] 📝 Commencing Document Analysis on: {os.path.basename(path)}", flush=True)
    time.sleep(0.8)
    
    if path.lower().endswith(".pdf"):
        text = ""
        try:
            print("[FRIDAY AI] 🔍 Parsing PDF document catalog and pages using PyMuPDF...", flush=True)
            time.sleep(0.8)
            doc = fitz.open(path)
            for page in doc:
                text += page.get_text()
        except Exception as e:
            text = f"Error reading PDF: {e}"
    else:
        print("[FRIDAY AI] 🔍 Loading plain-text document contents...", flush=True)
        time.sleep(0.8)
        text = read_file(path)

    print("[FRIDAY AI] 🧠 Querying neural processor for semantic summaries and action items...", flush=True)
    time.sleep(0.8)
    print("--- AI Analysis ---\n", flush=True)

    prompt = f"""
Please analyze the document provided below.
The document content is enclosed in <document> tags.

Provide the following in your analysis:
- A concise summary
- Key points
- Any important action items or information

<document>
{text}
</document>
"""

    from ai.ai_engine import ask_ai_stream
    return ask_ai_stream(prompt, save_to_memory=False, include_history=False)