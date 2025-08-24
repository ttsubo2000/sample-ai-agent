from langchain_experimental.utilities import PythonREPL
from typing import Annotated
from mcp.server.fastmcp import FastMCP
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import contextlib
import sys

# MCP Server のインスタンス作成
mcp = FastMCP("PythonREPL")

# Python REPL ユーティリティの初期化
repl = PythonREPL()

@mcp.tool()
def python_repl(code: Annotated[str, "チャートを生成するために実行する Python コード"]) -> str:
    """
    Python コードを実行し、matplotlib のグラフが含まれる場合は base64 PNG 画像として返す。
    """
    try:
        # stdout の捕捉
        stdout = BytesIO()
        with contextlib.redirect_stdout(sys.stdout):
            exec(code, globals())

        # matplotlibの画像を base64 に変換
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        plt.close()

        return f"Successfully executed:\n```python\n{code}\n```\n\n![chart](data:image/png;base64,{img_base64})"
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
