from pydantic import BaseModel, Field
from typing import List, Dict, Any

class InterviewState(BaseModel):
    """
    Data model tracking the dynamic stats of an active adaptive interview session.
    Persists in Streamlit's session state.
    """
    current_question_number: int = Field(1, description="1-indexed current question number.")
    current_category: str = Field("Resume & Projects", description="The current active category.")
    current_difficulty: str = Field("Medium", description="The current difficulty level (Easy, Medium, Hard, Expert).")
    question_history: List[str] = Field(default_factory=list, description="List of questions asked so far.")
    answer_history: List[str] = Field(default_factory=list, description="List of answers provided by the candidate.")
    evaluation_history: List[Dict[str, int]] = Field(
        default_factory=list, 
        description="Detailed history of evaluations: [{'accuracy': int, 'depth': int, 'confidence': int, 'clarity': int}]"
    )
    overall_technical_score: float = Field(0.0, description="Overall technical score percentage (0 to 100).")
    confidence_trend: List[int] = Field(default_factory=list, description="Confidence scores out of 5 across questions.")
    current_strength_areas: List[str] = Field(default_factory=list, description="Ongoing list of identified technical strengths.")
    current_weak_areas: List[str] = Field(default_factory=list, description="Ongoing list of identified technical gap areas.")
