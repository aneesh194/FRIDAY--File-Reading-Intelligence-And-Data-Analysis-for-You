import os
import sys
import time

# Auto-inject FileMind virtual environment site-packages to ensure all dependencies load perfectly
venv_site = r"d:\FileMind\venv\Lib\site-packages"
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from utils.clawd_client import send_clawd_status

# Force standard output to use UTF-8 encoding for full emoji/unicode support on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Enable virtual terminal processing (ANSI escape codes) natively on Windows Command Prompt
if os.name == 'nt':
    try:
        os.system('')
    except:
        pass

try:
    import torch
except ImportError:
    pass

from utils.intent_router import detect_intent
from ai.ai_engine import ask_ai, ask_ai_stream
from analyzers.code_analyzer import analyze_code_file
from analyzers.document_analyzer import analyze_document
from analyzers.log_analyzer import analyze_log
from analyzers.image_analyzer import analyze_image
from utils.report_generator import save_report


def load_last_analysis():
    import json
    if os.path.exists("reports/active_project.json"):
        try:
            with open("reports/active_project.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"type": None, "path": None, "content": None}


def save_last_analysis(analysis):
    import json
    try:
        os.makedirs("reports", exist_ok=True)
        with open("reports/active_project.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=4, ensure_ascii=False)
    except:
        pass


def print_friday_banner(frame_idx=0, mood="idle"):
    from utils.buddy import render_buddy_frame, HAS_CLAWD2
    
    left_lines = [
        "  Welcome to FRIDAY",
        "   ███████╗██████╗ ██╗██████╗  █████╗ ██╗  ██╗",
        "   ██╔════╝██╔══██╗██║██╔══██╗██╔══██╗╚██╗██╔╝",
        "   █████╗  ██████╔╝██║██║  ██║███████║ ╚███╔╝ ",
        "   ██╔══╝  ██╔══██╗██║██║  ██║██╔══██║  ██╔╝  ",
        "   ██║     ██║  ██║██║██████╔╝██║  ██║  ██║   ",
        "   ╚═╝     ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝  ╚═╝   ",
        "  Command-line interface",
        "",
        "  Friday can write, test and debug code",
        "  right from your terminal. Describe a",
        "  task to get started or enter ? for help.",
        "  Friday uses AI, check for mistakes."
    ]
    
    pet_lines = []
    if HAS_CLAWD2:
        from utils.buddy import set_buddy_mood
        set_buddy_mood(mood)
        pet_lines = render_buddy_frame("clawd-2", frame_idx)
    else:
        pet_lines = [
            "                    ",
            "                    ",
            "                    ",
            "      (\\_._/)       ",
            "     / (o o) \\\\     ",
            "    (   -=-   )     ",
            "     `-\"---`-\"      ",
            "                    ",
            "                    ",
            "                    ",
            "                    "
        ]
        
    pet_lines = ["                    "] + pet_lines + ["                    "]
    
    banner = []
    banner.append("┌" + "─" * 78 + "┐")
    for i in range(13):
        left_text = left_lines[i]
        left_padded = f"{left_text:<52}"
        pet_part = pet_lines[i]
        banner.append(f"│ {left_padded} {pet_part} │")
    banner.append("└" + "─" * 78 + "┘")
    
    for line in banner:
        sys.stdout.write(line + "\n")
    sys.stdout.flush()


def animate_startup_banner():
    from utils.buddy import set_buddy_mood, HAS_CLAWD2
    frames_count = 12
    first_render = True
    for f in range(frames_count):
        if not first_render:
            sys.stdout.write("\033[15A")
        else:
            first_render = False
        print_friday_banner(frame_idx=f, mood="happy")
        time.sleep(0.15)
    # Render final frame with idle pet so the static banner looks calm
    sys.stdout.write("\033[15A")
    print_friday_banner(frame_idx=0, mood="idle")
    if HAS_CLAWD2:
        set_buddy_mood("idle")


def animate_exit_buddy():
    from utils.buddy import set_buddy_mood, HAS_CLAWD2, render_buddy_frame
    if not HAS_CLAWD2:
        print("\nExiting FRIDAY AI. Goodbye!")
        return
        
    print("\n[FRIDAY AI] 💤 Putting companion to sleep...")
    set_buddy_mood("sleeping")
    first_render = True
    for f in range(8):
        lines = render_buddy_frame("clawd-2", f)
        block = []
        block.append("[FRIDAY Companion] (State: SLEEPING)")
        for line in lines:
            block.append(f"  {line}")
        block.append("  System: Offline. Goodbye!")
        
        output_str = ""
        if not first_render:
            output_str += f"\033[{len(block)}A"
        else:
            first_render = False
            
        for l in block:
            output_str += f"\033[K{l}\n"
            
        sys.stdout.write(output_str)
        sys.stdout.flush()
        time.sleep(0.15)


def main():
    # Start the local API server in a background daemon thread so it is always active
    try:
        import threading
        from ai.api_server import start_server
        server_thread = threading.Thread(
            target=lambda: start_server(port=8000), 
            daemon=True
        )
        server_thread.start()
        time.sleep(0.05)
    except Exception:
        pass
    
    # Reset conversation memory at startup for a fresh, lightning-fast session
    from memory.conversation_memory import clear_history
    clear_history()
    
    last_analysis = load_last_analysis()
    
    # Render the animated startup banner
    animate_startup_banner()
        
    print("\nFRIDAY: Hi! How can I help you today?")

    while True:
        try:
            user_input = input("\nAsk: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting FRIDAY AI. Goodbye!")
            break

        if user_input.lower() == "exit":
            break

        intent = detect_intent(user_input)

        # Clear conversation history if user is switching analysis to a new target
        if intent["type"] in ("code", "document", "log", "image", "folder"):
            target_path = intent.get("path")
            if target_path and target_path != last_analysis.get("path"):
                from memory.conversation_memory import clear_history
                clear_history()
                print("\n[FRIDAY AI] 🔄 Switching context to a new analysis target. Conversation history reset to maximize speed and clarity.", flush=True)

        try:

            # GENERAL AI
            if intent["type"] == "general":
                q_lower = user_input.lower().strip().rstrip("!.,?")
                
                # Friendly small talk, greetings, feelings, and identity patterns
                friendly_patterns = [
                    "how are you", "how is it going", "how's it going", "how are things", "how do you feel",
                    "are you ok", "are you okay", "how are you doing", "what's up", "whats up", "sup",
                    "who are you", "what are you", "what is your name", "who is your creator", "who made you",
                    "are you my friend", "do you like me", "do you have feelings", "are you real", "are you happy",
                    "do you love me", "are you a robot", "tell me a joke", "say something funny", "make me laugh",
                    "thank you", "thanks", "greetings", "hi friday", "hello friday", "good job", "awesome",
                    "how's your day", "how is your day", "you are cool", "you are great", "love you",
                    "are you feeling", "nice to meet you", "pleasure to meet you"
                ]
                greetings = {"hi", "hello", "hey", "sup", "yo", "hiya", "howdy", "good morning", "good evening", "good afternoon"}
                
                is_friendly = any(p in q_lower for p in friendly_patterns) or q_lower in greetings
                
                if is_friendly:
                    print("\nFRIDAY: ", end="", flush=True)
                    ask_ai_stream(user_input, workspace_context=None, save_to_memory=True, show_spinner=True, friendly_chat=True)
                else:
                    print("\nFRIDAY: ", end="", flush=True)
                    # Only pass workspace context for follow-up questions about an active analysis.
                    # This prevents polluting general AI queries (e.g. "what is AI") with
                    # irrelevant workspace data that confuses the model in the 4096-token window.
                    workspace_ctx = None
                    if last_analysis and last_analysis.get("content"):
                        follow_up_terms = [
                            "explain", "detail", "summary", "summarize", "report",
                            "bill", "invoice", "receipt", "document", "file", "folder",
                            "code", "result", "finding", "analysis", "analyze", "scan",
                            "previous", "above", "earlier", "more about", "tell me more",
                            "elaborate", "expand", "what was", "how much", "total",
                        ]
                        if any(term in q_lower for term in follow_up_terms):
                            workspace_ctx = last_analysis.get("content")
                    ask_ai_stream(user_input, workspace_context=workspace_ctx, save_to_memory=True, show_spinner=True, friendly_chat=False)

            # EXPLICIT REPORT GENERATION
            elif intent["type"] == "report":
                path_to_report = intent.get("path") or last_analysis.get("path")
                
                if path_to_report is not None:
                    target_type = "folder" if os.path.isdir(path_to_report) else "file"
                    
                    # Update active project state tracking if a new path was provided directly
                    if path_to_report != last_analysis.get("path"):
                        last_analysis = {
                            "type": target_type,
                            "path": path_to_report,
                            "content": ""
                        }
                        save_last_analysis(last_analysis)
                        
                    # Prompt the user for save location
                    print("\n[Save Report] Enter the directory path where you want to save the report.")
                    user_dir = input("Save Path (Press Enter for default 'reports/'): ").strip()
                    save_dir = user_dir if user_dir else "reports"
                    
                    print("\n[Save Report] Choose report format:")
                    print("  1) Markdown (.md) [Default]")
                    print("  2) Text (.txt)")
                    print("  3) HTML (.html)")
                    print("  4) Word Document (.docx)")
                    format_choice = input("Format (1/2/3/4): ").strip()
                    
                    fmt = "md"
                    if format_choice == "2":
                        fmt = "txt"
                    elif format_choice == "3":
                        fmt = "html"
                    elif format_choice == "4":
                        fmt = "docx"
                    
                    if target_type == "folder":
                        from report_generator.report_generator import generate_project_report
                        generate_project_report(path_to_report, save_directory=save_dir, fmt=fmt)
                    else:
                        save_report(target_type, path_to_report, last_analysis.get("content", ""), save_directory=save_dir, fmt=fmt)
                else:
                    print("\n[No analysis has been performed yet in this session. Please analyze a file, folder, or image first!]")

            # SAVE CODE / GENERATE FILE
            elif intent["type"] == "save_code":
                from memory.conversation_memory import get_history
                import re
                
                history = get_history()
                last_ai_response = None
                for msg in reversed(history):
                    if msg["role"] == "assistant":
                        last_ai_response = msg["content"]
                        break
                        
                if not last_ai_response:
                    print("\n[Save Code] No recent AI responses found to extract code from.")
                    continue
                    
                # Match markdown code blocks: ```language\n code \n```
                code_blocks = re.findall(r'```([a-zA-Z0-9+#-]+)?\n(.*?)\n```', last_ai_response, re.DOTALL)
                
                if not code_blocks:
                    print("\n[Save Code] No code blocks found in the most recent AI response.")
                    continue
                
                print(f"\n[Save Code] Found {len(code_blocks)} code block(s).")
                for i, (lang, code) in enumerate(code_blocks, 1):
                    lang = lang.strip().lower() if lang else "txt"
                    
                    # Map common markdown languages to file extensions
                    ext_map = {
                        "python": "py", "py": "py",
                        "javascript": "js", "js": "js", "jsx": "jsx",
                        "typescript": "ts", "ts": "ts", "tsx": "tsx",
                        "html": "html",
                        "css": "css", "scss": "scss",
                        "json": "json",
                        "c++": "cpp", "cpp": "cpp",
                        "c": "c",
                        "java": "java",
                        "rust": "rs", "rs": "rs",
                        "go": "go",
                        "bash": "sh", "sh": "sh",
                        "xml": "xml",
                        "sql": "sql",
                        "md": "md", "markdown": "md"
                    }
                    ext = ext_map.get(lang, "txt")
                    if not ext.startswith("."): ext = "." + ext
                    
                    preview = code[:80].replace("\n", " ").strip()
                    print(f"\n--- Code Block {i} (Detected Language: {lang} -> {ext}) ---")
                    print(f"Preview: {preview}...")
                    
                    user_path = input(f"Enter file path to save Block {i} (or press Enter to skip): ").strip()
                    
                    if user_path:
                        # Append the extension if user didn't provide one
                        if not any(user_path.lower().endswith(e) for e in ext_map.values()) and "." not in os.path.basename(user_path):
                            user_path += ext
                            
                        try:
                            os.makedirs(os.path.dirname(os.path.abspath(user_path)), exist_ok=True)
                            with open(user_path, "w", encoding="utf-8") as f:
                                f.write(code.strip() + "\n")
                            print(f"[Success] Code saved to {user_path}")
                        except Exception as e:
                            print(f"[Error] Failed to save file: {e}")

            # CODE ANALYSIS
            elif intent["type"] == "code":
                print("\nCode Analysis:\n", flush=True)
                explanation = analyze_code_file(intent["path"])
                last_analysis = {
                    "type": "code",
                    "path": intent["path"],
                    "content": explanation
                }
                save_last_analysis(last_analysis)
                print("\n[Tip: Type 'generate report' to save this analysis as a report file!]")

            # DOCUMENT ANALYSIS
            elif intent["type"] == "document":
                print("\nDocument Analysis:\n", flush=True)
                explanation = analyze_document(intent["path"])
                last_analysis = {
                    "type": "document",
                    "path": intent["path"],
                    "content": explanation
                }
                save_last_analysis(last_analysis)
                print("\n[Tip: Type 'generate report' to save this analysis as a report file!]")

            # LOG ANALYSIS
            elif intent["type"] == "log":
                print("\nLog Analysis:\n", flush=True)
                explanation = analyze_log(intent["path"])
                last_analysis = {
                    "type": "log",
                    "path": intent["path"],
                    "content": explanation
                }
                save_last_analysis(last_analysis)
                print("\n[Tip: Type 'generate report' to save this analysis as a report file!]")

            # IMAGE ANALYSIS
            elif intent["type"] == "image":
                print("\nImage Analysis:\n", flush=True)
                explanation = analyze_image(intent["path"])
                last_analysis = {
                    "type": "image",
                    "path": intent["path"],
                    "content": explanation
                }
                save_last_analysis(last_analysis)
                print("\n[Tip: Type 'generate report' to save this analysis as a report file!]")

            # FOLDER ANALYSIS
            elif intent["type"] == "folder":
                try:
                    from utils.buddy import set_buddy_mood
                    set_buddy_mood("typing")  # Show 'waiting' animation during analysis prep
                except Exception:
                    pass
                print(f"\n[FRIDAY AI] 📂 Commencing Workspace Audit on: {intent['path']}", flush=True)
                time.sleep(0.8)
                print("[FRIDAY AI] 🔍 Scanning folder directory structure recursively...", flush=True)
                time.sleep(0.8)
                files_found = []
                ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", ".next"}

                for root, dirs, files in os.walk(intent["path"]):
                    dirs[:] = [d for d in dirs if d not in ignore_dirs]
                    for f in files:
                        files_found.append(os.path.join(root, f))

                print(f"Found {len(files_found)} file(s).")

                # ── Detect image-only / image-heavy folders ──────────────────────
                IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif")
                CODE_EXTS  = (".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".json", ".md")

                image_files = [f for f in files_found if f.lower().endswith(IMAGE_EXTS)]
                code_files  = [f for f in files_found if f.lower().endswith(CODE_EXTS)]

                if image_files and len(image_files) >= len(code_files):
                    # ── IMAGE FOLDER: batch OCR all images → one combined AI summary ──
                    from analyzers.image_analyzer import extract_ocr_text
                    print(f"[FRIDAY AI] 🖼️  Detected image folder — extracting text from {len(image_files)} image(s)...", flush=True)

                    combined_text = ""
                    for idx, img_path in enumerate(image_files[:10], 1):  # cap at 10
                        fname = os.path.basename(img_path)
                        print(f"[FRIDAY AI] 🔍 OCR scanning ({idx}/{min(len(image_files),10)}): {fname}", flush=True)
                        ocr_text = extract_ocr_text(img_path)
                        char_count = len(ocr_text.strip())
                        print(f"             ✓ Extracted {char_count} characters", flush=True)
                        combined_text += f"\n\n--- Document {idx}: {fname} ---\n"
                        combined_text += ocr_text if ocr_text.strip() else "[No text found in this image]"

                    if len(image_files) > 10:
                        combined_text += f"\n\n[Note: {len(image_files) - 10} more image(s) not processed.]"

                    print("[FRIDAY AI] 🧠 Sending all extracted data to AI for unified summary...", flush=True)
                    time.sleep(0.5)

                    # Guard: warn user if no content was extracted
                    total_chars = len(combined_text.replace("[No text found in this image]", "").strip())
                    if total_chars < 50:
                        print("\n[Warning] Very little text was extracted from the images.")
                        print("[Tip] Make sure paddleocr is installed: pip install paddleocr")
                        print(f"[Debug] Combined text preview:\n{combined_text[:500]}\n")
                    
                    print("\nSummary:\n", flush=True)

                    prompt = f"""
Below are text records extracted from {min(len(image_files), 10)} files in a folder.
Each record is separated by a --- Document --- header.

Your task:
1. For each document: identify what type it is (invoice, receipt, hotel bill, etc.), who issued it, and the key amounts.
2. List the financial breakdown for each: subtotal, tax, discount, and final total.
3. Calculate and show a GRAND TOTAL across all documents.
4. Note any important observations.

Use a clean table format for the financial summary.

<records>
{combined_text}
</records>
"""
                    explanation = ask_ai_stream(prompt, save_to_memory=False, include_history=False)

                else:
                    # ── CODE / MIXED FOLDER: read code snippets ───────────────────
                    print("[FRIDAY AI] ⚡ Prioritizing and loading active module contents...", flush=True)
                    time.sleep(0.8)

                    # Prioritize key entry-point files or main module codes
                    PRIORITY_NAMES = {"app.py", "main.py", "index.js", "App.js", "App.tsx", "server.js", "package.json", "schema.sql", "routes.py", "models.py", "frontend_logic.js", "src/app.jsx", "src/app.js"}
                    
                    def sort_priority(filepath):
                        fname = os.path.basename(filepath).lower()
                        # prioritize files by name or sub-path matches
                        if fname in PRIORITY_NAMES or any(pn in filepath.replace("\\", "/").lower() for pn in ["src/app.jsx", "src/app.js", "frontend/package.json"]):
                            return (0, fname)
                        elif fname.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".sql")):
                            return (1, fname)
                        return (2, fname)
                    
                    sorted_files = sorted(files_found, key=sort_priority)

                    # ── Extract technical metadata via regex for a super structured summary ──
                    routes_found = []
                    tables_found = []
                    tech_stack = []

                    import re
                    # Scan for tech stack markers
                    for fp in files_found:
                        fn = os.path.basename(fp).lower()
                        if fn == "package.json":
                            tech_stack.append("Node.js/npm dependencies present")
                        elif fn == "requirements.txt":
                            tech_stack.append("Python dependencies present")
                        elif fn == "jobconnect.db" or fn.endswith(".db"):
                            tech_stack.append("SQLite database file detected")
                        elif fn == "schema.sql":
                            tech_stack.append("SQL Schema setup file detected")
                        elif "vite.config" in fn:
                            tech_stack.append("Vite build system active")
                        elif "react" in fn:
                            tech_stack.append("React frontend active")

                    # Scan files for routes and database schemas
                    for file_path in sorted_files:
                        if file_path.lower().endswith(CODE_EXTS) or file_path.lower().endswith(".sql"):
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content_str = f.read(50000) # read first 50KB for regex parsing
                                    
                                    # Find Flask routes
                                    if file_path.endswith(".py"):
                                        flask_routes = re.findall(r"@app\.route\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*(\[[^\]]+\]))?", content_str)
                                        for r_path, r_methods in flask_routes:
                                            methods_clean = r_methods.replace("'", "").replace('"', '').strip() if r_methods else "GET"
                                            routes_found.append(f"- `[Flask]` {methods_clean} `{r_path}`")
                                            
                                    # Find Express / JS routes
                                    elif file_path.endswith((".js", ".jsx", ".ts", ".tsx")):
                                        js_routes = re.findall(r"(?:app|router)\.(get|post|put|delete)\(\s*['\"]([^'\"]+)['\"]", content_str)
                                        for method, r_path in js_routes:
                                            routes_found.append(f"- `[Express/JS]` {method.upper()} `{r_path}`")
                                            
                                    # Find SQL Tables
                                    if file_path.endswith(".sql") or "schema" in file_path.lower():
                                        sql_tables = re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_0-9]+)", content_str, re.IGNORECASE)
                                        for tbl in sql_tables:
                                            if tbl.lower() not in [t.lower() for t in tables_found]:
                                                tables_found.append(tbl)
                            except:
                                pass

                    tech_summary = "\n".join(f"- {ts}" for ts in set(tech_stack)) if tech_stack else "- Standard files folder"
                    routes_summary = "\n".join(routes_found[:25]) if routes_found else "- No explicit routes detected via regex scan"
                    if len(routes_found) > 25:
                        routes_summary += f"\n- ... and {len(routes_found) - 25} more routes."
                        
                    tables_summary = ", ".join(f"`{t}`" for t in tables_found) if tables_found else "No database tables detected via schema scan"

                    file_contents = ""
                    files_read = 0
                    for file_path in sorted_files:
                        if files_read >= 15:
                            break
                        if file_path.lower().endswith(CODE_EXTS):
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    fname = os.path.basename(file_path).lower()
                                    is_priority = (fname in PRIORITY_NAMES or 
                                                   any(pn in file_path.replace("\\", "/").lower() for pn in ["src/app.jsx", "src/app.js", "frontend/package.json"]))
                                    line_limit = 600 if is_priority else 150
                                    
                                    lines = [f.readline() for _ in range(line_limit)]
                                    content = "".join([l for l in lines if l])
                                    if content.strip():
                                        rel_path = os.path.relpath(file_path, intent["path"])
                                        file_contents += f"\n--- File: {rel_path} ---\n{content}\n"
                                        files_read += 1
                            except:
                                pass

                    rel_files = [os.path.relpath(f, intent["path"]) for f in files_found]
                    folder_summary  = f"Folder: {intent['path']}\n"
                    folder_summary += f"Total files found: {len(files_found)}\n\nFull Directory Tree Index:\n"
                    folder_summary += "\n".join(f"- {rf}" for rf in rel_files[:80])
                    if len(rel_files) > 80:
                        folder_summary += f"\n- ... and {len(rel_files) - 80} more files."

                    if not file_contents.strip():
                        file_contents = "[No readable code or text files found in this folder. Only binary or media files present.]"

                    prompt = f"""
Analyze the provided codebase and files folder to explain the architecture, tech stack, and logic:
1. **Primary Project Purpose**: What this system accomplishes.
2. **Main Architecture & Design Patterns**: Map out the components (e.g. backend, database, client side).
3. **Core Database Schema & Data Models**: Identify and explain the database tables: {tables_summary}
4. **Key API Endpoints Table**: Discuss the routing and APIs:
{routes_summary}
5. **Detailed File Map & Logic Flow**: Provide a breakdown of what the key files are used for and how data flows through them. Explain the core functions, authentication, session management, and business logic inside the code files.

Keep the tone highly professional, precise, and educational. Format with clear Markdown headings, lists, and tables.

<tech_stack>
{tech_summary}
</tech_stack>

<folder_structure>
{folder_summary}
</folder_structure>

<file_contents>
{file_contents}
</file_contents>
"""
                    print("[FRIDAY AI] 🧠 Sending workspace structures to local neural model...", flush=True)
                    time.sleep(0.8)
                    print("\nFolder Analysis:\n", flush=True)
                    explanation = ask_ai_stream(prompt, save_to_memory=False, include_history=False)

                last_analysis = {
                    "type": "folder",
                    "path": intent["path"],
                    "content": explanation
                }
                save_last_analysis(last_analysis)
                print("\n[Tip: Type 'generate report' to save this analysis as a report file!]")

            else:
                print("Could not understand request.")

        except KeyboardInterrupt:
            print("\n\n[Operation cancelled. Returning to main menu...]")
        except Exception as e:
            print("Error:", e)

    try:
        animate_exit_buddy()
    except Exception as e:
        print("\nExiting FRIDAY AI. Goodbye!")


if __name__ == "__main__":
    main()