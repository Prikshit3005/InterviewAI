import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
# We check both the application base directory and its parent directory (workspace root)
env_paths = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
]
env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        env_loaded = True
        break

if not env_loaded:
    load_dotenv()


# Application UI Settings
APP_TITLE = "AI Interview Assistant"
APP_ICON = "💼"

# File Upload Settings
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = ["pdf"]

# Interview Constraints (For future Milestones, defined here centrally)
DEFAULT_QUESTION_COUNT = 8
CATEGORY_WEIGHTS = {
    "Resume & Projects": 0.40,
    "AI/ML Concepts": 0.25,
    "Software Engineering": 0.20,
    "DSA & CS Fundamentals": 0.15,
}

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# Mode configuration (Production / Development)
DEV_MODE = os.getenv("DEV_MODE", "False").strip().lower() == "true"
if DEV_MODE:
    print("Running in DEVELOPMENT MODE (Offline Dataset)", flush=True)
else:
    print("Running in PRODUCTION MODE (Gemini Enabled)", flush=True)
