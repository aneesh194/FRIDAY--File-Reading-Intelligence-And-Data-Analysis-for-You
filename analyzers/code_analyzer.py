import ast
import time
from utils.file_reader import read_file
from ai.ai_engine import ask_ai


def analyze_code_file(path):
    print(f"\n[FRIDAY AI] 📂 Reading code file: {path}...", flush=True)
    time.sleep(0.8)
    code = read_file(path)
    
    ast_info = ""
    if path.lower().endswith(".py"):
        try:
            print("[FRIDAY AI] ⚙️ Scanning Abstract Syntax Tree (AST) for class/function symbols...", flush=True)
            time.sleep(0.8)
            tree = ast.parse(code)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            
            ast_info = f"\n\nAST Parsing Results (Python):\n- Classes: {classes}\n- Functions: {functions}"
        except Exception as e:
            ast_info = f"\n\nAST Parsing Error: Could not parse python syntax. {e}"
    if ast_info:
        print(ast_info)
    
    print("[FRIDAY AI] 🧠 Contacting local neural network for deep code insights...", flush=True)
    time.sleep(0.8)
    print("--- AI Analysis ---\n", flush=True)
    
    prompt = f"""
Please analyze the code provided below.
The code is enclosed in <code> tags.

Provide the following in your analysis:
- The purpose of the code
- Important functions and their roles
- Any possible issues, bugs, or improvements

<code>
{code}
{ast_info}
</code>
"""

    from ai.ai_engine import ask_ai_stream
    return ask_ai_stream(prompt, save_to_memory=False, include_history=False)