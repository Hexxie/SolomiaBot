# SolomiaBot

This repository contains the source code for a Python bot (e.g., Telegram or FastAPI-based).  
The following instructions describe how to set up and run the local development environment using **Poetry**.

---

## 📦 Requirements

Make sure you have the following installed:

- **Python ≥ 3.10**
- **Poetry** → [https://python-poetry.org/docs/](https://python-poetry.org/docs/)

Check your versions:
```bash
python --version
poetry --version
```

## ⚙️ Setup (First Time)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Configure Poetry to create a .venv inside the project

```bash
poetry config virtualenvs.in-project true
```

### 3. Install dependencies

```bash
poetry install
```

### 4. Activate the virtual environment

```bash
poetry shell
```

### 5. (Optional) Add new dependencies

```bash
poetry add <package-name>
```

## 🚀 Run the Bot (Development)

Example for a FastAPI bot:
```bash
uvicorn main:app --reload
```

Example for a Telegram bot:
```bash
python main.py
```