from pydantic import BaseModel, Field
from typing import Literal

# Defined Question Categories
QuestionCategory = Literal["Resume & Projects", "AI/ML", "Software Engineering", "DSA & CS Fundamentals"]

class Question(BaseModel):
    """
    Pydantic data model representing a single interview question.
    """
    id: str = Field(description="Unique question identifier (e.g. Q1, Q2).")
    text: str = Field(description="The question text presented to the candidate.")
    category: QuestionCategory = Field(description="The category classification of the question.")
    topic: str = Field(description="The specific concept or topic covered by this question.")
