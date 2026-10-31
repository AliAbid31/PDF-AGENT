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
MODEL_FALLBACKS = ("gemini-3.8-flash", "gemini-3.5-flash")


def _model_unavailable(error: Exception) -> bool:
    message = str(error).casefold()
    return any(
        marker in message
        for marker in (
            "404",
            "not_found",
            "not found",
            "503",
            "429",
            "unavailable",
            "resource exhausted",
        )
    )

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
and email a PDF file, not just to display a summary. After searching the document, you MUST call generate_pdf_tool with the complete
requested content as content. Choose a document_title that describes the
user's requested subject and document type; never use a fixed generic title
when the request provides a specific subject. The user's email is injected
automatically; never ask the user for it.

For document questions, base the answer only on the passages returned by
search_document. For summaries, request the complete document context, cover
all returned pages, preserve important definitions, examples, formulas, and
section order, and do not invent missing content. If the returned context is
insufficient, say which part could not be read instead of guessing.
"""
    messages = [{"role": "system", "content": system_prompt}] + list(
        state["messages"]
    )
    response = None
    last_error: Exception | None = None
    for model_name in MODEL_FALLBACKS:
        try:
            model = ChatGoogleGenerativeAI(
                model=model_name,
                streaming=True,
                api_key=settings.GEMINI_API_KEY,
            ).bind_tools(tools)
            response = model.invoke(messages)
            break
        except Exception as error:
            last_error = error
            if not _model_unavailable(error):
                raise
    if response is None:
        raise RuntimeError(
            "The configured Gemini models are unavailable. "
            "Please check the Gemini API key and enabled models."
        ) from last_error
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