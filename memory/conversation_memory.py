import os
import json

HISTORY_FILE = "reports/conversation_history.json"
MAX_TURNS = 10

def add_message(role, content):
    """
    Appends a new interaction turn to the sliding conversation window.
    """
    history = get_history()
    
    # Clean role to match standard instructs
    history.append({
        "role": role,
        "content": content
    })
    
    # Maintain last 10 messages (5 user-assistant turns)
    if len(history) > MAX_TURNS:
        history = history[-MAX_TURNS:]
        
    save_history(history)


def get_history():
    """
    Retrieves the current session history list of messages,
    automatically converting legacy formats.
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            return []
            
        normalized = []
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # If it's the legacy {"user": "...", "ai": "..."} format, expand it into two messages
            if "user" in item and "ai" in item:
                normalized.append({"role": "user", "content": item["user"]})
                normalized.append({"role": "assistant", "content": item["ai"]})
            # If it's the standard {"role": "...", "content": "..."} format
            elif "role" in item and "content" in item:
                normalized.append(item)
                
        return normalized
    except:
        return []


def save_history(history):
    """
    Saves the session history list back to disk.
    """
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Error writing conversation history: {e}]")


def get_instruct_context(model_family="deepseek"):
    """
    Formats the history as a clean, native prompt context block for the specific model.
    """
    history = get_history()
    if not history:
        return ""
        
    context_str = ""
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        
        if model_family == "llama3":
            if role == "user":
                context_str += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                context_str += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        elif model_family == "mistral":
            if role == "user":
                context_str += f"[INST] {content} [/INST]"
            elif role == "assistant":
                context_str += f"{content}</s>"
        elif model_family == "phi3":
            if role == "user":
                context_str += f"<|user|>\n{content}<|end|>\n"
            elif role == "assistant":
                context_str += f"<|assistant|>\n{content}<|end|>\n"
        elif model_family == "qwen":
            if role == "user":
                context_str += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                context_str += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        else: # deepseek
            if role == "user":
                context_str += f"### Instruction:\n{content}\n\n"
            elif role == "assistant":
                context_str += f"### Response:\n{content}\n\n"
                
    # If the last message was a user message, we need to append the assistant start tag
    if history and history[-1]["role"] == "user":
        if model_family == "llama3":
            context_str += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        elif model_family == "phi3":
            context_str += "<|assistant|>\n"
        elif model_family == "qwen":
            context_str += "<|im_start|>assistant\n"
        elif model_family == "deepseek":
            context_str += "### Response:\n"

    return context_str


def clear_history():
    """
    Clears the sliding conversation history.
    """
    save_history([])
