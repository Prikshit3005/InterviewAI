import uuid
import json
import requests
import streamlit as st
from config import settings
from src.models.profile import CandidateProfile
from src.models.question import Question
from src.models.interview_session import InterviewSession, QAPair
from src.models.interview_state import InterviewState
from src.utils.helpers import retry_on_rate_limit, sanitize_ai_output

class InterviewEngineError(Exception):
    """Custom exception raised when the Interview Engine encounters a failure."""
    pass

class InterviewEngine:
    """
    Service responsible for driving the technical interview pipeline.
    Handles adaptive question generation, difficulty adjustments,
    and progress management step-by-step using Gemini.
    """

    @staticmethod
    def get_category_sequence(count: int) -> list[str]:
        """
        Determines the ordered sequence of question categories based on weight distribution:
        - Resume & Projects (40%)
        - AI/ML (25%)
        - Software Engineering (20%)
        - DSA & CS Fundamentals (15%)
        All questions within a category are grouped sequentially.
        """
        c1 = max(1, round(count * 0.40))
        c2 = max(1, round(count * 0.25))
        c3 = max(1, round(count * 0.20))
        c4 = max(1, count - (c1 + c2 + c3))
        
        if c4 <= 0:
            c4 = 1
            diff = (c1 + c2 + c3 + c4) - count
            for _ in range(diff):
                if c1 > 1:
                    c1 -= 1
                elif c2 > 1:
                    c2 -= 1
                elif c3 > 1:
                    c3 -= 1
                    
        return (
            ["Resume & Projects"] * c1 +
            ["AI/ML"] * c2 +
            ["Software Engineering"] * c3 +
            ["DSA & CS Fundamentals"] * c4
        )[:count]

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def generate_first_question(profile: CandidateProfile, category: str, difficulty: str) -> Question:
        """
        Generates the first question based on candidate profile, category, and initial difficulty.
        """
        if not settings.GEMINI_API_KEY:
            raise InterviewEngineError(
                "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

        system_instruction = (
            "You are a professional technical interviewer conducting an interview for an internship placement.\n"
            "Your task is to generate the first technical question tailored to the candidate's background.\n\n"
            f"Candidate Name: {profile.name}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Education: {', '.join(profile.education)}\n"
            f"Projects: {', '.join(profile.projects)}\n\n"
            f"Requirements:\n"
            f"1. Category of the question MUST be exactly: {category}\n"
            f"2. Difficulty level of the question MUST be: {difficulty}\n"
            "3. Keep the question technical, precise, and demanding for an internship candidate.\n"
            "4. Output a single JSON object matching the requested schema."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "Generate the first question."}
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
                        "text": {"type": "string", "description": "The technical question text."},
                        "category": {
                            "type": "string",
                            "enum": ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]
                        },
                        "topic": {"type": "string", "description": "The specific technical topic/concept tested."}
                    },
                    "required": ["text", "category", "topic"]
                }
            }
        }

        headers = {"Content-Type": "application/json"}
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=35)
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise InterviewEngineError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")

                response_data = response.json()
                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                q_dict = json.loads(json_text)
                
                # Sanitize
                q_dict["id"] = "Q1"
                q_dict["text"] = sanitize_ai_output(q_dict.get("text", ""))
                q_dict["topic"] = sanitize_ai_output(q_dict.get("topic", ""))
                q_dict["category"] = sanitize_ai_output(q_dict.get("category", ""))
                
                # Ensure category matches requested if Gemini returned something else
                if q_dict["category"] not in ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]:
                    q_dict["category"] = category
                
                return Question(**q_dict)
            except Exception as e:
                last_error = e
                print(f"[generate_first_question] Attempt {attempt + 1} failed: {e}")
                continue

        raise InterviewEngineError(f"Failed to generate first question: {last_error}")

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def evaluate_and_generate_next(
        profile: CandidateProfile,
        current_q: Question,
        user_ans: str,
        current_diff: str,
        next_category: str,
        history: list[dict],
        is_last: bool = False
    ) -> dict:
        """
        Sends candidate answer and context to Gemini to perform three tasks:
        1. Evaluate the answer (Technical Accuracy, Depth, Confidence, Communication Clarity).
        2. Determine the next difficulty level (Easy, Medium, Hard, Expert) using standard rules:
           - Excellent answer -> increase difficulty
           - Average answer -> keep difficulty
           - Poor answer -> reduce difficulty
           (NEVER jump more than one level).
        3. Generate the next question of the next_category category tailored to the candidate's performance
           and resume details (unless is_last is True).
        """
        if not settings.GEMINI_API_KEY:
            raise InterviewEngineError(
                "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

        # Format history for prompt
        history_str = ""
        for idx, h in enumerate(history):
            history_str += (
                f"Question {idx+1} [{h['category']}] (Difficulty: {h['difficulty']}): {h['question']}\n"
                f"Answer: {h['answer']}\n"
                f"Evaluation: Accuracy: {h['evaluation']['accuracy']}/5, Depth: {h['evaluation']['depth']}/5, "
                f"Confidence: {h['evaluation']['confidence']}/5, Clarity: {h['evaluation']['clarity']}/5\n\n"
            )

        system_instruction = (
            "You are a professional technical interviewer conducting an adaptive technical interview for an internship placement.\n"
            "You must perform three tasks simultaneously:\n"
            "1. Evaluate the candidate's response to the current question across 4 metrics (each graded 1 to 5, where 5 is perfect):\n"
            "   - Technical Accuracy\n"
            "   - Depth of explanation\n"
            "   - Confidence shown\n"
            "   - Communication Clarity\n"
            "2. Decide on the next difficulty level based on the evaluation:\n"
            "   - Excellent answer (high scores, average >= 4.0): increase difficulty (Easy -> Medium -> Hard -> Expert)\n"
            "   - Average answer (average ~3.0): keep difficulty same\n"
            "   - Poor answer (average < 2.5): reduce difficulty (Expert -> Hard -> Medium -> Easy)\n"
            "   * Note: NEVER jump more than one level from the current difficulty.\n"
            f"3. Generate the next interview question. Requirements:\n"
            f"   - Category of next question MUST be: {next_category}\n"
            "   - The difficulty of next question should match the updated difficulty level.\n"
            "   - Tailor the question's concept: if the candidate is weak, ask a simpler follow-up; if strong, increase the technical depth (e.g. OOP -> Virtual Functions -> Virtual Table -> Diamond Problem -> Memory Layout).\n"
            "   - Avoid repeating concepts already tested in the interview history.\n"
            "   - If this is the last step, you can populate a dummy next question, but it will be ignored.\n\n"
            f"Candidate Name: {profile.name}\n"
            f"Skills: {', '.join(profile.skills)}\n"
            f"Projects: {', '.join(profile.projects)}\n\n"
            "Your output must be a single JSON object matching the requested schema."
        )

        prompt_text = (
            f"Interview History:\n{history_str}\n"
            f"Current Question: {current_q.text}\n"
            f"Current Category: {current_q.category}\n"
            f"Current Topic/Concept: {current_q.topic}\n"
            f"Current Difficulty: {current_diff}\n"
            f"Candidate Response: {user_ans}\n\n"
            f"Analyze and generate evaluation and the next question."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_instruction}
                ]
            },
            "generationConfig": {
                "temperature": 0.4,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "evaluation": {
                            "type": "object",
                            "properties": {
                                "accuracy": {"type": "integer", "description": "Score 1-5"},
                                "depth": {"type": "integer", "description": "Score 1-5"},
                                "confidence": {"type": "integer", "description": "Score 1-5"},
                                "clarity": {"type": "integer", "description": "Score 1-5"}
                            },
                            "required": ["accuracy", "depth", "confidence", "clarity"]
                        },
                        "difficulty_change": {
                            "type": "string",
                            "enum": ["Easy", "Medium", "Hard", "Expert"],
                            "description": "The updated difficulty level name."
                        },
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific strengths shown in this response."
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific weaknesses or gaps in this response."
                        },
                        "next_question": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "Next technical question text."},
                                "category": {
                                    "type": "string",
                                    "enum": ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]
                                },
                                "topic": {"type": "string", "description": "The concept tested."}
                            },
                            "required": ["text", "category", "topic"]
                        }
                    },
                    "required": ["evaluation", "difficulty_change", "strengths", "weaknesses", "next_question"]
                }
            }
        }

        headers = {"Content-Type": "application/json"}
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=40)
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise InterviewEngineError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")

                response_data = response.json()
                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                res_dict = json.loads(json_text)
                
                # Sanitize text outputs
                res_dict["strengths"] = [sanitize_ai_output(s) for s in res_dict.get("strengths", []) if s]
                res_dict["weaknesses"] = [sanitize_ai_output(w) for w in res_dict.get("weaknesses", []) if w]
                
                nq = res_dict.get("next_question", {})
                nq["text"] = sanitize_ai_output(nq.get("text", ""))
                nq["topic"] = sanitize_ai_output(nq.get("topic", ""))
                nq["category"] = sanitize_ai_output(nq.get("category", ""))
                if nq["category"] not in ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]:
                    nq["category"] = next_category
                
                # Enforce evaluation score bounds
                ev = res_dict.get("evaluation", {})
                for k in ["accuracy", "depth", "confidence", "clarity"]:
                    ev[k] = max(1, min(5, int(ev.get(k, 3))))
                
                return res_dict
            except Exception as e:
                last_error = e
                print(f"[evaluate_and_generate_next] Attempt {attempt + 1} failed: {e}")
                continue

        raise InterviewEngineError(f"Failed to evaluate response and generate next question: {last_error}")

    @staticmethod
    def calculate_next_difficulty(current_diff: str, suggested_diff: str) -> str:
        """
        Enforces that difficulty transitions never jump by more than 1 level
        between Easy, Medium, Hard, and Expert.
        """
        difficulties = ["Easy", "Medium", "Hard", "Expert"]
        if current_diff not in difficulties:
            current_diff = "Medium"
        if suggested_diff not in difficulties:
            suggested_diff = current_diff
            
        curr_idx = difficulties.index(current_diff)
        sugg_idx = difficulties.index(suggested_diff)
        
        # Enforce max 1 step change
        if sugg_idx > curr_idx + 1:
            sugg_idx = curr_idx + 1
        elif sugg_idx < curr_idx - 1:
            sugg_idx = curr_idx - 1
            
        return difficulties[sugg_idx]

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def generate_all_questions(profile: CandidateProfile, count: int = 8) -> list[Question]:
        """
        [Legacy / Deprecated method preserved for backward compatibility]
        Sends candidate profile details to Gemini in a single API call to generate
        all interview questions distributed across target category weights.
        """
        if not settings.GEMINI_API_KEY:
            raise InterviewEngineError(
                "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

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
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=35)
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise InterviewEngineError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")

                response_data = response.json()
                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                questions_dict = json.loads(json_text)
                
                questions_list = []
                for idx, q_dict in enumerate(questions_dict.get("questions", [])):
                    q_dict["id"] = f"Q{idx + 1}"
                    q_dict["text"] = sanitize_ai_output(q_dict.get("text", ""))
                    q_dict["topic"] = sanitize_ai_output(q_dict.get("topic", ""))
                    q_dict["category"] = sanitize_ai_output(q_dict.get("category", ""))
                    questions_list.append(Question(**q_dict))
                    
                if len(questions_list) == 0:
                    raise InterviewEngineError("Gemini generated zero questions.")
                return questions_list
            except Exception as e:
                last_error = e
                continue
        raise InterviewEngineError(f"Legacy generation failed: {last_error}")

    @staticmethod
    def initialize_session(profile: CandidateProfile, count: int = 8) -> InterviewSession:
        """
        Initializes the interview session by planning categories, generating Question 1,
        and setting up the Streamlit session state 'interview_state'.
        """
        from src.models.interview_state import InterviewState
        
        session_id = str(uuid.uuid4())
        
        # Plan the sequence of categories
        category_sequence = InterviewEngine.get_category_sequence(count)
        st.session_state["category_sequence"] = category_sequence
        
        # Generate Question 1 (Medium difficulty, category index 0)
        first_category = category_sequence[0]
        question_1 = InterviewEngine.generate_first_question(profile, first_category, "Medium")
        
        # Initialize the InterviewState model
        state = InterviewState(
            current_question_number=1,
            current_category=question_1.category,
            current_difficulty="Medium",
            question_history=[question_1.text],
            answer_history=[],
            evaluation_history=[],
            overall_technical_score=0.0,
            confidence_trend=[],
            current_strength_areas=[],
            current_weak_areas=[]
        )
        st.session_state["interview_state"] = state
        
        # Initialize session with only Question 1
        return InterviewSession(
            session_id=session_id,
            candidate_profile=profile,
            questions=[question_1],
            history=[],
            current_question_index=0,
            is_completed=False
        )

    @staticmethod
    def submit_answer(session: InterviewSession, answer: str) -> None:
        """
        Submits the candidate's response to the current question, calls Gemini to evaluate
        it and generate the next question, updates session history, and shifts difficulty.
        """
        from config.settings import DEFAULT_QUESTION_COUNT
        from src.models.interview_state import InterviewState
        
        if session.current_question_index >= DEFAULT_QUESTION_COUNT:
            raise InterviewEngineError("Interview is already completed.")
            
        current_q = session.questions[session.current_question_index]
        state: InterviewState = st.session_state.get("interview_state")
        if not state:
            raise InterviewEngineError("Interview state is not initialized.")
            
        # Get category sequence
        category_sequence = st.session_state.get("category_sequence")
        if not category_sequence:
            category_sequence = InterviewEngine.get_category_sequence(DEFAULT_QUESTION_COUNT)
            st.session_state["category_sequence"] = category_sequence
            
        # Check if this is the last question
        is_last = (session.current_question_index == DEFAULT_QUESTION_COUNT - 1)
        
        # Prepare next category
        next_category = category_sequence[min(session.current_question_index + 1, DEFAULT_QUESTION_COUNT - 1)]
        
        # Format the history list for prompt context
        formatted_history = []
        for i, qa in enumerate(session.history):
            eval_metrics = state.evaluation_history[i] if i < len(state.evaluation_history) else {"accuracy": 3, "depth": 3, "confidence": 3, "clarity": 3}
            formatted_history.append({
                "question": qa.question.text,
                "category": qa.question.category,
                "difficulty": state.question_history[i] if i < len(state.question_history) else "Medium",
                "answer": qa.user_answer,
                "evaluation": eval_metrics
            })
            
        # Call single API endpoint for Evaluation, Difficulty Update, and Question Generation
        res = InterviewEngine.evaluate_and_generate_next(
            profile=session.candidate_profile,
            current_q=current_q,
            user_ans=answer,
            current_diff=state.current_difficulty,
            next_category=next_category,
            history=formatted_history,
            is_last=is_last
        )
        
        # Extract response fields
        evaluation_scores = res["evaluation"]
        suggested_diff = res["difficulty_change"]
        new_strengths = res["strengths"]
        new_weaknesses = res["weaknesses"]
        next_q_data = res["next_question"]
        
        # Validate & Enforce transition bounds programmatically
        new_diff = InterviewEngine.calculate_next_difficulty(state.current_difficulty, suggested_diff)
        
        # Append QA pair to session history
        qa_pair = QAPair(
            question=current_q,
            user_answer=answer.strip(),
            evaluation=None # Will be fully populated qualitatively at the end by EvaluationEngine
        )
        session.history.append(qa_pair)
        
        # Update the state history lists
        state.answer_history.append(answer)
        state.evaluation_history.append(evaluation_scores)
        state.confidence_trend.append(evaluation_scores["confidence"])
        
        # Update strength and weakness areas
        for s in new_strengths:
            if s not in state.current_strength_areas:
                state.current_strength_areas.append(s)
        for w in new_weaknesses:
            if w not in state.current_weak_areas:
                state.current_weak_areas.append(w)
                
        # Calculate dynamic overall score
        total_eval_score = 0.0
        for ev in state.evaluation_history:
            total_eval_score += sum(ev.values())
        max_possible = len(state.evaluation_history) * 20.0
        state.overall_technical_score = round((total_eval_score / max_possible) * 100.0, 1) if max_possible > 0 else 0.0
        
        if not is_last:
            # Setup next question
            next_q_idx = session.current_question_index + 1
            next_q_id = f"Q{next_q_idx + 1}"
            next_q = Question(
                id=next_q_id,
                text=next_q_data["text"],
                category=next_q_data["category"],
                topic=next_q_data["topic"]
            )
            session.questions.append(next_q)
            
            # Update state for next question
            state.current_question_number = next_q_idx + 1
            state.current_category = next_q.category
            state.current_difficulty = new_diff
            state.question_history.append(next_q.text)
        else:
            # End of interview
            session.is_completed = True
            
        # Increment index in session
        session.current_question_index += 1
        
        # Save state back to st.session_state
        st.session_state["interview_state"] = state
