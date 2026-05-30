import sys
import threading
import time
import os
import warnings

# Suppress all Python warnings from native llama.cpp bindings
warnings.filterwarnings("ignore")

# ── Comprehensive C/Python output suppression ────────────────────────────────
# Redirect Python-level stderr and unraisablehook BEFORE importing llama_cpp
# to fully prevent the four startup warning lines from leaking to the terminal.
_real_stderr = sys.stderr
_real_hook = getattr(sys, 'unraisablehook', None)

class _DevNull:
    """File-like sink that silently discards all writes."""
    def write(self, *a, **kw): pass
    def flush(self, *a, **kw): pass
    def close(self): pass

sys.stderr = _DevNull()
try:
    sys.unraisablehook = lambda *a, **kw: None
except AttributeError:
    pass

from llama_cpp import Llama
from ai.prompts import SYSTEM_PROMPT, FRIENDLY_SYSTEM_PROMPT

# ── Model Configuration ─────────────────────────────────────────────────────
# Change MODEL_PATH to switch models. Supported: Mistral, Llama3, DeepSeek, Phi3, Qwen
MODEL_PATH = "models/DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf"

# Auto-detect model family from filename for correct prompt template
_mp = MODEL_PATH.lower()
if "mistral" in _mp or "mixtral" in _mp:
    MODEL_FAMILY = "mistral"
elif ("llama-3" in _mp or "llama3" in _mp or "meta-llama-3" in _mp
      or "distill-llama" in _mp):       # ← catches DeepSeek-R1-Distill-Llama
    MODEL_FAMILY = "llama3"
elif "phi-3" in _mp or "phi3" in _mp:
    MODEL_FAMILY = "phi3"
elif "qwen" in _mp:
    MODEL_FAMILY = "qwen"
else:
    MODEL_FAMILY = "deepseek"  # default

# Suppress low-level C stdout/stderr and Python warnings during model load
class SuppressOutput:
    def __enter__(self):
        try:
            self.null_fds = [os.open(os.devnull, os.O_RDWR) for _ in range(2)]
            self.save_fds = [os.dup(1), os.dup(2)]
            os.dup2(self.null_fds[0], 1)
            os.dup2(self.null_fds[1], 2)
        except Exception:
            self.null_fds = []
            self.save_fds = []

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.save_fds:
            try:
                os.dup2(self.save_fds[0], 1)
                os.dup2(self.save_fds[1], 2)
                os.close(self.null_fds[0])
                os.close(self.null_fds[1])
                os.close(self.save_fds[0])
                os.close(self.save_fds[1])
            except Exception:
                pass

optimal_threads = max(1, min(4, (os.cpu_count() or 4)))

with SuppressOutput():
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=4096,  # Reduced from 12288 to speed up prompt evaluation by 3x on CPU
        n_threads=optimal_threads,
        verbose=False
    )

# ── Restore stderr after all noisy initialization is complete ──────────────
sys.stderr = _real_stderr
if _real_hook is not None:
    sys.unraisablehook = _real_hook

# Global thread lock for C++ Llama instance safety
llm_lock = threading.Lock()

from memory.conversation_memory import add_message, get_instruct_context
from memory.persistent_memory import store_memory, search_memory
from utils.clawd_client import send_clawd_status


# ── Prompt Builders ─────────────────────────────────────────────────────────

def _get_stop_tokens() -> list:
    """Return the correct EOS / stop tokens for the loaded model family."""
    return {
        "llama3":  ["<|eot_id|>", "<|end_of_text|>"],
        "mistral": ["</s>", "[/INST]"],
        "phi3":    ["<|end|>", "<|endoftext|>"],
        "qwen":    ["<|im_end|>", "<|endoftext|>"],
        "deepseek": ["### Instruction:", "<|EOT|>"],
    }.get(MODEL_FAMILY, ["</s>"])


def _build_prompt(question: str, session_context: str,
                  workspace_block: str, memory_context: str,
                  friendly_chat: bool = False) -> str:
    """
    Assemble the full model prompt using the correct chat template
    for the active MODEL_FAMILY.
    """
    # Load durable persistent memories from memdir
    try:
        from memory.memdir import get_private_memories, get_team_memories
        private_m = get_private_memories()
        team_m = get_team_memories()
        
        memdir_context = ""
        if private_m or team_m:
            memdir_context += "### Durable Persistent Memories:\n"
            if private_m:
                memdir_context += "#### User Preferences:\n"
                for m in private_m:
                    memdir_context += f"- {m}\n"
            if team_m:
                memdir_context += "#### Codebase & Project Notes:\n"
                for m in team_m:
                    memdir_context += f"- {m}\n"
            memdir_context += "\n"
    except Exception:
        memdir_context = ""

    # Combined dynamic context injected after the system prompt
    dynamic = ""
    if memdir_context:
        dynamic += memdir_context
    if memory_context:
        dynamic += memory_context
    if workspace_block:
        dynamic += workspace_block

    sys_prompt = FRIENDLY_SYSTEM_PROMPT if friendly_chat else SYSTEM_PROMPT

    if MODEL_FAMILY == "llama3":
        # ── Llama-3 instruct template (also used by DeepSeek-R1-Distill-Llama) ──
        system_block = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            f"{sys_prompt.strip()}\n\n{dynamic}"
            f"<|eot_id|>"
        )
        if session_context:
            # session_context already contains formatted user/assistant turns and ends with <|start_header_id|>assistant<|end_header_id|>\n\n
            suffix = "" if friendly_chat else "<think>\n"
            return system_block + session_context + suffix
        else:
            suffix = "" if friendly_chat else "<think>\n"
            return (
                system_block
                + f"<|start_header_id|>user<|end_header_id|>\n\n{question}<|eot_id|>"
                + "<|start_header_id|>assistant<|end_header_id|>\n\n" + suffix
            )

    elif MODEL_FAMILY == "mistral":
        sys_part = f"{sys_prompt.strip()}\n\n{dynamic}"
        if session_context:
            return f"<s>[INST] {sys_part} [/INST]" + session_context
        return f"<s>[INST] {sys_part}\n\n{question} [/INST]"

    elif MODEL_FAMILY == "phi3":
        sys_part = f"{sys_prompt.strip()}\n\n{dynamic}"
        if session_context:
            return f"<|system|>\n{sys_part}<|end|>\n" + session_context
        return (
            f"<|system|>\n{sys_part}<|end|>\n"
            f"<|user|>\n{question}<|end|>\n"
            f"<|assistant|>\n"
        )

    elif MODEL_FAMILY == "qwen":
        sys_part = f"{sys_prompt.strip()}\n\n{dynamic}"
        if session_context:
            return f"<|im_start|>system\n{sys_part}<|im_end|>\n" + session_context
        return (
            f"<|im_start|>system\n{sys_part}<|im_end|>\n"
            f"<|im_start|>user\n{question}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    else:  # deepseek / generic instruct
        sys_part = f"{sys_prompt.strip()}\n\n{dynamic}"
        if session_context:
            return f"{sys_part}\n\n" + session_context
        return (
            f"{sys_part}\n\n"
            f"### Instruction:\n{question}\n\n"
            f"### Response:\n"
        )


def _build_truncated_prompt(question: str, session_context: str,
                             workspace_block: str, memory_context: str,
                             friendly_chat: bool = False) -> str:
    """
    Builds the prompt and truncates inputs token-wise if the total tokens exceed
    the context window (minus a buffer for generation).
    """
    try:
        n_ctx_val = llm.n_ctx() if callable(llm.n_ctx) else llm.n_ctx
    except Exception:
        n_ctx_val = 4096

    # Leave a healthy buffer of 800 tokens for the AI response
    max_response_tokens = 800
    max_prompt_len = max(1024, n_ctx_val - max_response_tokens)

    # Build prompt without truncation first
    prompt = _build_prompt(question, session_context, workspace_block, memory_context, friendly_chat)

    try:
        tokens = llm.tokenize(prompt.encode('utf-8'))
        total_tokens = len(tokens)
    except Exception:
        # Fallback if tokenize fails: estimate using 4 chars per token
        total_tokens = len(prompt) // 4

    if total_tokens <= max_prompt_len:
        return prompt

    # Print a clear notice so the user understands why/what context is being trimmed
    sys.stdout.write(f"\n[FRIDAY AI] [Warning] Prompt tokens ({total_tokens}) exceed context limit of {n_ctx_val}.\n")
    sys.stdout.write("[FRIDAY AI] [Notice] Automatically trimming context to fit the model window...\n")
    sys.stdout.flush()

    def get_tokens(text: str) -> list:
        if not text:
            return []
        try:
            return llm.tokenize(text.encode('utf-8'))
        except Exception:
            return []

    # Get token chunks for each dynamic part
    w_tokens = get_tokens(workspace_block)
    q_tokens = get_tokens(question)
    s_tokens = get_tokens(session_context)
    m_tokens = get_tokens(memory_context)

    # Measure system prompt / template base tokens
    base_prompt = _build_prompt("", "", "", "", friendly_chat)
    try:
        base_tokens = len(llm.tokenize(base_prompt.encode('utf-8')))
    except Exception:
        base_tokens = 300

    budget = max_prompt_len - base_tokens
    if budget <= 0:
        # Emergency fallback: slice raw prompt directly
        try:
            full_tokens = llm.tokenize(prompt.encode('utf-8'))
            truncated_tokens = full_tokens[:max_prompt_len]
            return llm.detokenize(truncated_tokens).decode('utf-8', errors='ignore')
        except Exception:
            return prompt[:max_prompt_len * 4]

    # Dynamically allocate budget:
    # 1. Memory context: up to 200 tokens
    # 2. Session history: up to 600 tokens
    # 3. Question / prompt content: up to 1000 tokens
    # The rest goes to workspace_block (which holds large folder files/structure)
    m_limit = min(len(m_tokens), 200)
    s_limit = min(len(s_tokens), 600)
    q_limit = min(len(q_tokens), 1000)
    
    allocated = m_limit + s_limit + q_limit
    w_limit = max(0, budget - allocated)

    # Re-distribute unused budget if some components are smaller than their limit
    if len(w_tokens) < w_limit:
        unused = w_limit - len(w_tokens)
        w_limit = len(w_tokens)
        q_limit = min(len(q_tokens), q_limit + unused)
        unused = max(0, (q_limit + unused) - min(len(q_tokens), q_limit + unused))
        if unused > 0:
            s_limit = min(len(s_tokens), s_limit + unused)

    # Iterative fallback reduction if the sum still exceeds budget
    while (m_limit + s_limit + q_limit + w_limit) > budget:
        if w_limit > 0:
            w_limit = max(0, w_limit - 50)
        elif q_limit > 500:
            q_limit -= 50
        elif s_limit > 200:
            s_limit -= 50
        elif q_limit > 100:
            q_limit -= 50
        elif s_limit > 0:
            s_limit = max(0, s_limit - 50)
        else:
            m_limit = max(0, m_limit - 20)
            if m_limit == 0:
                break

    # Helper to detokenize back to string with custom truncation notices
    def detok(tokens_list: list, limit: int, label: str, keep_end: bool = False) -> str:
        if not tokens_list:
            return ""
        if len(tokens_list) <= limit:
            try:
                return llm.detokenize(tokens_list).decode('utf-8', errors='ignore')
            except Exception:
                return ""
        
        try:
            if keep_end:
                truncated = tokens_list[-limit:]
                text = llm.detokenize(truncated).decode('utf-8', errors='ignore')
                return f"\n... [older {label} context truncated to fit AI window] ...\n" + text
            else:
                truncated = tokens_list[:limit]
                text = llm.detokenize(truncated).decode('utf-8', errors='ignore')
                return text + f"\n... [truncated {label} context to fit AI window] ...\n"
        except Exception:
            return ""

    truncated_wb = detok(w_tokens, w_limit, "workspace")
    truncated_q = detok(q_tokens, q_limit, "question")
    # For conversational history, we prioritize the LATEST turns, so keep the end of the history
    truncated_s = detok(s_tokens, s_limit, "history", keep_end=True)
    truncated_m = detok(m_tokens, m_limit, "memory")

    # Build the final safe prompt
    return _build_prompt(truncated_q, truncated_s, truncated_wb, truncated_m, friendly_chat)



class AnalysisSpinner:
    """
    Elegant terminal spinner class that shows an animated ASCII buddy next to status updates.
    """
    def __init__(self, species="crab", hat="none", friendly_chat=False):
        # Re-enabled terminal ASCII crab animator as requested by user
        try:
            from utils.buddy import BuddyAnimator
            self.animator = BuddyAnimator(species=species, hat=hat)
        except Exception:
            self.animator = None
        self.stop_event = threading.Event()
        self.thread = None
        self.friendly_chat = friendly_chat
        if friendly_chat:
            self.statuses = [
                "Connecting with Boss",
                "Warmly preparing response",
                "Powering up happy gears",
                "At your service"
            ]
        else:
            self.statuses = [
                "Analyzing codebase details",
                "Synthesizing technical response",
                "Evaluating dynamic workspace context",
                "Querying persistent neural weights"
            ]

    def _spin(self):
        # Fallback text spinner if animator not loaded
        idx = 0
        start_time = time.time()
        while not self.stop_event.is_set():
            elapsed = time.time() - start_time
            status = self.statuses[idx % len(self.statuses)]
            sys.stdout.write(f"\r[FRIDAY AI] ⚙️  {status}... ({elapsed:.1f}s)")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.4)
        sys.stdout.write("\r" + " " * 75 + "\r")
        sys.stdout.flush()

    def start(self):
        send_clawd_status("thinking")
        try:
            from utils.buddy import set_buddy_mood
            if self.friendly_chat:
                set_buddy_mood("happy")
            else:
                set_buddy_mood("thinking")
        except:
            pass
        if self.animator:
            import random
            status = random.choice(self.statuses)
            self.animator.start(status)
        else:
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()

    def stop(self):
        send_clawd_status("working_1")
        try:
            from utils.buddy import set_buddy_mood
            set_buddy_mood("idle")
        except:
            pass
        if self.animator:
            self.animator.stop()
        elif self.thread:
            self.stop_event.set()
            self.thread.join(timeout=2.0)
            self.thread = None


def ask_ai(question, workspace_context=None, save_to_memory=False, include_history=True, show_spinner=True, friendly_chat=False):
    # 1. Search persistent long-term memory (Bypass for short greetings to prevent RAG noise)
    is_greeting = friendly_chat or len(question.strip()) < 15 or question.lower().strip() in ("hi", "hello", "hey", "test", "thanks", "thank you", "clear", "exit")
    relevant_memories = []
    if include_history and not is_greeting:
        relevant_memories = search_memory(question)
        
    memory_context = ""
    if relevant_memories:
        memory_context = "### Relevant Historical Context:\n"
        for doc in relevant_memories:
            memory_context += f"- {doc}\n"
        memory_context += "\n"

    # 2. Manage short-term conversation memory
    if save_to_memory:
        add_message("user", question)
        
    session_context = get_instruct_context(MODEL_FAMILY) if include_history else ""

    workspace_block = f"### Active Workspace Context:\n{workspace_context}\n\n" if workspace_context else ""

    prompt = _build_truncated_prompt(question, session_context, workspace_block, memory_context, friendly_chat=friendly_chat)
    stop_tokens = _get_stop_tokens()


    spinner = None
    if show_spinner:
        spinner = AnalysisSpinner(friendly_chat=friendly_chat)
        spinner.start()
    try:
        with llm_lock:
            output = llm(
                prompt,
                max_tokens=-1,
                temperature=0.7,
                repeat_penalty=1.15,
                stop=stop_tokens
            )
    except Exception as e:
        send_clawd_status("confused")
        raise e
    finally:
        if spinner:
            spinner.stop()
        send_clawd_status("idle")

    raw_response = output["choices"][0]["text"].strip()
    if MODEL_FAMILY == "llama3" and not friendly_chat:
        raw_response = "<think>\n" + raw_response
        
    # Strip <think> blocks natively generated by DeepSeek-R1
    import re
    clean_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
    if '</think>' in clean_response:
        clean_response = clean_response.split('</think>')[-1].strip()
        
    if save_to_memory:
        # Save raw response (with `<think>...</think>`) to session history so that
        # multi-turn reasoning models like DeepSeek-R1 remain stable and context-aligned.
        add_message("assistant", raw_response)
        store_memory(f"User: {question}\nAssistant: {clean_response}")
        # Parse and store persistent memories
        try:
            from memory.memdir import parse_and_store_memories_from_response
            parse_and_store_memories_from_response(question, clean_response)
        except Exception:
            pass
        
    return clean_response


def ask_ai_stream(question, workspace_context=None, save_to_memory=True, include_history=True, show_spinner=True, friendly_chat=False):
    # 1. Search persistent long-term memory (Bypass for short greetings to prevent RAG noise)
    is_greeting = friendly_chat or len(question.strip()) < 15 or question.lower().strip() in ("hi", "hello", "hey", "test", "thanks", "thank you", "clear", "exit")
    relevant_memories = []
    if include_history and not is_greeting:
        relevant_memories = search_memory(question)
        
    memory_context = ""
    if relevant_memories:
        memory_context = "### Relevant Historical Context:\n"
        for doc in relevant_memories:
            memory_context += f"- {doc}\n"
        memory_context += "\n"

    # 2. Manage short-term conversation memory
    if save_to_memory:
        add_message("user", question)
        
    session_context = get_instruct_context(MODEL_FAMILY) if include_history else ""

    workspace_block = ""
    if workspace_context:
        workspace_block = f"### Active Workspace Context:\n{workspace_context}\n\n"

    prompt = _build_truncated_prompt(question, session_context, workspace_block, memory_context, friendly_chat=friendly_chat)
    stop_tokens = _get_stop_tokens()

    color_started = False
    spinner = None
    if show_spinner:
        spinner = AnalysisSpinner(friendly_chat=friendly_chat)
        spinner.start()

    try:
        with llm_lock:
            stream = llm(
                prompt,
                max_tokens=-1,
                temperature=0.7,
                repeat_penalty=1.15,
                stop=stop_tokens,
                stream=True
            )

        if MODEL_FAMILY == "llama3":
            full_response = ["<think>\n"] if not friendly_chat else []
        else:
            full_response = []
        consecutive_ticks = 0
        thinking_concluded = False
        printed_index = 0
        
        for chunk in stream:
            token = chunk["choices"][0]["text"]
            full_response.append(token)
            
            # Guardrail against infinite backtick loops
            if "```" in token:
                consecutive_ticks += 1
            else:
                if token.strip():
                    consecutive_ticks = 0
                    
            if consecutive_ticks > 3:
                break
                
            current_full_text = "".join(full_response)
            
            if not thinking_concluded:
                if "</think>" in current_full_text:
                    thinking_concluded = True
                    if spinner:
                        spinner.stop()
                        spinner = None
                    parts = current_full_text.split("</think>", 1)
                    after_think = parts[1]
                    if after_think.strip():
                        if not color_started:
                            sys.stdout.write("\033[38;2;255;165;0m")
                            color_started = True
                        sys.stdout.write(after_think)
                        sys.stdout.flush()
                        printed_index = len(after_think)
                else:
                    # Dynamically detect if this is a non-thinking model/response.
                    stripped_text = current_full_text.lstrip()
                    
                    # Check if the prefix matches a think tag prefix.
                    is_think_prefix = False
                    for prefix in ["<", "<t", "<th", "<thi", "<thin", "<think"]:
                        if stripped_text == prefix or stripped_text.startswith(prefix):
                            is_think_prefix = True
                            break
                    
                    # If we have non-whitespace text that is not a think prefix, it's a standard model!
                    if not is_think_prefix and len(stripped_text) > 0:
                        thinking_concluded = True
                    # Fallback check for safe limits
                    elif len(stripped_text) > 15 and "<think>" not in stripped_text:
                        thinking_concluded = True
                        
                    if thinking_concluded:
                        if spinner:
                            spinner.stop()
                            spinner = None
                        if not color_started:
                            sys.stdout.write("\033[38;2;255;165;0m")
                            color_started = True
                        sys.stdout.write(current_full_text)
                        sys.stdout.flush()
                        printed_index = len(current_full_text)
            else:
                # Reasoning concluded. Output response tokens in real-time.
                if spinner:
                    spinner.stop()
                    spinner = None
                parts = current_full_text.split("</think>", 1)
                after_think = parts[1] if len(parts) > 1 else current_full_text
                
                # Guardrail: if the model tries to start a new thinking block or turn, stop streaming immediately
                if any(marker in after_think for marker in ["<think>", "<|start_header_id|>", "<|im_start|>", "### Instruction:"]):
                    break
                    
                new_delta = after_think[printed_index:]
                if new_delta:
                    if not color_started:
                        sys.stdout.write("\033[38;2;255;165;0m")
                        color_started = True
                    sys.stdout.write(new_delta)
                    sys.stdout.flush()
                    printed_index += len(new_delta)
    except Exception as e:
        send_clawd_status("confused")
        raise e
    finally:
        if color_started:
            sys.stdout.write("\033[0m")
            sys.stdout.flush()
        if spinner:
            spinner.stop()
        send_clawd_status("idle")
    print()  # Add newline at the end
    response_str = "".join(full_response).strip()
    
    # Clean the final stored string perfectly to remove R1 reasoning blocks
    import re
    clean_response = re.sub(r'<think>.*?</think>', '', response_str, flags=re.DOTALL).strip()
    if '</think>' in clean_response:
        clean_response = clean_response.split('</think>')[-1].strip()
    
    if save_to_memory:
        # Save raw response (with `<think>...</think>`) to session history so that
        # multi-turn reasoning models like DeepSeek-R1 remain stable and context-aligned.
        add_message("assistant", response_str)
        # Store in long-term memory
        store_memory(f"User: {question}\nAssistant: {clean_response}")
        # Parse and store persistent memories
        try:
            from memory.memdir import parse_and_store_memories_from_response
            parse_and_store_memories_from_response(question, clean_response)
        except Exception:
            pass
        
    return clean_response