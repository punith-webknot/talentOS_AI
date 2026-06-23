import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain.agents import create_agent
from langchain.messages import AIMessageChunk
from langchain_core.runnables import RunnableConfig
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import build_gmail_service

from Source.app.agents.context import AgentContext
from Source.app.config.settings import get_settings
from Source.app.llms.openai_client import get_model
from Source.app.utils.gmail_credentials import get_google_credentials_from_db

settings = get_settings()
TEST_USER_ID = "test1234"

# If no token exists for TEST_USER_ID, prints a Google login URL, waits for
# authorization, then saves the token directly to gmail_oauth_tokens (not token.json).
credentials = get_google_credentials_from_db(
    user_id=TEST_USER_ID,
    scopes=["https://mail.google.com/"],
    on_missing_token="oauth",
)
api_resource = build_gmail_service(credentials=credentials)
toolkit = GmailToolkit(api_resource=api_resource)

tools = toolkit.get_tools()
print(tools)

gmail_agent = create_agent(
    get_model(),
    tools=tools,
    context_schema=AgentContext,
)

example_query = "send an email to punithkumarnimmala@gmail.com thanking them for coffee."


async def run_agent() -> None:
    config: RunnableConfig = {"configurable": {"thread_id": "gmail-test"}}
    context = AgentContext(thread_id="gmail-test")

    async for chunk in gmail_agent.astream(
        {"messages": [{"role": "user", "content": example_query}]},
        config=config,
        context=context,
        stream_mode=["messages"],
        version="v2",
    ):
        if chunk["type"] != "messages":
            continue

        token, _metadata = chunk["data"]
        if not isinstance(token, AIMessageChunk):
            continue

        if token.tool_call_chunks:
            for tool_call in token.tool_call_chunks:
                if tool_call.get("name") is not None:
                    print(f"\n[tool] {tool_call['name']}")
                if tool_call.get("args") not in (None, ""):
                    print(tool_call["args"], end="", flush=True)
        elif token.text:
            print(token.text, end="", flush=True)

    print()


asyncio.run(run_agent())
