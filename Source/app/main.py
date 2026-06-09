import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from app.graphs.builder import graph
load_dotenv()

__all__ = ["graph"]

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "1"}}
    while True:
        user_input = input("Enter a message: ")
        if user_input == "exit":
            break
        result = graph.invoke(
            {
                "messages": [user_input],
                "next_agent": "END",
            },
            config,
        )
        print(f"ai: {result}")
        # print(f"ai: {result['messages'][-1]}")