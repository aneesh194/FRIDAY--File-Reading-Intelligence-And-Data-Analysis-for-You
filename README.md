# 🤖 FRIDAY AI
### File Reading & Intelligent Data Analysis for You

FRIDAY AI is a fully offline, privacy-first AI assistant inspired by Tony Stark's FRIDAY. Built with Python and local Large Language Models (LLMs), it provides conversational AI, document intelligence, OCR processing, code analysis, persistent memory, report generation, and a premium animated terminal companion — all without requiring cloud APIs or internet connectivity.

---

## ✨ Features

### 🧠 Local AI Intelligence
- DeepSeek-R1-Distill-Llama-8B powered inference
- Runs completely offline using llama.cpp
- Real-time streaming responses
- Technical and friendly conversation modes
- Automatic model family detection

### 📄 Document Analysis
- PDF analysis
- DOCX document analysis
- TXT file analysis
- Intelligent document summarization
- Financial document extraction

### 👁️ OCR & Image Understanding
- PaddleOCR integration
- Invoice and receipt processing
- Screenshot analysis
- Batch image folder analysis
- Multi-format image support

### 💻 Code Intelligence
- Source code analysis
- Project structure understanding
- Flask route detection
- Express.js route extraction
- SQL schema analysis
- Folder-wide code audits

### 🧠 Multi-Tier Memory System
- Short-term conversation memory
- Long-term vector memory with ChromaDB
- Durable structured memory
- Semantic retrieval (RAG)
- User preference retention

### 📊 Report Generation
Generate reports in:
- DOCX
- HTML
- Markdown
- TXT

### 🎨 Clawd-2 Terminal Companion
- Animated AI companion
- Multiple moods and expressions
- Thinking animations
- Typing indicators
- Startup and shutdown animations
- Full 24-bit ANSI color rendering

### 🌐 Local API Support
- FastAPI integration
- REST API endpoints
- Localhost access
- Easy third-party integration

---

## 🏗️ Architecture

```text
User Input
    │
    ▼
Intent Router
    │
    ├── Friendly Chat
    ├── Technical Chat
    ├── Document Analysis
    ├── Image Analysis
    ├── Code Analysis
    └── Folder Audit
            │
            ▼
      DeepSeek-R1
      (llama.cpp)
            │
            ▼
     Memory System
            │
     ├── Short-Term
     ├── Long-Term RAG
     └── Durable Memory
            │
            ▼
       Final Output
```

---

## 🛠️ Technology Stack

| Component | Technology |
|------------|------------|
| Language | Python 3.11 |
| LLM Engine | llama-cpp-python |
| Model | DeepSeek-R1-Distill-Llama-8B |
| Vector Database | ChromaDB |
| Embeddings | all-MiniLM-L6-v2 |
| OCR | PaddleOCR |
| API | FastAPI |
| Document Processing | pdfplumber, python-docx |
| Image Processing | Pillow |
| Server | Uvicorn |

---

## 📂 Project Structure

```text
FRIDAY-AI/
│
├── ai/
│   ├── ai_engine.py
│   ├── prompts.py
│   └── api_server.py
│
├── analyzers/
│   ├── code_analyzer.py
│   ├── document_analyzer.py
│   ├── image_analyzer.py
│   └── log_analyzer.py
│
├── memory/
│   ├── conversation_memory.py
│   ├── persistent_memory.py
│   └── memdir.py
│
├── utils/
│   ├── buddy.py
│   ├── intent_router.py
│   ├── clawd_client.py
│   └── report_generator.py
│
├── models/
│
├── reports/
│
├── main.py
└── run_friday.bat
```

---

## 🚀 Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/FRIDAY-AI.git
cd FRIDAY-AI
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux / Mac

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install llama-cpp-python chromadb
pip install sentence-transformers torch transformers
pip install Pillow paddleocr pdfplumber
pip install fastapi uvicorn python-docx requests
```

---

## 📥 Model Setup

Download a GGUF model and place it inside:

```text
models/
```

Recommended:

```text
DeepSeek-R1-Distill-Llama-8B-Q4_K_M.gguf
```

---

## ▶️ Run FRIDAY

### Windows

```bash
run_friday.bat
```

### Direct Launch

```bash
python main.py
```

---

## 🎯 Supported Commands

### Chat

```text
hello
how are you
tell me a joke
```

### Document Analysis

```text
analyze invoice.pdf
analyze report.docx
```

### Image Analysis

```text
analyze receipt.png
analyze screenshot.jpg
```

### Code Analysis

```text
analyze app.py
analyze project_folder/
```

### Reports

```text
save report
generate docx report
```

---

## 🔒 Privacy First

FRIDAY AI is designed to run entirely on your machine.

- No cloud APIs
- No external AI services
- No data collection
- No internet dependency
- Complete user control

---

## 📈 Future Roadmap

- Voice Assistant
- Speech-to-Text
- Text-to-Speech
- Desktop GUI
- VS Code Extension
- Autonomous Agents
- Multi-Model Support
- Advanced Workflow Automation

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome.

Fork the repository and submit a pull request.

---

## 📜 License

This project is licensed under the MIT License.

---

## ⚡ About

**FRIDAY AI** combines local LLM inference, OCR, document intelligence, code understanding, semantic memory, and a premium terminal experience into a single offline assistant platform.

**No Cloud. No Subscriptions. Just Intelligence.**
