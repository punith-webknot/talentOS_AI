from typing import Literal, List
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

<priority_disqualification_rules>
Evaluate the custom criteria with absolute priority. Populate `rejection_details` if any of the following apply. You must check ALL criteria and include ALL applicable failures:
1. YOE: If a Years of Experience range is explicitly provided in the custom criteria, the candidate's experience MUST fall within that range. If outside, add an entry with criterion "YOE", JD set to the required range from the JD/custom criteria, and Candidate set to the candidate's stated experience.
2. BUDGET: Compare candidate salary expectations to the budget. If the candidate's expected compensation exceeds the budget, add an entry with criterion "BUDGET", JD set to the budget limit, and Candidate set to the candidate's expected compensation. If equal to or less than the budget, do NOT disqualify.
3. LOCATION: If the candidate's current location does not match the JD requirement AND they explicitly indicate they are NOT willing to relocate (or fail a strict location check given in custom criteria), add an entry with criterion "LOCATION", JD set to the required location, and Candidate set to the candidate's location/relocation stance.
4. NOTICE_PERIOD: If the candidate's notice period is longer than the specified limit in the criteria, add an entry with criterion "NOTICE_PERIOD", JD set to the maximum allowed notice period, and Candidate set to the candidate's notice period.

If a candidate triggers multiple disqualifications, include one `rejection_details` entry per failed criterion. If they satisfy all baseline custom criteria rules, `rejection_details` MUST be [].
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
    },
    {
      "criterion": "LOCATION",
      "JD": "[Required location from JD or custom criteria]",
      "Candidate": "[Candidate's location or relocation stance]"
    },
    {
      "criterion": "BUDGET",
      "JD": "[Budget limit from JD or custom criteria]",
      "Candidate": "[Candidate's expected compensation]"
    }
  ]
}

If no disqualifications apply, `rejection_details` MUST be []. Include only criteria the candidate actually failed — one object per failure (e.g. if only YOE and BUDGET fail, return two entries, not all four).
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