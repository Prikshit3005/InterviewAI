from pydantic import BaseModel, Field
from typing import List

class CandidateProfile(BaseModel):
    """
    Pydantic data model representing a candidate's parsed resume profile.
    Used for structured output from the Gemini API and validation.
    """
    name: str = Field(description="The full name of the candidate, or empty string if not found.")
    email: str = Field(description="The email address of the candidate, or empty string if not found.")
    skills: List[str] = Field(
        default_factory=list,
        description="A list of technical skills, programming languages, libraries, databases, and tools."
    )
    education: List[str] = Field(
        default_factory=list,
        description="A list of degrees, schools, and years attended."
    )
    projects: List[str] = Field(
        default_factory=list,
        description="A list of project names along with a brief description or context."
    )
