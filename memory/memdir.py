import os
import json
import re
from typing import Dict, Any, List

MEMDIR_PATH = "memory"
PRIVATE_MEMORY_FILE = os.path.join(MEMDIR_PATH, "private_memory.json")
TEAM_MEMORY_FILE = os.path.join(MEMDIR_PATH, "team_memory.json")
MEMORY_MD_FILE = "MEMORY.md"

os.makedirs(MEMDIR_PATH, exist_ok=True)

def load_json_file(file_path: str) -> dict:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_json_file(file_path: str, data: dict) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Warning] Failed to save memory file {file_path}: {e}")

def get_private_memories() -> List[str]:
    data = load_json_file(PRIVATE_MEMORY_FILE)
    return data.get("facts", [])

def add_private_memory(fact: str) -> None:
    data = load_json_file(PRIVATE_MEMORY_FILE)
    facts = data.get("facts", [])
    if fact not in facts:
        facts.append(fact)
        data["facts"] = facts
        save_json_file(PRIVATE_MEMORY_FILE, data)
        update_memory_markdown()

def get_team_memories() -> List[str]:
    data = load_json_file(TEAM_MEMORY_FILE)
    return data.get("learnings", [])

def add_team_memory(learning: str) -> None:
    data = load_json_file(TEAM_MEMORY_FILE)
    learnings = data.get("learnings", [])
    if learning not in learnings:
        learnings.append(learning)
        data["learnings"] = learnings
        save_json_file(TEAM_MEMORY_FILE, data)
        update_memory_markdown()

def update_memory_markdown() -> None:
    """Dynamically compiles private and team memories into a elegant MEMORY.md index."""
    private_facts = get_private_memories()
    team_learnings = get_team_memories()
    
    content = f"""# FRIDAY AI Persistent Memory Index

This file is automatically managed by FRIDAY's memory engine to store user-specific preferences and team-specific codebase quirks.

---

## 👤 Private Memory (User Preferences & Habits)
*This section contains facts specific to your workflow and choices.*

{"" if private_facts else "_No user-specific preferences have been registered yet._"}
"""
    for fact in private_facts:
        content += f"- {fact}\n"
        
    content += f"""
---

## 👥 Team Memory (Codebase & Project Quirks)
*This section tracks project architecture, module definitions, and operational anomalies.*

{"" if team_learnings else "_No project-specific learnings have been registered yet._"}
"""
    for learning in team_learnings:
        content += f"- {learning}\n"
        
    content += """
---
*MEMORY.md — Maintained automatically by FRIDAY Memdir.*
"""
    try:
        with open(MEMORY_MD_FILE, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
    except Exception as e:
        print(f"[Warning] Failed to write MEMORY.md: {e}")

def parse_and_store_memories_from_response(question: str, response: str) -> None:
    """Analyze chat turn to extract key user habits or project facts to memory."""
    # Simple semantic rules for extraction:
    # 1. User preferences: "I prefer", "My favorite", "I am working in", etc.
    q_lower = question.lower()
    
    # Check User preferences (Private)
    pref_match = re.search(r"(?:my favorite|i prefer|i use|i like|remember that i|always use)\s+([^.\n]+)", q_lower)
    if pref_match:
        preference = pref_match.group(1).strip()
        add_private_memory(f"User preference: {preference}")
        
    # Check Workspace context facts (Team)
    if "error" in q_lower or "bug" in q_lower or "fail" in q_lower:
        # If response explains a fix or quirk, add it to team learning
        if "fix" in response.lower() or "because" in response.lower():
            # Try to grab a concise sentence about the issue/solution
            add_team_memory(f"Encountered and solved query about: {question[:80]}...")
    elif "how does" in q_lower or "explain" in q_lower:
        add_team_memory(f"Explored architecture component: {question[:80]}...")
