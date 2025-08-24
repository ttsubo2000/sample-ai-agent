import os
import asyncio

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from PIL import Image
import matplotlib.pyplot as plt
import re
import base64
import io
import numpy as np


# base64データをデコードして表示
def display_base64_image(base64_string):
    # base64デコード
    image_data = base64.b64decode(base64_string)

    # バイトデータをPIL Imageに変換
    image = Image.open(io.BytesIO(image_data))

    # numpy配列に変換
    img_array = np.array(image)

    # matplotlib で表示
    plt.figure(figsize=(10, 8))
    plt.imshow(img_array)
    plt.axis('off')
    plt.show()

async def main(user_request: str):
    # 入力プロンプトを理解するためのLLMの定義
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.7,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        max_output_tokens=500,
    )

    # MCPサーバーの定義
    client = MultiServerMCPClient(
        {
            "stock": {
                "command": "python",
                "args": ["/Users/ttsubo/source/ttsubo2000/sample-ai-agent/mcp/yahoofinance_server.py"],
                "transport": "stdio",
            },
            "chart": {
                 "command": "python",
                 "args": ["/Users/ttsubo/source/ttsubo2000/sample-ai-agent/mcp/repl_server.py"],
                 "transport": "stdio",
            }
        }
    )
    # MCPサーバーをツールとして定義
    tools = await client.get_tools()

    # エージェントの定義(LangGraphでReActエージェントを定義)
    agent = create_react_agent(llm, tools)

    # 入力プロンプトの定義
    agent_response = await agent.ainvoke({
        "messages": user_request
    })

    # 出力結果の表示
    print(agent_response["messages"][3].content)

    # グラフの画像の表示
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', str(agent_response))
    if match:
        image_data = match.group(1)
        display_base64_image(image_data)
    else:
        print(agent_response)


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
