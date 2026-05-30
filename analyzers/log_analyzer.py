import os
import time
from utils.file_reader import read_file
from ai.ai_engine import ask_ai


def analyze_log(path):
    print(f"\n[FRIDAY AI] ⚙️ Commencing Log Register Audit on: {os.path.basename(path)}", flush=True)
    time.sleep(0.8)
    
    print("[FRIDAY AI] 🔍 Scanning log segments for warnings, errors, and fatal exceptions...", flush=True)
    time.sleep(0.8)
    logs = read_file(path)

    print("[FRIDAY AI] 🧠 Querying neural analyzer to diagnose system issues and recommend fixes...", flush=True)
    time.sleep(0.8)
    print("--- AI Analysis ---\n", flush=True)

    prompt = f"""
Please analyze the logs provided below.
The logs are enclosed in <logs> tags.

Provide the following in your analysis:
- Identify any errors
- Identify any warnings
- Explain the possible root cause of any issues found

<logs>
{logs}
</logs>
"""

    from ai.ai_engine import ask_ai_stream
    return ask_ai_stream(prompt, save_to_memory=False, include_history=False)