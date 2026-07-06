from typing import Literal, Optional, List
from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from Source.app.llms.factory import get_evaluation_structured_model


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
    rejected_status: List[Literal["YOE", "BUDGET", "LOCATION", "NOTICE_PERIOD", "NONE"]] = Field(
        default_factory=list,
        description="If the candidate fails any mandatory custom evaluation criteria, "
        "populate this list with all applicable reason tags: 'YOE', 'BUDGET', 'LOCATION', or 'NOTICE_PERIOD'. "
        "Leave as an empty list [] if the candidate passes all baseline parameters."
    )
    rejected_reason: Optional[str] = Field(
        default=None,
        description="A brief, clear sentence explaining all specific disqualification reasons (e.g., 'Candidate has insufficient YOE and does not match the required location'). "
        "Leave as None if rejected_status is empty."
    )


async def evaluate_resume(
    resume_txt: str,
    custom_evaluation_criteria: str,
    jd_details: str,
) -> ResumeEvaluation:

    system_message = """
You are an objective technical ATS evaluation engine. Assess the candidate's resume against the Job Description (JD) and Custom Evaluation Criteria.

<priority_disqualification_rules>
Evaluate the custom criteria with absolute priority. Populate `rejected_status` and `rejected_reason` if any of the following apply. You must check ALL criteria and include ALL applicable failures in the response array:
1. YOE: If a Years of Experience range is explicitly provided in the custom criteria, the candidate's experience MUST fall within that range. If outside, append 'YOE' to the status array.
2. BUDGET: Compare candidate salary expectations to the budget. If the candidate's expected compensation exceeds the budget, append 'BUDGET' to the status array. If it is equal to or less than the budget, do NOT disqualify them.
3. LOCATION: If the candidate's current location does not match the JD requirement AND they explicitly indicate they are NOT willing to relocate (or fail a strict location check given in custom criteria), append 'LOCATION' to the status array.
4. NOTICE_PERIOD: If the candidate's notice period is longer than the specified limit in the criteria, append 'NOTICE_PERIOD' to the status array.

If a candidate triggers multiple disqualifications, include ALL triggered tags in the `rejected_status` array and clearly mention all corresponding reasons inside `rejected_reason`. If they satisfy all baseline custom criteria rules, `rejected_status` MUST be [] and `rejected_reason` MUST be null.
</priority_disqualification_rules>

<data_normalization_guardrails>
- Missing Data: If a data point required for disqualification (e.g., Notice Period, Location Willingness, or Expected CTC) is completely absent or unstated in the resume, do NOT reject the candidate based on that metric. Treat it as neutral, skip that check, and do not append its status tag.
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
  "rejected_status": ["YOE" | "BUDGET" | "LOCATION" | "NOTICE_PERIOD" | "NONE"],
  "rejected_reason": "[Single brief sentence explaining all identified rejection reasons combined]" | NONE
}
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

    return await model_with_structure.ainvoke([
        SystemMessage(content=system_message),
        HumanMessage(content=human_message),
    ])