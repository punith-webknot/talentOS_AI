from typing import Literal, List, Optional
import re

from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_serializer

from Source.app.llms.factory import get_evaluation_structured_model


class RejectionDetailItem(BaseModel):
    """A single failed disqualification criterion with JD vs candidate comparison."""

    criterion: Literal["YOE", "BUDGET", "LOCATION", "NOTICE_PERIOD"] = Field(
        description="The disqualification criterion tag that the candidate failed."
    )
    JD: str = Field(
        description="What was required for this criterion in the JD or custom evaluation criteria."
    )
    Candidate: str = Field(
        description="What the candidate has or stated in their resume for this criterion."
    )


class ResumeEvaluation(BaseModel):
    """A concise, high-signal resume evaluation containing strict disqualification checks."""

    resume_summary: str = Field(
        description="A hyper-concise, punchy Markdown summary of the candidate's alignment. "
        "Strictly adhere to the Markdown schema provided in the system prompt. "
        "Keep each bullet point to a single short sentence."
    )
    overall_score_percentage: int = Field(
        description="An integer from 0 to 100 representing the holistic fit. "
        "If the candidate is rejected, this score should reflect a low or zero value."
    )
    rejection_details: List[RejectionDetailItem] = Field(
        default_factory=list,
        description="One entry per failed disqualification criterion, each with JD vs Candidate values. "
        "Leave as an empty list [] if the candidate passes all baseline parameters."
    )

    @field_serializer("rejection_details")
    def serialize_rejection_details(
        self, value: List[RejectionDetailItem]
    ) -> List[dict[str, dict[str, str]]]:
        return [{item.criterion: {"JD": item.JD, "Candidate": item.Candidate}} for item in value]


async def evaluate_resume(
    resume_txt: str,
    custom_evaluation_criteria: str,
    jd_details: str,
) -> ResumeEvaluation:

    system_message = """
You are an objective technical ATS evaluation engine. Assess the candidate's resume against the Job Description (JD) and Custom Evaluation Criteria.

<disqualification_direction>
Rejection entries are only for criteria where the candidate is WORSE than what the JD requires. A candidate who is BETTER than the JD requirement is a PASS and MUST NEVER appear in `rejection_details`:
- YOE: required minimum. Candidate is BETTER when their experience is >= the required years.
- BUDGET: candidate's expected compensation vs the JD budget cap. Candidate is BETTER when their expected compensation is <= the budget.
- LOCATION: candidate is BETTER when they meet the required location or are willing to relocate.
- NOTICE_PERIOD: candidate is BETTER when their notice period is <= the JD limit (e.g. candidate 15 days vs JD limit 30 days is a PASS).
If the candidate satisfies or beats the JD requirement, the criterion is a PASS — do NOT list it, do NOT fill it, skip it entirely.
</disqualification_direction>

<priority_disqualification_rules>
Add a `rejection_details` entry ONLY for criteria the candidate FAILED:
1. YOE: If a Years of Experience minimum is explicitly provided, the candidate's experience MUST meet or exceed it. Add an entry ONLY if the candidate's experience is below the required minimum.
2. BUDGET: Add an entry ONLY if the candidate's expected compensation EXCEEDS the budget. If equal to or less than the budget, it is a PASS — do NOT add an entry.
3. LOCATION: Add an entry ONLY if the candidate's current location does not match the JD requirement AND they explicitly state they are NOT willing to relocate (or fail a strict location check given in custom criteria).
4. NOTICE_PERIOD: Add an entry ONLY if the candidate's notice period is LONGER than the specified limit. If it is equal to or shorter than the limit, it is a PASS — do NOT add an entry.

After applying all checks, `rejection_details` MUST contain ONLY the criteria the candidate FAILED. If the candidate passes every baseline rule, `rejection_details` MUST be an empty array [].
</priority_disqualification_rules>

<data_normalization_guardrails>
- Missing Data: If a data point required for disqualification (e.g., Notice Period, Location Willingness, or Expected CTC) is completely absent or unstated in the resume, do NOT reject the candidate based on that metric. Treat it as neutral, skip that check, and do not add a `rejection_details` entry for it.
- Time Handling: Handle "Immediate" or "serving notice" notice periods as 0 days. Normalize months to days (1 month = 30 days, 2 months = 60 days) before making evaluations against the threshold.
- Financial Scaling: Convert candidate salary expectations to Annual INR (LPA) before comparing against the budget threshold (e.g., if a candidate lists 1,00,000/month, calculate it as 12 LPA).
- Strict YOE Range: Treat YOE ranges strictly as provided. If a candidate's experience is below the minimum floor or completely above the maximum ceiling, they must be rejected under 'YOE'.
</data_normalization_guardrails>

<core_directives>
1. SEMANTIC MATCHING: Look for actual engineering evidence, not just keywords.
2. HYPER-CONCISE & PUNCHY: Write with extreme brevity. Avoid filler words. Every bullet point must be exactly one short sentence.
3. SCANNABILITY: Use the strict Markdown structure below.
</core_directives>

<output_schema>
You MUST return your response as a valid, parsable JSON object matching this exact structure:
{
  "resume_summary": "**Overview:** [1 short sentence summarizing the candidate's core profile]\\n\\n**Strong Matches:**\\n* [1 short sentence on core technical alignment]\\n* [1 short sentence on experience alignment]\\n\\n**Gaps & Concerns:**\\n* [1 short sentence on a missing skill or red flag]\\n* [1 short sentence on another gap]",
  "overall_score_percentage": [Integer from 0 to 100],
  "rejection_details": [
    {
      "criterion": "YOE",
      "JD": "[Required YOE from JD or custom criteria]",
      "Candidate": "[Candidate's YOE from resume]"
    }
  ]
}

RULES FOR `rejection_details`:
- List ONLY criteria the candidate FAILED (one object per failed criterion).
- A criterion the candidate passes or beats is NEVER listed. In particular, do NOT list BUDGET when the candidate's expected compensation is within/under budget, and do NOT list NOTICE_PERIOD when the candidate's notice period is within/shorter than the limit.
- If the candidate passes every baseline rule, `rejection_details` MUST be [].
- Example: JD requires 5+ years, budget 50 LPA, notice period <= 30 days. Candidate has 2 years, expects 2 LPA, notice period 15 days. Only YOE fails, so `rejection_details` = [{"criterion": "YOE", "JD": "5+ years", "Candidate": "2 years"}]. BUDGET and NOTICE_PERIOD are PASSES and MUST be omitted.
</output_schema>
"""

    human_message = f"""
Evaluate this candidate. Be highly critical, punchy, and concise. Keep bullets to single sentences.

<job_description>
{jd_details}
</job_description>

<custom_evaluation_criteria>
{custom_evaluation_criteria}
</custom_evaluation_criteria>

<candidate_resume_text>
{resume_txt}
</candidate_resume_text>

Return ONLY the raw structured JSON object.
"""

    model_with_structure = get_evaluation_structured_model(ResumeEvaluation)

    result = await model_with_structure.ainvoke([
        SystemMessage(content=system_message),
        HumanMessage(content=human_message),
    ])
    if isinstance(result, ResumeEvaluation):
        result = _filter_false_positive_rejections(result)
    return result


# ── deterministic safety-net for rejection_details ──────────────────────────

_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")

_MONTH_DAYS = 30


def _extract_number(text: str) -> Optional[float]:
    """Return the first numeric value in a string (handles units/commas)."""
    if not text:
        return None
    match = _NUMBER_RE.search(text.replace(",", ""))
    return float(match.group(1)) if match else None


def _notice_days(text: str) -> Optional[float]:
    """Normalize a notice-period string to days. 'immediate'/'serving notice' -> 0."""
    lowered = (text or "").lower()
    if not lowered:
        return None
    if "immediate" in lowered or "serving notice" in lowered:
        return 0.0
    value = _extract_number(text)
    if value is None:
        return None
    if "month" in lowered:
        return value * _MONTH_DAYS
    return value


def _filter_false_positive_rejections(result: ResumeEvaluation) -> ResumeEvaluation:
    """Drop rejection entries where the candidate is actually BETTER than the JD.

    The LLM sometimes lists criteria the candidate satisfies (e.g. notice 15 days
    vs JD 30 days, or expected CTC 2 LPA vs budget 50 LPA). This deterministic
    pass removes such false positives so a passing candidate is never shown as
    rejected. Unparseable entries are kept to avoid dropping real rejections.
    """
    if not result.rejection_details:
        return result

    kept: List[RejectionDetailItem] = []
    for item in result.rejection_details:
        criterion = item.criterion
        jd_text = item.JD or ""
        candidate_text = item.Candidate or ""

        if criterion == "NOTICE_PERIOD":
            jd_days = _notice_days(jd_text)
            candidate_days = _notice_days(candidate_text)
            if jd_days is not None and candidate_days is not None and candidate_days <= jd_days:
                continue

        elif criterion == "BUDGET":
            jd_value = _extract_number(jd_text)
            candidate_value = _extract_number(candidate_text)
            if jd_value is not None and candidate_value is not None and candidate_value <= jd_value:
                continue

        elif criterion == "YOE":
            jd_value = _extract_number(jd_text)
            candidate_value = _extract_number(candidate_text)
            if jd_value is not None and candidate_value is not None and candidate_value >= jd_value:
                continue

        kept.append(item)

    result.rejection_details = kept
    return result