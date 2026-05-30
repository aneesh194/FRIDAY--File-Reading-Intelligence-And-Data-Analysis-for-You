# FileMind AI - Comprehensive Codebase Blueprint

This document acts as the master technical code blueprint for **FileMind AI**. It provides an exhaustive, file-by-file analysis of **all 13 primary files** in the project, detailing their code purposes, exact function signatures, core operational duties, and the algorithms/design patterns they employ.

---

## 1. Core Core Orchestration & AI Engine

### 1.1 [main.py](file:///d:/FileMind%20Project/main.py)
* **Code Purpose**: The central command-line loop and session lifecycle manager.
* **Main Code Functions**:
  * `load_last_analysis() -> dict`: Reads the persistent state from `reports/active_project.json` on startup. If found, returns the dictionary; otherwise, returns an empty analysis structure.
  * `save_last_analysis(analysis: dict) -> None`: Writes the current analysis target (type, path, and content) to `reports/active_project.json` in clean UTF-8 format.
  * `main() -> None`: Orchestrates terminal inputs, executes global console UTF-8 stream adjustments, handles intent router mapping, feeds targets to appropriate analyzers, updates the active persistent project state, and processes report generation commands.
* **Algorithms & Design Patterns**:
  * **Global Encoding Override**: Configures terminal standard output to UTF-8 using `sys.stdout.reconfigure(encoding='utf-8')` to render high-unicode characters flawlessly on Windows.
  * **Persistent Workspace Memento Pattern**: Dynamically serializes and de-serializes operational states to avoid redundant folder analysis across session restarts.

---

### 1.2 [ai/ai_engine.py](file:///d:/FileMind%20Project/ai/ai_engine.py)
* **Code Purpose**: The local Large Language Model wrapper and streaming controller.
* **Main Code Functions**:
  * `ask_ai(question: str, save_to_memory: bool = False, include_history: bool = True) -> str`: Standard inference handler. Retrieves persistent vector memories and sliding conversational logs (if `include_history=True`), compiles prompts, triggers `llama.cpp` inference, and returns complete answers.
  * `ask_ai_stream(question: str, save_to_memory: bool = True, include_history: bool = True) -> str`: Streaming inference handler. Intercepts generated tokens in real time, flushes them directly to console stdout, checks for code-block loop guardrails, and returns the final string.
* **Algorithms & Design Patterns**:
  * **Context Size Capacity Scale Algorithm**: Sets active context bounds (`n_ctx=12288`) to accommodate dense, multi-file codebases natively on local CPUs.
  * **Context History-Isolation Pattern**: Dynamically ignores conversation history for background utility sub-queries (setting `include_history=False`), dropping background token footprints strictly under 1,000 tokens for maximum speed.
  * **Infinite-Loop Guardrail Algorithm**: Measures consecutive backtick loops (` ``` `). If a token generator outputs redundant tick structures, the handler breaks the loop, protecting against endless execution.

---

### 1.3 [ai/prompts.py](file:///d:/FileMind%20Project/ai/prompts.py)
* **Code Purpose**: Defines premium system directives and model boundaries.
* **Main Code Structures**:
  * `SYSTEM_PROMPT`: The master prompt directing the model to act as a highly technical, encouraging, conversational AI companion. It demands formatted code structures, direct answers, and friendly Multi-byte UTF-8 emojis.
* **Algorithms & Design Patterns**:
  * **Role-Prompting Pattern**: Instructs local models to maintain strict analytical boundaries (distinguishing friendly queries from traceback scans) and output well-structured diagnostic responses.

---

## 2. Memory & Database Subsystems

### 2.1 [memory/conversation_memory.py](file:///d:/FileMind%20Project/memory/conversation_memory.py)
* **Code Purpose**: Manages local sliding conversational histories.
* **Main Code Functions**:
  * `add_message(role: str, content: str) -> None`: Appends chat turns to the list and writes the JSON cache to `reports/conversation_history.json`.
  * `get_history() -> list`: Loads history records, automatically applying self-healing transformations.
  * `get_instruct_context() -> str`: Compiles history records into formatted system prompts (e.g. `### Instruction: ... \n### Response: ...`).
* **Algorithms & Design Patterns**:
  * **Self-Healing Data Transformation Algorithm**: Automatically intercepts and maps legacy `{ "user": u, "ai": a }` dictionary keys to new modern compliant roles on the fly, guaranteeing backwards-compatibility.

---

### 2.2 [memory/persistent_memory.py](file:///d:/FileMind%20Project/memory/persistent_memory.py)
* **Code Purpose**: Manages ChromaDB semantic vector search indexes.
* **Main Code Functions**:
  * `store_memory(text: str, metadata: dict = None) -> None`: Generates local on-device embeddings and registers texts inside SQLite vector indices under a randomized UUID key.
  * `search_memory(query: str, limit: int = 3) -> list`: Queries the ChromaDB index and returns the top 3 semantically relevant documents using on-device Cosine Similarity computations.
* **Algorithms & Design Patterns**:
  * **Cosine Similarity Over CPU Embeddings**: Utilizes local vector operations to compute proximity between chat terms and prior sessions.
  * **Null Metadata Sanitizer Pattern**: Resolves empty metadata dictionaries `{}` to standard `None` parameters to prevent ChromaDB schema-mismatch warnings.

---

## 3. Workspace Report Generator & Intent Router

### 3.1 [report_generator/report_generator.py](file:///d:/FileMind%20Project/report_generator/report_generator.py)
* **Code Purpose**: Deep-walks folders, parses code frameworks, runs image OCR, and compiles premium markdown reports.
* **Main Code Functions**:
  * `generate_project_report(folder_path: str, save_directory: str = "reports") -> str`: Walk directory trees, categorizes files, extracts functions/classes/frameworks, parses log warnings, executes local image OCR, runs utility summaries, compiles the report, and writes it to the user's directory path.
* **Algorithms & Design Patterns**:
  * **Folder Walk & Ignore Algorithms**: Recursively explores code directories using `os.walk` while dynamically ignoring heavy build and virtualenv libraries (like `.git`, `node_modules`, `venv`, `.venv`).
  * **Python Code AST Parsing**: Parses source files into Abstract Syntax Trees using `ast.parse()`, walking nodes to locate class definitions (`ast.ClassDef`) and function definitions (`ast.FunctionDef`).
  * **PaddleOCR Extraction Pipeline**: Binds image scanners to OCR pipelines, reading text blocks out of local graphics files.

---

### 3.2 [utils/intent_router.py](file:///d:/FileMind%20Project/utils/intent_router.py)
* **Code Purpose**: Parses user inputs, extracts path structures, and determines operational branches.
* **Main Code Functions**:
  * `detect_intent(text: str) -> dict`: Resolves keywords (like report generators) and extracts path strings. Returns dictionary types (`folder`, `code`, `document`, `log`, `image`, `report`, `general`).
  * `extract_path(text: str) -> str`: Analyzes inputs to extract valid physical target paths.
* **Algorithms & Design Patterns**:
  * **Spaced-Path Combination Search Algorithm**: Splits input sentences into contiguous word lists, checking every sliding combination from longest to shortest against the physical disk:
    $$w_{i:i+k} \mid \text{os.path.exists}(w_{i:i+k}) = \text{True}$$
    This matches folders containing spaces (e.g. `D:\Error Explainer`) perfectly without requiring wrapping quotes.

---

## 4. Operational Domain Analyzers & Fallbacks

### 4.1 [analyzers/code_analyzer.py](file:///d:/FileMind%20Project/analyzers/code_analyzer.py)
* **Code Purpose**: Technical single-file code analyzer.
* **Main Code Functions**:
  * `analyze_code_file(file_path: str) -> str`: Reads code files, builds specific diagnostic instructions, and streams responses via `ask_ai_stream`.

### 4.2 [analyzers/document_analyzer.py](file:///d:/FileMind%20Project/analyzers/document_analyzer.py)
* **Code Purpose**: Handles PDFs, TXT, MD, and CSV files.
* **Main Code Functions**:
  * `analyze_document(file_path: str) -> str`: Normalizes line spacing and processes multi-page texts.

### 4.3 [analyzers/log_analyzer.py](file:///d:/FileMind%20Project/analyzers/log_analyzer.py)
* **Code Purpose**: Traverses server logs for error details.
* **Main Code Functions**:
  * `analyze_log(file_path: str) -> str`: Reads log tracks, isolates critical warning statements, and requests formatted technical explanations.
* **Algorithms & Design Patterns**:
  * **Sliding Window Error Buffer**: Isolates matches using string-matching bounds, preventing log files from overflowing token capacities.

### 4.4 [analyzers/image_analyzer.py](file:///d:/FileMind%20Project/analyzers/image_analyzer.py)
* **Code Purpose**: OCR-based image processor.
* **Main Code Functions**:
  * `analyze_image(image_path: str) -> str`: Directs local image pipelines to read logs, code, or terminal snapshots inside graphics files.

### 4.5 [utils/file_reader.py](file:///d:/FileMind%20Project/utils/file_reader.py)
* **Code Purpose**: Core low-level file reader.
* **Main Code Functions**:
  * `read_file(file_path: str) -> str`: Reads files dynamically, checking and cleaning encoding layouts.

### 4.6 [utils/report_generator.py](file:///d:/FileMind%20Project/utils/report_generator.py) (Legacy)
* **Code Purpose**: Fallback report compiler.
* **Main Code Functions**:
  * `save_report(target_type: str, file_path: str, explanation: str, save_directory: str = "reports") -> str`: Saves simple single-file code analysis reports to markdown outputs.

---
*FileMind AI Comprehensive Codebase Blueprint — Maintained locally in workspace.*
