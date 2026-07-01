from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from Source.app.llms.factory import get_evaluation_structured_model


class ResumeEvaluation(BaseModel):
    """A concise, high-signal resume evaluation."""

    resume_summary: str = Field(
        description="A hyper-concise, punchy Markdown summary of the candidate's alignment. "
        "Strictly adhere to the Markdown schema provided in the system prompt. "
        "Keep each bullet point to a single short sentence."
    )
    overall_score_percentage: int = Field(
        description="An integer from 0 to 100 representing the holistic fit"
    )


async def evaluate_resume(
    resume_txt: str,
    custom_evaluation_criteria: str,
    jd_details: str,
) -> ResumeEvaluation:
    # 1. Shortened and focused system message
    system_message = """
You are an objective technical ATS evaluation engine. Assess the candidate's resume against the Job Description (JD) and Custom Evaluation Criteria.

<core_directives>
1. SEMANTIC MATCHING: Look for actual engineering evidence, not just keywords.
2. HYPER-CONCISE & PUNCHY: Write with extreme brevity. Avoid filler words. Every bullet point must be exactly one short sentence.
3. SCANNABILITY: Use the strict Markdown structure below.
</core_directives>

<output_schema>
You MUST return your response as a valid, parsable JSON object matching this exact structure:
{
  "resume_summary": "**Overview:** [1 short sentence summarizing the candidate's core profile]\n\n**Strong Matches:**\n* [1 short sentence on core technical alignment]\n* [1 short sentence on experience alignment]\n\n**Gaps & Concerns:**\n* [1 short sentence on a missing skill or red flag]\n* [1 short sentence on another gap]",
  "overall_score_percentage": [Integer from 0 to 100]
}
</output_schema>
"""

    # 2. Force the human message to demand strict brevity
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