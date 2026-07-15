from pydantic import BaseModel, Field
from typing import List

class AnswerEvaluation(BaseModel):
    """
    Pydantic data model representing the assessment of a candidate's single answer.
    """
    score: int = Field(
        ge=1, 
        le=5, 
        description="Overall grade from 1 (unacceptable/incorrect) to 5 (excellent technical explanation)."
    )
    accuracy_feedback: str = Field(
        description="Critique of the technical accuracy of facts and concepts stated by the candidate."
    )
    depth_feedback: str = Field(
        description="Analysis of how deeply the candidate explained the underlying engineering principles."
    )
    clarity_feedback: str = Field(
        description="Assessment of communication flow, terminology usage, and structural clarity."
    )
    completeness_feedback: str = Field(
        description="Evaluation of whether the candidate addressed all parts of the question."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Specific good concepts or correct points identified in the answer."
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Specific gaps, errors, or missed concepts identified in the answer."
    )

class CategoryScore(BaseModel):
    """
    Model storing score averages computed per category.
    """
    category: str = Field(description="The question category name.")
    score: float = Field(
        ge=0.0, 
        le=100.0, 
        description="The percentage score earned in this category (0-100)."
    )

class InterviewReport(BaseModel):
    """
    Model representing the compiled report after the interview session finishes.
    """
    overall_score: float = Field(
        ge=0.0, 
        le=100.0, 
        description="Programmatically calculated overall score out of 100."
    )
    category_scores: List[CategoryScore] = Field(
        default_factory=list,
        description="Averaged performance breakdown per category."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Overall technical and communicative strengths observed across the session."
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Areas of weakness, gaps in skills, or engineering concepts that require focus."
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable learning paths, projects, or study guides recommended to close gaps."
    )
    summary: str = Field(
        description="A comprehensive recruiter-style narrative summarizing the candidate's hiring recommendation."
    )
