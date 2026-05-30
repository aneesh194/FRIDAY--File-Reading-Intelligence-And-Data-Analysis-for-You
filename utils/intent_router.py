import os


def detect_intent(text):
    text_lower = text.lower()
    
    report_keywords = ["generate report", "give report", "save report", "create report", "make report", "write report", "export report"]
    if any(kw in text_lower for kw in report_keywords) or text_lower.strip() == "report":
        path = extract_path(text)
        return {
            "type": "report",
            "path": path
        }
        
    save_code_keywords = ["generate file", "save code", "create file", "export code", "write code to file"]
    if any(kw in text_lower for kw in save_code_keywords):
        return {
            "type": "save_code"
        }
        
    path = extract_path(text)
    
    if path:
        if os.path.isdir(path):
            return {
                "type": "folder",
                "path": path
            }
            
        # Detect exact file intent based on the actual path extension
        path_lower = path.lower()
        if path_lower.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".json", ".css", ".cpp", ".c", ".h", ".java", ".go", ".rs")):
            return {
                "type": "code",
                "path": path
            }
        elif path_lower.endswith((".txt", ".pdf", ".md", ".docx", ".csv")):
            return {
                "type": "document",
                "path": path
            }
        elif path_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
            return {
                "type": "image",
                "path": path
            }
        elif path_lower.endswith(".log") or "log" in path_lower:
            return {
                "type": "log",
                "path": path
            }

    else:
        return {
            "type": "general"
        }


def extract_path(text):
    # Try the entire string first (cleaning quotes)
    clean_text = text.strip().strip("\"'")
    if os.path.exists(clean_text):
        return clean_text

    # Extract longest contiguous substring of words that actually exists on disk
    # This solves the spaces in paths (e.g. "D:\Error Explainer") problem completely!
    words = text.split()
    n = len(words)
    longest_path = None
    
    for length in range(n, 0, -1):
        for i in range(n - length + 1):
            possible_sub = " ".join(words[i:i+length]).strip().strip("\"'")
            if os.path.exists(possible_sub):
                # Avoid tiny words like "a", "d" unless they are valid short drives or full inputs
                if len(possible_sub) > 2 or possible_sub in (".", "..") or (len(possible_sub) == 2 and possible_sub.endswith(":")):
                    if longest_path is None or len(possible_sub) > len(longest_path):
                        longest_path = possible_sub
                        
    if longest_path:
        return longest_path

    # Try extracting path after common action verbs (including both analyze / analyse)
    text_lower = text.lower()
    prefixes = [
        "analyze ", "analyse ", "check ", "read ", "explain ", 
        "analyze this ", "analyse this ", "explain this ", "check this ",
        "scan ", "scan this "
    ]
    
    for prefix in prefixes:
        if text_lower.startswith(prefix):
            possible_path = text[len(prefix):].strip().strip("\"'")
            if os.path.exists(possible_path):
                return possible_path

    return None