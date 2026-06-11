from langchain.agents import create_agent
from source.app.llms.openai_client import model
from source.app.prompts.interview_agent_prompt import INTERVIEW_AGENT_PROMPT

def create_interview_agent():
    """
    Factory function to initialize the Interview Agent.
    This agent specializes in designing structured interview processes, 
    questions, and evaluation rubrics based on job requirements.
    """
    return create_agent(
        model,
        tools=[],
        system_prompt=INTERVIEW_AGENT_PROMPT,
    )