import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent

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
