import os
from typing import Union, Dict, Set, List, TypedDict, Annotated, Any
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
import yfinance as yf
import datetime as dt
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.volume import volume_weighted_average_price
import traceback
import pandas as pd


FUNDAMENTAL_ANALYST_PROMPT = """

あなたは、企業（シンボルが {company} の会社）のパフォーマンスを株価、テクニカル指標、および財務指標に基づいて評価することを専門とするファンダメンタルアナリストです。あなたのタスクは、指定された株式のファンダメンタル分析に関する包括的な要約を提供することです。

使用可能なツール：
1. **get_stock_prices**: 最新の株価、過去の価格データ、およびRSI、MACD、ドローダウン、VWAPなどのテクニカル指標を取得します。
2. **get_financial_metrics**: 売上高、1株当たり利益（EPS）、株価収益率（P/E）、負債比率などの主要な財務指標を取得します。

### あなたのタスク：
1. **株式シンボルを入力する**: 提供された株式シンボルを使用してツールをクエリし、関連情報を収集します。
2. **データを分析する**: ツールからの結果を評価し、潜在的な抵抗線、主要なトレンド、強み、または懸念点を特定します。
3. **要約を提供する**: 以下を強調する簡潔で構造化された要約を作成します：
   - 最近の株価動向、トレンド、および潜在的な抵抗線。
   - テクニカル指標から得られる重要な洞察（例：株が買われすぎているのか売られすぎているのか）。
   - 財務指標に基づく財務の健全性とパフォーマンス。
### 制約条件：
 - 提供されたツールから得られるデータのみを使用してください。
 - 推測的な言葉を避け、観察可能なデータやトレンドに焦点を当ててください。
 - ツールがデータを提供できなかった場合、その旨を要約で明確に記載してください。

### 出力フォーマット：
以下の形式で応答してください：

"stock": "<株式シンボル>",
"price_analysis": "<株価動向の詳細な分析>",
"technical_analysis": "<全てのテクニカル指標に基づく時系列分析の詳細>",
"financial_analysis": "<財務指標に基づく詳細な分析>",
"final Summary": "<上記の分析に基づく総合的な結論>",
"Asked Question Answer": "<上記の詳細と分析に基づく質問への回答>"

応答は客観的で簡潔、かつ実用的なものにしてください。
"""

class State(TypedDict):
    messages: Annotated[list, add_messages]
    stock: str


@tool
def get_stock_prices(ticker: str) -> Union[Dict, str]:
    """指定されたティッカーの過去の株価データとテクニカル指標を取得します。"""
    try:
        data = yf.download(
            ticker,
            start=dt.datetime.now() - dt.timedelta(weeks=24*3),
            end=dt.datetime.now(),
            interval='1wk'
        )
        df= data.copy()
        if len(df.columns[0]) > 1:
          df.columns = [i[0] for i in df.columns]
        data.reset_index(inplace=True)
        data.Date = data.Date.astype(str)

        indicators = {}

        # Momentum Indicators
        rsi_series = RSIIndicator(df['Close'], window=14).rsi().iloc[-12:]
        indicators["RSI"] = {date.strftime('%Y-%m-%d'): int(value) for date, value in rsi_series.dropna().to_dict().items()}
        sto_series = StochasticOscillator(
            df['High'], df['Low'], df['Close'], window=14).stoch().iloc[-12:]
        print(sto_series)
        indicators["Stochastic_Oscillator"] = {date.strftime('%Y-%m-%d'): int(value) for date, value in sto_series.dropna().to_dict().items()}

        macd = MACD(df['Close'])
        macd_series = macd.macd().iloc[-12:]
        print(macd_series)
        indicators["MACD"] = {date.strftime('%Y-%m-%d'): int(value) for date, value in macd_series.to_dict().items()}
        macd_signal_series = macd.macd_signal().iloc[-12:]
        print(macd_signal_series)
        indicators["MACD_Signal"] = {date.strftime('%Y-%m-%d'): int(value) for date, value in macd_signal_series.to_dict().items()}

        vwap_series = volume_weighted_average_price(
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            volume=df['Volume'],
        ).iloc[-12:]
        indicators["vwap"] = {date.strftime('%Y-%m-%d'): int(value) for date, value in vwap_series.to_dict().items()}

        return {'stock_price': data.to_dict(orient='records'), 'indicators': indicators}
    except Exception as e:
        return f"Error fetching price data: {str(e)}"

@tool
def get_financial_metrics(ticker: str) -> Union[Dict, str]:
    """指定されたティッカーの主要な財務比率を取得します。"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            'pe_ratio': info.get('forwardPE'),
            'price_to_book': info.get('priceToBook'),
            'debt_to_equity': info.get('debtToEquity'),
            'profit_margins': info.get('profitMargins')
        }
    except Exception as e:
        return f"Error fetching ratios: {str(e)}"

tools = [get_stock_prices, get_financial_metrics]


class StockAgent:
    def __init__(self, llm_with_tool: ChatGoogleGenerativeAI):

        self.llm_with_tool = llm_with_tool
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        graph_builder = StateGraph(State)

        graph_builder.add_node('fundamental_analyst', self.fundamental_analyst)
        graph_builder.add_edge(START, 'fundamental_analyst')
        graph_builder.add_node(ToolNode(tools))
        graph_builder.add_conditional_edges('fundamental_analyst', tools_condition)
        graph_builder.add_edge('tools', 'fundamental_analyst')
        graph_builder.add_edge('fundamental_analyst', END)
        return graph_builder.compile()

    def fundamental_analyst(self, state: State) -> dict[str, Any]:
        messages = [
            SystemMessage(content=FUNDAMENTAL_ANALYST_PROMPT.format(company=state['stock'])),
        ]  + state['messages']
        return {
            'messages': self.llm_with_tool.invoke(messages)
        }

    def run(self, ticker: str):
        input = {'messages':[('user', 'この株を買うべき？')], 'stock': ticker}
        events = self.graph.stream(input, stream_mode='values')
        for event in events:
            if 'messages' in event:
                event['messages'][-1].pretty_print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="ユーザー要求に基づいて要件定義を生成します"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        help="ティッカーコードを入力してください",
    )
    args = parser.parse_args()

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
    llm_with_tool = llm.bind_tools(tools)

    agent = StockAgent(llm_with_tool=llm_with_tool)
    agent.run(args.ticker)
