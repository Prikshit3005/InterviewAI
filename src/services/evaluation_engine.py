import json
import requests
from config import settings
from src.models.profile import CandidateProfile
from src.models.question import Question
from src.models.interview_session import InterviewSession
from src.models.evaluation import AnswerEvaluation, InterviewReport, CategoryScore
from src.utils.helpers import retry_on_rate_limit, sanitize_ai_output

class EvaluationEngineError(Exception):
    """Custom exception raised when evaluation or report generation fails."""
    pass

class EvaluationEngine:
    """
    Service responsible for batch-evaluating candidate answers and synthesizing
    the final evaluation report after the session concludes.
    """

    @staticmethod
    @retry_on_rate_limit(max_retries=5, initial_delay=3.0, backoff_factor=2.0)
    def generate_report(session: InterviewSession) -> InterviewReport:
        """
        Submits the entire Q&A transcript to Gemini in a single request to evaluate
        all answers and generate qualitative report summaries, then calculates
        quantitative score averages programmatically.

        Args:
            session (InterviewSession): The completed interview session containing Q&A history.

        Returns:
            InterviewReport: The finalized candidate report card with populated question feedback.

        Raises:
            EvaluationEngineError: If history is empty, API key is missing, or synthesis fails.
        """
        if not session.history:
            raise EvaluationEngineError("Cannot generate a report for an empty interview session.")

        if not settings.GEMINI_API_KEY:
            raise EvaluationEngineError("Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file.")

        # 1. Compile Q&A transcript for Gemini batch evaluation
        transcript_parts = []
        for i, qa in enumerate(session.history):
            transcript_parts.append(
                f"--- Question {i+1} [{qa.question.category}] - Topic: {qa.question.topic} ---\n"
                f"Q: {qa.question.text}\n"
                f"A: {qa.user_answer}\n"
            )
        
        transcript_summary = "\n".join(transcript_parts)

        # 2. Build API endpoint URL using Flash
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"

        # 3. System instructions outlining the interviewer grading criteria
        system_instruction = (
            "You are a Senior Tech Lead and Technical Recruiter. Your task is to analyze the candidate's complete technical interview transcript.\n\n"
            "First, evaluate each question's answer individually based on the following criteria:\n"
            "  - Technical Accuracy: Are the technical details correct?\n"
            "  - Depth of Knowledge: Does the candidate explain concepts deeply or just repeat surface keywords?\n"
            "  - Communication Clarity: Is the phrasing logical, professional, and clear?\n"
            "  - Completeness: Were all aspects of the question answered?\n"
            "For each answer, assign an individual score from 1 (completely incorrect/skipped) to 5 (excellent explanation).\n\n"
            "Second, synthesize the overall performance: summarize overall strengths, overall weaknesses, "
            "actionable study recommendations, and a recruiter summary narrative including a clear recommendation statement.\n\n"
            "Output a single JSON object matching the requested schema. The 'evaluations' list MUST have exactly the same "
            "number of elements as the questions in the transcript, in the exact same order."
        )

        prompt_text = (
            f"Candidate Profile Name: {session.candidate_profile.name}\n"
            f"Extracted Resume Skills: {', '.join(session.candidate_profile.skills)}\n\n"
            f"Interview Q&A Transcript:\n{transcript_summary}\n"
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
                "temperature": 0.2,  # Low temperature for objective assessment
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Synthesized technical and coding strengths observed across the session."
                        },
                        "weaknesses": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Systemic technical gaps, logical errors, or weaknesses identified."
                        },
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific actionable next steps to prepare for actual internship placement."
                        },
                        "summary": {
                            "type": "string",
                            "description": "Recruiter summary narrative explaining hiring recommendation."
                        },
                        "evaluations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "score": {
                                        "type": "integer", 
                                        "description": "Grading score from 1 (poor/skipped) to 5 (excellent)."
                                    },
                                    "accuracy_feedback": {"type": "string", "description": "Critique on technical details accuracy."},
                                    "depth_feedback": {"type": "string", "description": "Critique on depth of knowledge shown."},
                                    "clarity_feedback": {"type": "string", "description": "Critique on communication clarity."},
                                    "completeness_feedback": {"type": "string", "description": "Critique on answer completeness."},
                                    "strengths": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Correct points identified in the candidate answer."
                                    },
                                    "weaknesses": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Gaps or misconceptions identified in the candidate answer."
                                    }
                                },
                                "required": [
                                    "score", 
                                    "accuracy_feedback", 
                                    "depth_feedback", 
                                    "clarity_feedback", 
                                    "completeness_feedback",
                                    "strengths", 
                                    "weaknesses"
                                ]
                            },
                            "description": "List of individual evaluations matching each question sequentially."
                        }
                    },
                    "required": ["strengths", "weaknesses", "suggestions", "summary", "evaluations"]
                }
            }
        }

        headers = {"Content-Type": "application/json"}

        # Defensive 2-attempt validation retry loop
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                if response.status_code != 200:
                    error_msg = "Unknown error"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", "Unknown error")
                    except Exception:
                        pass
                    raise EvaluationEngineError(f"Gemini API Error (HTTP {response.status_code}): {error_msg}")

                response_data = response.json()
                
                if "candidates" not in response_data or not response_data["candidates"]:
                    raise EvaluationEngineError("Invalid response structure from Gemini API during report synthesis.")

                candidate_part = response_data["candidates"][0]["content"]["parts"][0]
                json_text = candidate_part["text"]
                report_dict = json.loads(json_text)
                
                # Sanitize outer report fields defensively
                report_dict["summary"] = sanitize_ai_output(report_dict.get("summary", ""))
                report_dict["strengths"] = [sanitize_ai_output(s) for s in report_dict.get("strengths", []) if s]
                report_dict["weaknesses"] = [sanitize_ai_output(w) for w in report_dict.get("weaknesses", []) if w]
                report_dict["suggestions"] = [sanitize_ai_output(sg) for sg in report_dict.get("suggestions", []) if sg]
                
                # Parse and back-populate individual question evaluations into history
                evaluations_list = report_dict.get("evaluations", [])
                for i, qa in enumerate(session.history):
                    if i < len(evaluations_list):
                        eval_dict = evaluations_list[i]
                        eval_dict["score"] = max(1, min(5, int(eval_dict.get("score", 3))))
                        
                        # Sanitize answer feedback fields defensively
                        eval_dict["accuracy_feedback"] = sanitize_ai_output(eval_dict.get("accuracy_feedback", ""))
                        eval_dict["depth_feedback"] = sanitize_ai_output(eval_dict.get("depth_feedback", ""))
                        eval_dict["clarity_feedback"] = sanitize_ai_output(eval_dict.get("clarity_feedback", ""))
                        eval_dict["completeness_feedback"] = sanitize_ai_output(eval_dict.get("completeness_feedback", ""))
                        eval_dict["strengths"] = [sanitize_ai_output(s) for s in eval_dict.get("strengths", []) if s]
                        eval_dict["weaknesses"] = [sanitize_ai_output(w) for w in eval_dict.get("weaknesses", []) if w]
                        
                        qa.evaluation = AnswerEvaluation(**eval_dict)
                    else:
                        # Fallback evaluation in case of missing index elements
                        qa.evaluation = AnswerEvaluation(
                            score=1,
                            accuracy_feedback="No evaluation was generated for this response.",
                            depth_feedback="",
                            clarity_feedback="",
                            completeness_feedback="",
                            strengths=[],
                            weaknesses=[]
                        )

                # Calculate scores in Python programmatically
                category_totals = {}
                category_counts = {}
                total_score = 0.0
                graded_questions_count = 0

                for qa in session.history:
                    if qa.evaluation:
                        score = float(qa.evaluation.score)
                        cat = qa.question.category
                        
                        category_totals[cat] = category_totals.get(cat, 0.0) + score
                        category_counts[cat] = category_counts.get(cat, 0) + 1
                        
                        total_score += score
                        graded_questions_count += 1

                overall_score_percentage = (total_score / (graded_questions_count * 5.0)) * 100.0 if graded_questions_count > 0 else 0.0

                category_scores_list = []
                for cat in ["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]:
                    if cat in category_totals:
                        cat_avg = category_totals[cat] / category_counts[cat]
                        cat_pct = (cat_avg / 5.0) * 100.0
                        category_scores_list.append(CategoryScore(category=cat, score=round(cat_pct, 1)))
                    else:
                        category_scores_list.append(CategoryScore(category=cat, score=0.0))

                report_dict["overall_score"] = round(overall_score_percentage, 1)
                report_dict["category_scores"] = [cs.model_dump() for cs in category_scores_list]
                
                if "evaluations" in report_dict:
                    del report_dict["evaluations"]

                report = InterviewReport(**report_dict)
                return report
            except (requests.exceptions.RequestException, ValueError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as e:
                last_error = e
                print(f"[generate_report] Validation attempt {attempt + 1} failed. Details: {str(e)}. Retrying...")
                continue
                
        raise EvaluationEngineError(
            f"Failed to synthesize evaluation report after multiple attempts. Last error: {str(last_error)}"
        )
