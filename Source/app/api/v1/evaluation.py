from fastapi import APIRouter
from pydantic import BaseModel

from Source.app.services.resume_evaluation import ResumeEvaluation, evaluate_resume

router = APIRouter()


class EvaluateResumeRequest(BaseModel):
    resume_txt: str
    custom_evaluation_criteria: str
    jd_details: str


@router.post("/evaluate-resume", response_model=ResumeEvaluation)
async def evaluate_resume_endpoint(payload: EvaluateResumeRequest):
    """Evaluate a candidate resume against a job description and custom criteria."""
    return await evaluate_resume(
        payload.resume_txt,
        payload.custom_evaluation_criteria,
        payload.jd_details,
    )
