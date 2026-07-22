from typing import List, Optional

from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from Source.app.llms.factory import get_evaluation_structured_model


MAX_QUESTIONS = 10
MAX_PHASES = 4


class ReviewPhase(BaseModel):
    """One interview phase with rating questions for that phase."""

    phase: str = Field(
        description="Short human-readable phase name reflecting a broad section of the interview "
        "(e.g. 'Background & Communication', 'Technical Judgment', 'Problem Solving')."
    )
    questions: List[str] = Field(
        description="Broad rating questions for this phase that HR or a next interviewer "
        "can interpret without deep technical context. Prefer 2–3 questions."
    )


class InterviewReviewQuestions(BaseModel):
    """Phase-wise rating questions for reviewing a candidate after an interview."""

    phases: List[ReviewPhase] = Field(
        description="At most 3–4 broad interview phases in order. "
        "Across all phases, total questions must not exceed 10."
    )


def _enforce_limits(result: InterviewReviewQuestions) -> InterviewReviewQuestions:
    """Cap phases and total questions so the response stays review-friendly."""
    phases: List[ReviewPhase] = []
    remaining = MAX_QUESTIONS

    for phase in result.phases[:MAX_PHASES]:
        if remaining <= 0:
            break
        questions = [q.strip() for q in phase.questions if q and q.strip()][:remaining]
        if not questions:
            continue
        phases.append(ReviewPhase(phase=phase.phase.strip(), questions=questions))
        remaining -= len(questions)

    return InterviewReviewQuestions(phases=phases)


_SHARED_DIRECTIVES = """
<core_directives>
1. PHASE BY PHASE: Collapse into at most 3–4 broad phases that cover the full spectrum
   (e.g. Background & Communication, Technical Judgment, Problem Solving / Troubleshooting, Overall Fit).
   Merge narrow sections. Use plain phase names — not tool or product jargon.
2. HARD LIMIT: Generate at most 10 questions total across all phases. Never exceed 10.
   Prefer 7–10 high-signal questions. Roughly 2–3 questions per phase.
3. BROAD, NOT HYPER-TECHNICAL: Ask about judgment, clarity, depth, structure, ownership, trade-off thinking,
   stakeholder communication, calm under pressure, and overall competency in that area.
   Do NOT name specific products, APIs, configs, or implementation details.
4. RATING QUESTIONS ONLY: Each item must be easy to score on a rating scale
   (prefer "How would you rate …?" / "How strong was the candidate's …?").
5. NO META LANGUAGE: Never mention the transcript, JD, conversation, recording, or that questions were generated.
6. AUDIENCE: Write so an HR partner or next-round interviewer understands what is being rated immediately.
</core_directives>

<good_examples>
- "How would you rate the clarity and structure of the candidate's explanations?"
- "How strong was the candidate's security and access-control judgment?"
- "How well did the candidate reason through architecture trade-offs?"
- "How effective was the candidate at diagnosing issues under pressure?"
- "How clearly did the candidate communicate risk and status to stakeholders?"
</good_examples>

<bad_examples>
- "How would you rate the candidate's dual-key coexistence rotation process?"
- "How would you rate Workload Identity Federation attribute conditions for Azure DevOps?"
- "How would you rate the candidate's ECMP / asymmetric routing firewall explanation?"
</bad_examples>

<output_schema>
Return a valid JSON object matching:
{
  "phases": [
    {
      "phase": "Background & Communication",
      "questions": [
        "How would you rate …?"
      ]
    }
  ]
}
Total questions across all phases must be <= 10. Use at most 4 phases.
</output_schema>
"""


async def generate_review_questions(
    transcription: Optional[str] = None,
    jd_details: Optional[str] = None,
) -> InterviewReviewQuestions:
    transcription = (transcription or "").strip() or None
    jd_details = (jd_details or "").strip() or None

    if transcription:
        system_message = f"""
You generate post-interview rating questions used by HR and the next interviewer to review a candidate.

The person filling these ratings may NOT have deep technical expertise and will NOT re-read the full transcript.
Questions must stay useful as standalone review criteria.

{_SHARED_DIRECTIVES}

STILL GROUNDED: Infer phases and themes from what was discussed, but generalize them into reviewable competencies.
"""
        human_message = f"""
Generate phase-wise, broad rating questions for HR / next-interviewer review from this interview.
Use at most 4 phases and at most 10 questions total.

<interview_transcription>
{transcription}
</interview_transcription>

Return ONLY the raw structured JSON object.
"""
    else:
        system_message = f"""
You generate interview rating questions used by HR and the next interviewer to review a candidate
for a role described in a Job Description (JD). No interview transcript is available.

Derive broad review phases from the role's responsibilities, required competencies, and seniority.
Questions must stay useful as standalone review criteria without requiring deep technical jargon.

{_SHARED_DIRECTIVES}

STILL GROUNDED: Infer phases and themes from the JD, but generalize them into reviewable competencies
for an interviewer to rate after speaking with the candidate.
"""
        human_message = f"""
Generate phase-wise, broad rating questions for HR / next-interviewer review based on this job description.
Use at most 4 phases and at most 10 questions total.

<job_description>
{jd_details}
</job_description>

Return ONLY the raw structured JSON object.
"""

    model_with_structure = get_evaluation_structured_model(InterviewReviewQuestions)

    result = await model_with_structure.ainvoke([
        SystemMessage(content=system_message),
        HumanMessage(content=human_message),
    ])
    return _enforce_limits(result)
