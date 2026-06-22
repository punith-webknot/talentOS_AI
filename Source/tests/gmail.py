import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_gmail_service
from langchain_openai import ChatOpenAI

from Source.app.config.settings import get_settings
from Source.app.utils.gmail_credentials import get_google_credentials_from_env

settings = get_settings()

credentials = get_google_credentials_from_env(
    token_file="token.json",
    scopes=["https://mail.google.com/"],
)
api_resource = build_gmail_service(credentials=credentials)
toolkit = GmailToolkit(api_resource=api_resource)

tools = toolkit.get_tools()
print(tools)

llm = ChatOpenAI(model=settings.model_name, temperature=0)

from langchain.agents import create_agent

agent_executor = create_agent(llm, tools)

example_query = "send an email to punithkumarnimmala@gmail.com thanking them for coffee."

stream = agent_executor.stream_events(
    {"messages": [("user", example_query)]},
    version="v3",
)
for snapshot in stream.values:
    snapshot["messages"][-1].pretty_print()
