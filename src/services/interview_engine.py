import uuid
import json
import requests
from config import settings
from src.models.profile import CandidateProfile
from src.models.question import Question
from src.models.interview_session import InterviewSession, QAPair
from src.utils.helpers import retry_on_rate_limit, sanitize_ai_output

class InterviewEngineError(Exception):
    """Custom exception raised when the Interview Engine encounters a failure."""
    pass

class InterviewEngine:
    """
    Service responsible for driving the technical interview pipeline.
    Handles upfront question generation (generating all questions in one API call)
    and progression management.
    """

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def generate_all_questions(profile: CandidateProfile, count: int = 8) -> list[Question]:
        """
        Sends candidate profile details to Gemini in a single API call to generate
        all interview questions distributed across target category weights.

        Args:
            profile (CandidateProfile): The structured candidate profile.
            count (int): The number of questions to generate.

        Returns:
            list[Question]: List of pre-generated Question objects.

        Raises:
            InterviewEngineError: If the API key is missing or generation fails.
        """
        if not settings.GEMINI_API_KEY:
            raise InterviewEngineError(
                "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."
            )

        # Build endpoint URL using Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

        # System instructions detailing distribution rules
        system_instruction = (
            "You are a professional technical interviewer conducting an interview for an internship placement.\n"
            f"Your task is to generate exactly {count} technical questions tailored to the candidate's background.\n\n"
            f"Candidate Name: {profile.name}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Education: {', '.join(profile.education)}\n"
            f"Projects: {', '.join(profile.projects)}\n\n"
            "Requirements:\n"
            f"1. Generate exactly {count} questions.\n"
            "2. Distribute the questions across categories according to these approximate weights:\n"
            "   - Resume & Projects (40%): Conceptual or design questions about the candidate's specific projects or listed skills.\n"
            "   - AI/ML (25%): Foundational machine learning, architectures, training, math, or tools.\n"
            "   - Software Engineering (20%): OOP/FP, REST APIs, design patterns, testing, or clean architecture.\n"
            "   - DSA & CS Fundamentals (15%): Data structures, runtime complexity (Big-O), networking, or OS basics.\n"
            "3. Keep each question technical, precise, and demanding for an internship candidate.\n"
            "4. Ensure each question has a clear, unique 'topic' concept.\n"
            "5. Avoid duplicate topics or generic fluff. Output a single JSON object matching the requested schema."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"Generate all {count} questions."}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Sequential ID (e.g. Q1)."},
                                    "text": {"type": "string", "description": "The technical question text."},
                                    "category": {
                                        "type": "string",
                                        "enum": ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]
                                    },
                                    "topic": {"type": "string", "description": "The specific technical concept being tested."}
                                },
                                "required": ["id", "text", "category", "topic"]
                            }
                        }
                    },
                    "required": ["questions"]
                }
            }
        }

        headers = {"Content-Type": "application/json"}

        # Defensive 2-attempt validation retry loop
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=35)
                
                # Handle HTTP errors explicitly
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise InterviewEngineError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")

                response_data = response.json()
                
                if "candidates" not in response_data or not response_data["candidates"]:
                    raise InterviewEngineError("Invalid response structure from Gemini API: 'candidates' field missing.")

                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                questions_dict = json.loads(json_text)
                
                questions_list = []
                for idx, q_dict in enumerate(questions_dict.get("questions", [])):
                    # Sanitize fields defensively
                    q_dict["id"] = f"Q{idx + 1}"
                    q_dict["text"] = sanitize_ai_output(q_dict.get("text", ""))
                    q_dict["topic"] = sanitize_ai_output(q_dict.get("topic", ""))
                    q_dict["category"] = sanitize_ai_output(q_dict.get("category", ""))
                    
                    questions_list.append(Question(**q_dict))
                    
                if len(questions_list) == 0:
                    raise InterviewEngineError("Gemini generated zero questions.")
                    
                return questions_list
            except (requests.exceptions.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as e:
                last_error = e
                print(f"[generate_all_questions] Validation attempt {attempt + 1} failed. Details: {str(e)}. Retrying...")
                continue
                
        raise InterviewEngineError(
            f"Failed to generate structured questions after multiple attempts. Last error: {str(last_error)}"
        )

    @staticmethod
    def initialize_session(profile: CandidateProfile, count: int = 8) -> InterviewSession:
        """
        Creates and returns a new initialized InterviewSession with pre-generated questions.

        Args:
            profile (CandidateProfile): The structured profile of the candidate.
            count (int): Number of questions to pre-generate.

        Returns:
            InterviewSession: A fresh session tracking structure populated with questions.
        """
        session_id = str(uuid.uuid4())
        # Call batch question generation
        questions = InterviewEngine.generate_all_questions(profile, count)
        
        return InterviewSession(
            session_id=session_id,
            candidate_profile=profile,
            questions=questions,
            history=[],
            current_question_index=0,
            is_completed=False
        )

    @staticmethod
    def submit_answer(session: InterviewSession, answer: str) -> None:
        """
        Submits the candidate's answer for the current question index.
        Appends the QAPair to session history, resets current_question,
        increments the index, and checks for completion.

        Args:
            session (InterviewSession): The active session to modify.
            answer (str): The candidate's text answer.

        Raises:
            InterviewEngineError: If the index is out of bounds.
        """
        if session.current_question_index >= len(session.questions):
            raise InterviewEngineError("No active question is set in this session.")

        current_q = session.questions[session.current_question_index]

        # Save QAPair in history without immediate evaluation
        qa_pair = QAPair(
            question=current_q, 
            user_answer=answer.strip(), 
            evaluation=None
        )
        session.history.append(qa_pair)

        # Increment index
        session.current_question_index += 1

        # Check if we have completed the interview
        if session.current_question_index >= len(session.questions):
            session.is_completed = True
