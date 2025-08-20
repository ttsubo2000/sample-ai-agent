import os
import operator
from datetime import datetime
from typing import Annotated, Any

from common.reflection_manager import ReflectionManager, TaskReflector
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from ai_agent_09_for_self_reflection import ReflectiveAgent


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ReflectiveAgentを使用してタスクを実行します（Self-reflection）"
    )
    parser.add_argument("--task", type=str, required=True, help="実行するタスク")
    args = parser.parse_args()

    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )

    anthropic_llm = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        temperature=0.0,
    )

    reflection_manager = ReflectionManager(file_path="tmp/cross_reflection_db.json")
    anthropic_task_reflector = TaskReflector(
        llm=anthropic_llm, reflection_manager=reflection_manager
    )

    agent = ReflectiveAgent(
        llm=gemini_llm,
        reflection_manager=reflection_manager,
        task_reflector=anthropic_task_reflector,
    )

    result = agent.run(args.task)
    print(result)
