from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from app.ai.nodes import retrieve_node, answer_node

class ChatState(TypedDict):
    question: str
    evidence: list[dict]
    answer: str
    provider: str
    model: str
    api_key: str
    base_url: str
    db: object


def build_chat_graph():
    graph = StateGraph(ChatState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("answer", answer_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "answer")
    graph.add_edge("answer", END)
    return graph.compile()

chat_graph = build_chat_graph()
