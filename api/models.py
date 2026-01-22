from pydantic import BaseModel
from typing import Optional, List

class ReviewRequest(BaseModel):
    diff: str
    language: Optional[str] = "python"

class ReviewResponse(BaseModel):
    submission_id: str
    status: str

class ReviewResult(BaseModel):
    submission_id: str
    status: str
    risk_score: int
    quality_score: int
    comments: List[str]
    flags: List[str]
