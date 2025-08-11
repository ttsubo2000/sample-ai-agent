import tempfile
import subprocess
import os
#from ai_agent_for_q_and_a_app import compiled as compiled_graph
#from ai_agent_for_confirm_checkpoint import compiled_graph
from ai_agent_for_reqirement_system import DocumentationAgent
from langchain_google_genai import ChatGoogleGenerativeAI


def quick_display(compiled_graph, method="imgcat"):
    """
    シンプルな表示関数
    """
    try:
        # グラフ構造を取得してPNG生成
        graph = compiled_graph.get_graph()
        png_data = graph.draw_png()

        if method == "imgcat":
            # imgcatで表示
            process = subprocess.Popen(
                ["imgcat"],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate(input=png_data)

            if process.returncode == 0:
                print("✅ グラフが表示されました")
            else:
                print(f"❌ imgcatエラー: {stderr.decode()}")
                # フォールバックでファイル保存
                fallback_save(png_data)

        elif method == "preview":
            # Preview.appで表示
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_data)
                tmp_path = tmp.name

            subprocess.run(["open", tmp_path])
            print(f"✅ Previewでグラフを表示: {tmp_path}")

        else:
            # その他の場合はファイル保存
            fallback_save(png_data)

    except Exception as e:
        print(f"❌ 表示エラー: {e}")
        fallback_save(png_data)

def fallback_save(png_data):
    """
    フォールバック用のファイル保存
    """
    try:
        output_path = "langgraph_structure.png"
        with open(output_path, "wb") as f:
            f.write(png_data)
        print(f"💾 グラフを保存しました: {output_path}")

        # macOSの場合は自動で開く
        subprocess.run(["open", output_path])

    except Exception as e:
        print(f"❌ 保存エラー: {e}")


if __name__ == "__main__":
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    agent = DocumentationAgent(llm=llm)
    compiled_graph = agent.graph
    print("📊 グラフ構造を可視化中...")

    # 表示方法を選択（環境に応じて変更）
    display_methods = ["imgcat", "preview"]

    for method in display_methods:
        try:
            print(f"\n🖼️  {method}で表示を試行...")
            quick_display(compiled_graph, method)
            break  # 成功したら他の方法は試さない
        except Exception as e:
            print(f"❌ {method}での表示に失敗: {e}")
            continue
