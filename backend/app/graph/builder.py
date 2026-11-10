"""Compile the fact-check LangGraph.

Flow:
    START -> fetch_article -> extract_claims -> retrieve_evidence
          -> graph_verify -+-> retrieve_evidence (evidence gap, bounded)
                            +-> adjudicate -> END
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import FactCheckNodes
from app.graph.state import FactCheckState


def route_after_graph_verify(state: FactCheckState) -> str:
    """Conditional edge: retry evidence once per configured round or adjudicate."""
    if state.evidence_sufficient:
        return "adjudicate"
    if state.evidence_round >= state.max_evidence_rounds:
        return "adjudicate"
    if not state.next_queries:
        return "adjudicate"
    return "retrieve_evidence"


def build_factcheck_graph(nodes: FactCheckNodes):
    """Build and compile the graph.

    The compiled graph keeps no per-request state and is safe to reuse across
    API requests. LangGraph merges node return values into ``FactCheckState``.
    """
    graph = StateGraph(FactCheckState)
    graph.add_node("fetch_article", nodes.fetch_article)
    graph.add_node("extract_claims", nodes.extract_claims)
    graph.add_node("retrieve_evidence", nodes.retrieve_evidence)
    graph.add_node("graph_verify", nodes.graph_verify)
    graph.add_node("adjudicate", nodes.adjudicate)

    graph.add_edge(START, "fetch_article")
    graph.add_edge("fetch_article", "extract_claims")
    graph.add_edge("extract_claims", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "graph_verify")
    graph.add_conditional_edges(
        "graph_verify",
        route_after_graph_verify,
        {
            "retrieve_evidence": "retrieve_evidence",
            "adjudicate": "adjudicate",
        },
    )
    graph.add_edge("adjudicate", END)
    return graph.compile()
