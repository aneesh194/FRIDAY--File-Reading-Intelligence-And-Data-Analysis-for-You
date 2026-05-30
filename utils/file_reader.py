import os

def read_file(path):
    ext = os.path.splitext(path)[1].lower()
    
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(path)
            return "\n".join(page.get_text() for page in doc)
        except Exception as e:
            return f"Error reading PDF: {e}"
            
    elif ext in (".xls", ".xlsx"):
        try:
            import pandas as pd
            df = pd.read_excel(path)
            return df.to_string()
        except ImportError:
            return "Error: pandas or openpyxl is not installed. Run `pip install pandas openpyxl` to read Excel files."
        except Exception as e:
            return f"Error reading Excel file: {e}"
            
    elif ext == ".csv":
        try:
            import pandas as pd
            df = pd.read_csv(path)
            return df.to_string()
        except ImportError:
            # Fallback to standard reading
            pass
        except Exception as e:
            return f"Error reading CSV file: {e}"
            
    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(path)
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except ImportError:
            return "Error: python-docx is not installed. Run `pip install python-docx` to read Word files."
        except Exception as e:
            return f"Error reading Word document: {e}"

    # Default text reading
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            # Fallback to latin-1
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return f"Error reading binary/unsupported file: {e}"
    except Exception as e:
        return f"Error reading file: {e}"