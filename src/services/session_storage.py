import json
from pathlib import Path
from typing import Dict, Any, Optional

class SessionStorageService:
    """
    Service responsible for loading and saving the complete adaptive interview session state
    to/from disk to support Development Mode (Offline).
    """
    DATA_DIR = Path("data")
    FILE_PATH = DATA_DIR / "demo_session.json"

    @staticmethod
    def save_session(
        profile: Any,
        session: Any,
        state: Any,
        category_sequence: list[str],
        extracted_text: str
    ) -> None:
        """
        Saves all structured data needed to recreate an interview session to disk.
        """
        SessionStorageService.DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "candidate_profile": profile.model_dump() if profile else None,
            "interview_session": session.model_dump() if session else None,
            "interview_state": state.model_dump() if state else None,
            "category_sequence": category_sequence,
            "extracted_text": extracted_text
        }
        with open(SessionStorageService.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_session() -> Optional[Dict[str, Any]]:
        """
        Loads the saved session dictionary from disk.
        """
        if not SessionStorageService.session_exists():
            return None
        try:
            with open(SessionStorageService.FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[SessionStorageService] Error loading session: {e}")
            return None

    @staticmethod
    def session_exists() -> bool:
        """
        Checks if the saved session file exists.
        """
        return SessionStorageService.FILE_PATH.exists()
