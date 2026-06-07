# PCOS – Personal Cognitive Operating System

## Setup
1. `python -m venv venv`
2. `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3. `pip install -r requirements.txt`
4. Edit `.env` to set your data directory (default E:/pcos_data)
5. `python -m src.pcos.main`

## Project structure
See architecture reference. Data directory configurable via PCOS_DATA_DIR env or .env file.