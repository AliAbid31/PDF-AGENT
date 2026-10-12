from typing import Annotated, Sequence
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from app.agent.tools import generate_pdf_tool, search_document
from app.core.config import settings

tools = [search_document, generate_pdf_tool]
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash", streaming=True, api_key=settings.GEMINI_API_KEY
).bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str

def call_model(state: AgentState):
    system_prompt = f"You are an AI assistant specializing in document analysis. The current user's user_id is : {state['user_id']}."
    messages = [{"role": "system", "content": system_prompt}] + list(
        state["messages"]
    )
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph = StateGraph(AgentState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("model")
graph.add_conditional_edges(
    "model", should_continue, {"tools": "tools", END: "model"}
)
graph.add_edge("tools", "model")
agent = graph.compile()