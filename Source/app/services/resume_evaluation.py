from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from Source.app.llms.openai_client import model


class ResumeEvaluation(BaseModel):
    """A resume evaluation with details."""

    resume_summary: str = Field(
        description="A detailed, objective paragraph that summarizes the candidate's background, "
        "explicitly evaluates them against the provided Custom Evaluation Criteria, "
        "and calls out any major missing skills or red flags."
    )
    overall_score_percentage: int = Field(
        description="An integer from 0 to 100 representing the holistic fit"
    )


async def evaluate_resume(
    resume_txt: str,
    custom_evaluation_criteria: str,
    jd_details: str,
) -> ResumeEvaluation:
    system_message = """
    You are an elite, highly objective technical hiring manager and ATS evaluation engine. Your job is to deeply analyze a candidate's resume against a specific Job Description (JD) and a set of custom Evaluation Criteria provided by the hiring team.

<core_directives>
1. SEMANTIC EVALUATION: Do NOT rely on simple keyword matching. Look for semantic evidence of the required skills, scale, impact, and competency.
2. EVIDENCE-ANCHORING: Be harsh but fair. Do not hallucinate experience that isn't explicitly written or strongly implied.
3. EXTREME SCANNABILITY: HR professionals are skimming this. The summary MUST be formatted using Markdown. You must use bullet points, bold text, and a rigid structure (Overview, Strong Matches, Gaps/Red Flags). Do not output a dense wall of text.
</core_directives>

<output_schema>
You MUST return your entire response as a valid, parsable JSON object. Do not include markdown blocks like ```json outside the object.

The JSON must exactly match this structure:
{
  "resume_summary": "A Markdown-formatted evaluation. It MUST follow this exact structure:\n\n**Overview:** [1 sentence summarizing the candidate's core profile]\n\n**Strong Matches:**\n* [Bullet 1 evaluating specific criteria]\n* [Bullet 2 evaluating specific criteria]\n\n**Gaps & Concerns:**\n* [Bullet 1 calling out missing criteria or red flags]\n* [Bullet 2 calling out missing criteria or red flags]",
  "overall_score_percentage": [Integer from 0 to 100 representing the holistic fit]
}
</output_schema>
    """

    human_message = f"""
    Evaluate the following candidate based on the provided parameters.

<job_description>
{jd_details}
</job_description>

<custom_evaluation_criteria>
{custom_evaluation_criteria}
</custom_evaluation_criteria>

<candidate_resume_text>
{resume_txt}
</candidate_resume_text>

Process the evaluation and return ONLY the raw JSON object.
    """

    model_with_structure = model.with_structured_output(ResumeEvaluation)

    return await model_with_structure.ainvoke([
        SystemMessage(content=system_message),
        HumanMessage(content=human_message),
    ])
