"""The LangGraph flow.

    START -> search -> dedupe --(nothing fresh)--> deliver -> record -> END
                          |
                          v
                      summarize <-> validate (one retry with feedback)
                                       |
                                       v
                                    deliver
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from .deps import Deps
from .nodes.dedupe import dedupe
from .nodes.deliver import deliver, record
from .nodes.search import search
from .nodes.summarize import summarize
from .nodes.validate import validate
from .state import AgentState


def _after_dedupe(state: AgentState) -> str:
    return "summarize" if state.get("fresh") else "deliver"


def _after_validate(state: AgentState) -> str:
    return "summarize" if state.get("errors") else "deliver"


def build_graph(deps: Deps):
    g = StateGraph(AgentState)
    g.add_node("search", partial(search, deps=deps))
    g.add_node("dedupe", partial(dedupe, deps=deps))
    g.add_node("summarize", partial(summarize, deps=deps))
    g.add_node("validate", partial(validate, deps=deps))
    g.add_node("deliver", partial(deliver, deps=deps))
    g.add_node("record", partial(record, deps=deps))

    g.add_edge(START, "search")
    g.add_edge("search", "dedupe")
    g.add_conditional_edges("dedupe", _after_dedupe, ["summarize", "deliver"])
    g.add_edge("summarize", "validate")
    g.add_conditional_edges("validate", _after_validate, ["summarize", "deliver"])
    g.add_edge("deliver", "record")
    g.add_edge("record", END)
    return g.compile()
