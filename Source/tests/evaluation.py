import os
from typing import Literal, List

from langchain.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, field_serializer

from Source.app.config.settings import get_settings
from Source.app.llms.openai_client import create_openai_model

class RejectionDetailItem(BaseModel):
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
    """A resume evaluation with details."""
    resume_summary: str = Field(description="A detailed, objective paragraph that summarizes the candidate's background, explicitly evaluates them against the provided Custom Evaluation Criteria, and calls out any major missing skills or red flags.")
    overall_score_percentage: int = Field(description="An integer from 0 to 100 representing the holistic fit")
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

os.environ.setdefault("LLM_PROVIDER", "groq")

model = create_openai_model(get_settings(), get_settings().active_evaluation_model_name)

def evaluate_resume(resume_txt :str, custom_evaluation_criteria :str, jd_details :str) -> dict:

    system_message = """
    You are an elite, highly objective technical hiring manager and ATS evaluation engine. Your job is to deeply analyze a candidate's resume against a specific Job Description (JD) and a set of custom Evaluation Criteria provided by the hiring team.

<core_directives>
1. SEMANTIC EVALUATION: Do NOT rely on simple keyword matching. Look for semantic evidence of the required skills, scale, impact, and competency.
2. EVIDENCE-ANCHORING: Be harsh but fair. Do not hallucinate experience that isn't explicitly written or strongly implied.
3. EXTREME SCANNABILITY: HR professionals are skimming this. The summary MUST be formatted using Markdown. You must use bullet points, bold text, and a rigid structure (Overview, Strong Matches, Gaps/Red Flags). Do not output a dense wall of text.
</core_directives>

<priority_disqualification_rules>
Evaluate the custom criteria with absolute priority. Populate `rejection_details` if any disqualification applies:
1. YOE: If experience is outside the required range, add an entry with criterion "YOE", JD = required range, Candidate = candidate's experience.
2. BUDGET: If expected compensation exceeds budget, add criterion "BUDGET" with JD = budget limit and Candidate = candidate expectation.
3. LOCATION: If location fails and candidate won't relocate, add criterion "LOCATION" with JD = required location and Candidate = candidate location/stance.
4. NOTICE_PERIOD: If notice period exceeds limit, add criterion "NOTICE_PERIOD" with JD = max allowed and Candidate = candidate's notice period.

Include one entry per failed criterion. If all pass, `rejection_details` MUST be [].
</priority_disqualification_rules>

<output_schema>
You MUST return your entire response as a valid, parsable JSON object. Do not include markdown blocks like ```json outside the object. 

The JSON must exactly match this structure:
{
  "resume_summary": "A Markdown-formatted evaluation. It MUST follow this exact structure:\\n\\n**Overview:** [1 sentence summarizing the candidate's core profile]\\n\\n**Strong Matches:**\\n* [Bullet 1 evaluating specific criteria]\\n* [Bullet 2 evaluating specific criteria]\\n\\n**Gaps & Concerns:**\\n* [Bullet 1 calling out missing criteria or red flags]\\n* [Bullet 2 calling out missing criteria or red flags]",
  "overall_score_percentage": [Integer from 0 to 100 representing the holistic fit],
  "rejection_details": [
    {
      "criterion": "YOE",
      "JD": "[Required value from JD or custom criteria]",
      "Candidate": "[Candidate's corresponding value]"
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

If no disqualifications apply, `rejection_details` MUST be []. Include only criteria the candidate actually failed — one object per failure (e.g. if only YOE and BUDGET fail, return two entries).
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

    response = model_with_structure.invoke([
        SystemMessage(content=system_message),
        HumanMessage(content=human_message)
    ])
    return response

if __name__ == "__main__":
    resume_txt = """
    John Doe is a software engineer with 5 years of experience in software development. He has worked on a variety of projects, including a web application, a mobile application, and a desktop application. He has a strong background in software development, with a focus on web development. He is a quick learner and is able to pick up new technologies quickly. He is a team player and is able to work well with others. He is a strong problem solver and is able to think critically to solve problems. He is a strong communicator and is able to communicate effectively with others. He is a strong leader and is able to lead others effectively. He is a strong problem solver and is able to think critically to solve problems. He is a strong communicator and is able to communicate effectively with others. He is a strong leader and is able to lead others effectively.
    """
    custom_evaluation_criteria = """
    1. Code Quality: Do they mention testing, CI/CD, or code review practices?
    2. Leadership: Have they mentored juniors?
    """
    jd_details = """
    We are looking for a software engineer with 5 years of experience in software development. We are looking for a software engineer with a strong background in software development, with a focus on web development. We are looking for a software engineer who is a quick learner and is able to pick up new technologies quickly. We are looking for a software engineer who is a team player and is able to work well with others. We are looking for a software engineer who is a strong problem solver and is able to think critically to solve problems. We are looking for a software engineer who is a strong communicator and is able to communicate effectively with others. We are looking for a software engineer who is a strong leader and is able to lead others effectively. We are looking for a software engineer who is a strong problem solver and is able to think critically to solve problems. We are looking for a software engineer who is a strong communicator and is able to communicate effectively with others. We are looking for a software engineer who is a strong leader and is able to lead others effectively.
    """
    print(evaluate_resume(resume_txt, custom_evaluation_criteria, jd_details))
