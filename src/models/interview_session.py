from pydantic import BaseModel, Field
from typing import List, Optional
from src.models.profile import CandidateProfile
from src.models.question import Question
from src.models.evaluation import AnswerEvaluation, InterviewReport

class QAPair(BaseModel):
    """
    Data model representing a Question, the candidate's Answer, and its silent Evaluation.
    """
    question: Question
    user_answer: Optional[str] = None
    evaluation: Optional[AnswerEvaluation] = None

class InterviewSession(BaseModel):
    """
    Pydantic data model representing the state of an active interview session.
    Tracks candidate context, pre-generated questions list, history of Q&A, progress, and the final synthesized evaluation report.
    """
    session_id: str = Field(description="A unique session identifier (UUID).")
    candidate_profile: CandidateProfile = Field(description="Structured profile of the candidate.")
    questions: List[Question] = Field(
        default_factory=list,
        description="List of pre-generated interview questions."
    )
    history: List[QAPair] = Field(
        default_factory=list,
        description="List of past questions, answers, and evaluations."
    )
    current_question_index: int = Field(
        0,
        description="The 0-based index of the question currently being answered."
    )
    is_completed: bool = Field(
        False,
        description="Flag indicating if the interview has reached its target question limit."
    )
    report: Optional[InterviewReport] = Field(
        None,
        description="Synthesized performance report generated upon interview completion."
    )
