import os
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent


async def main(user_request: str):
    # 入力プロンプトを理解するためのLLMの定義
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.7,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_output_tokens=500,
    )

    # MCPサーバーの定義
    server_params = StdioServerParameters(
        command="python",
        args=["/Users/ttsubo/source/ttsubo2000/sample-ai-agent/mcp/yahoofinance_server.py"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # MCPサーバーをツールとして定義
            tools = await load_mcp_tools(session)

            # エージェントの定義(LangGraphでReActエージェントを定義)
            agent = create_react_agent(llm, tools)

            # 入力プロンプトの定義
            agent_response = await agent.ainvoke({
                "messages": user_request
            })

            # 出力結果の表示
            print(agent_response["messages"][3].content)


if __name__ == "__main__":
    import argparse

    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(
        description="ユーザー要求に基づいて要件定義を生成します"
    )
    # "task"引数を追加
    parser.add_argument(
        "--task",
        type=str,
        help="作成したいアプリケーションについて記載してください",
    )
    # "k"引数を追加
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="生成するペルソナの人数を設定してください（デフォルト:5）",
    )
    # コマンドライン引数を解析
    args = parser.parse_args()
    asyncio.run(main(user_request=args.task))
