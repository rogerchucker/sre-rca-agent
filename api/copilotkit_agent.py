"""CopilotKit integration for the RCA Agent using AG-UI protocol.

This module wraps the LangGraph orchestrator with the AG-UI LangGraphAgent
to enable conversational AI-powered incident investigations.
"""
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint

from core.orchestrator import build_graph


def create_rca_agent() -> LangGraphAgent:
    """Create a LangGraphAgent wrapping the RCA workflow graph."""
    return LangGraphAgent(
        name="rca-agent",
        graph=build_graph(),
    )


# Agent singleton for import
rca_agent = create_rca_agent()


def add_copilotkit_endpoint(app):
    """Add the CopilotKit/AG-UI endpoint to a FastAPI app."""
    add_langgraph_fastapi_endpoint(app, rca_agent, "/copilotkit")
