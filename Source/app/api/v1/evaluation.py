from typing import Annotated, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from Source.app.services.interview_review_questions import (
    InterviewReviewQuestions,
    generate_review_questions,
)
from Source.app.services.resume_evaluation import ResumeEvaluation, evaluate_resume

router = APIRouter()


class EvaluateResumeRequest(BaseModel):
    resume_txt: str
    custom_evaluation_criteria: str
    jd_details: str


class GenerateReviewQuestionsRequest(BaseModel):
    transcription: Optional[str] = Field(
        default=None,
        description="Interview transcription. Prefer this when available.",
        examples=["Interviewer: Tell me about your background.\nCandidate: I have 10 years..."],
    )
    jd_details: Optional[str] = Field(
        default=None,
        description="Job description. Required when transcription is not provided.",
        examples=["Senior GCP Architect responsible for IAM, networking, and HA design."],
    )


@router.post("/evaluate-resume", response_model=ResumeEvaluation)
async def evaluate_resume_endpoint(payload: EvaluateResumeRequest):
    """Evaluate a candidate resume against a job description and custom criteria."""
    return await evaluate_resume(
        payload.resume_txt,
        payload.custom_evaluation_criteria,
        payload.jd_details,
    )


@router.post("/generate-review-questions", response_model=InterviewReviewQuestions)
async def generate_review_questions_endpoint(
    payload: Annotated[
        Optional[GenerateReviewQuestionsRequest],
        Body(),
    ] = None,
):
    """Generate rating questions from an interview transcription, or from JD if no transcript.

    - **transcription**: preferred when available
    - **jd_details**: required when transcription is missing
    """
    payload = payload or GenerateReviewQuestionsRequest()
    transcription = (payload.transcription or "").strip() or None
    jd_details = (payload.jd_details or "").strip() or None

    if not transcription and not jd_details:
        raise HTTPException(
            status_code=422,
            detail="Either jd_details or transcription should be sent.",
        )

    return await generate_review_questions(
        transcription=transcription,
        jd_details=jd_details,
    )
