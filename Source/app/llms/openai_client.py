import os
from langchain_openai import ChatOpenAI
from Source.app.config.settings import settings

# Bind key so LangChain picks it up automatically
os.environ["OPENAI_API_KEY"] = settings.openai_api_key

model = ChatOpenAI(model=settings.model_name)