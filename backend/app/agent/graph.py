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
    model="gemini-2.5-flash", streaming=True, api_key=settings.GEMINI_API_KEY
).bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    user_email: str

def call_model(state: AgentState):
    system_prompt = f"""
You are an AI assistant specializing in document analysis. The current user's
user_id is {state['user_id']}.

The user's uploaded PDF is already indexed and available through the
search_document tool. When the user asks for a summary, resume, synthesis, or
an exported PDF of the uploaded document, do not ask them to provide the
content again. First call search_document with a query describing the requested
summary. Then use the returned passages to write a faithful, well-structured
summary.

When the user says "generate a resume", "generate a résumé", "generate a
summary PDF", or asks to generate a PDF, this is an explicit request to create
and email a PDF file, not just to display a summary. After searching the
document, you MUST call generate_pdf_tool with the complete summary as content.
Use "Course Resume" as the document_title unless a more specific title is
available. The user's email is injected automatically; never ask the user for
it.
"""
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

def after_tools(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "name", None) == "generate_pdf_tool":
        return END
    return "model"

graph = StateGraph(AgentState)
graph.add_node("model", call_model)
graph.add_node("tools", ToolNode(tools))
graph.set_entry_point("model")
graph.add_conditional_edges(
    "model", should_continue, {"tools": "tools", END: END}
)
graph.add_conditional_edges(
    "tools", after_tools, {"model": "model", END: END}
)
agent = graph.compile()