import json
import requests
from pydantic import ValidationError
from config import settings
from src.models.profile import CandidateProfile
from src.utils.helpers import retry_on_rate_limit, sanitize_ai_output

class GeminiClientError(Exception):
    """Custom exception raised when the Gemini API request fails or returns invalid structures."""
    pass

class GeminiClientService:
    """
    Service responsible for interacting with the Gemini API using REST.
    Uses Python requests directly to provide clean, version-independent API calls.
    """

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def generate_profile(resume_text: str) -> CandidateProfile:
        """
        Sends extracted resume text to the Gemini API and returns a structured CandidateProfile.

        Args:
            resume_text (str): The raw text extracted from the candidate's resume PDF.

        Returns:
            CandidateProfile: A validated, typed data structure of the candidate.

        Raises:
            GeminiClientError: If the API key is missing, API request fails, or validation fails.
        """
        if not settings.GEMINI_API_KEY:
            raise GeminiClientError(
                "Gemini API key is not configured. "
                "Please add GEMINI_API_KEY to your .env file."
            )
        
        # Build API endpoint URL using 2.5 Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

        # System prompt to instruct the model on extraction rules
        system_instruction = (
            "You are a professional recruiting assistant. Your task is to analyze the raw text of a candidate's resume "
            "and extract structured information exactly matching the requested JSON schema. "
            "Ensure the output conforms to standard JSON. If the candidate name or email cannot be found, "
            "return empty strings. For skills, education, and projects, extract all relevant items."
        )

        prompt_text = f"Analyze the following resume and extract the candidate profile:\n\n{resume_text}"

        # Configure request payload conforming to Gemini API REST specification
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{system_instruction}\n\n{prompt_text}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for factual extraction
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The candidate's full name."},
                        "email": {"type": "string", "description": "The candidate's email address."},
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of technologies, languages, databases, or libraries."
                        },
                        "education": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of degrees, schools, and years attended."
                        },
                        "projects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of academic, professional, or personal projects."
                        }
                    },
                    "required": ["name", "email", "skills", "education", "projects"]
                }
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        # Defensive 2-attempt parsing and validation loop
        last_error = None
        for attempt in range(2):
            try:
                # Make the HTTP POST call
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                # Handle HTTP errors explicitly
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise GeminiClientError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")
                
                response_data = response.json()
                
                # Validate response structure
                if "candidates" not in response_data or not response_data["candidates"]:
                    # Check for safety blocks
                    if "promptFeedback" in response_data:
                        raise GeminiClientError(
                            f"Gemini API request was blocked by safety filters. Details: {response_data['promptFeedback']}"
                        )
                    raise GeminiClientError(
                        f"Invalid response structure from Gemini API. Expected 'candidates' field. Response: {response_data}"
                    )

                # Retrieve text part containing JSON output
                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                
                # Parse unstructured JSON string
                profile_dict = json.loads(json_text)
                
                # Sanitize all parsed fields defensively before Pydantic validation
                profile_dict["name"] = sanitize_ai_output(profile_dict.get("name", ""))
                profile_dict["email"] = sanitize_ai_output(profile_dict.get("email", ""))
                profile_dict["skills"] = [sanitize_ai_output(s) for s in profile_dict.get("skills", []) if s]
                profile_dict["education"] = [sanitize_ai_output(e) for e in profile_dict.get("education", []) if e]
                profile_dict["projects"] = [sanitize_ai_output(p) for p in profile_dict.get("projects", []) if p]
                
                # Instantiation validates types and requirements using Pydantic
                profile = CandidateProfile(**profile_dict)
                return profile
            except (requests.exceptions.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as e:
                last_error = e
                # Wait briefly before repeating the API query if it's the first attempt
                print(f"[generate_profile] Validation attempt {attempt + 1} failed. Details: {str(e)}. Retrying...")
                continue
                
        raise GeminiClientError(
            f"Failed to generate structured profile after multiple attempts. Last error details: {str(last_error)}"
        )
