# PCOS - Personal Cognitive Operating System

**PCOS (Personal Cognitive Operating System)** is a powerful, locally-hosted desktop application designed to act as your digital brain. It seamlessly runs in the background, offering quick captures of your thoughts, state monitoring, and semantic memory search—all powered by an embedded vector database and a local API server.

## 🚀 Key Features

- **Quick Capture System:** Instantly save tasks, ideas, and reminders using a global hotkey, without interrupting your workflow.
- **Always-on State Monitoring:** Runs silently in the background, constantly checking and recording your context every 30 seconds.
- **Local Semantic Memory:** Utilizes `ChromaDB` and `sentence-transformers` for powerful, embedding-based semantic search across all your captures.
- **Desktop Overlay & System Tray:** Accessible directly from your Windows system tray, complete with a quick-access overlay window.
- **Local API Server:** A robust FastAPI backend exposing REST endpoints to interface with the core cognitive engine.

## 🛠️ Technology Stack

- **Backend / API:** Python, FastAPI, Uvicorn
- **UI / Desktop App:** PyQt6, PyQt6-WebEngine
- **Memory & Embeddings:** ChromaDB, sentence-transformers
- **OS Integration:** pynput, keyboard, pywin32, windows-toasts
- **Graph Processing:** NetworkX

## 📂 Project Structure

```text
pcos/
├── src/
│   └── pcos/
│       ├── api/            # FastAPI server and endpoints
│       ├── core/           # Core business logic and cognitive engine
│       ├── infrastructure/ # Settings, DB connections, OS-specific integrations
│       ├── ui/             # PyQt6 desktop UI, Tray icon, Overlay window
│       ├── workers/        # Background workers (e.g., State monitor)
│       └── main.py         # Application entry point
├── .env                    # Environment variables (e.g., PCOS_DATA_DIR)
├── requirements.txt        # Python dependencies
└── run.ps1                 # Launch script for Windows
```

## ⚙️ Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd pcos
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment:**
   Edit the `.env` file in the root directory to set your desired data directory (default configurable via `PCOS_DATA_DIR`). This is where your vector DB and state data will be stored.

6. **Run the Application:**
   ```bash
   python -m src.pcos.main
   ```
   *Alternatively, you can use the provided `run.ps1` script on Windows.*

## ⌨️ Usage & Hotkeys

Once running, PCOS will reside in your system tray as a "P" icon.

- **`Ctrl+Alt+P`**: Open Quick Capture dialog. Type your thoughts and press `Ctrl+Enter` to save.
- **`Ctrl+Alt+O`**: Toggle the PCOS Overlay window.
- **System Tray Click**: Toggle the overlay or right-click to access the context menu (Show Current State, Quit, etc.).

## 🛡️ Privacy & Local First

PCOS is built with a local-first architecture. Your captures, semantic memories, and state monitoring data remain strictly on your machine, stored within your configured data directory.
