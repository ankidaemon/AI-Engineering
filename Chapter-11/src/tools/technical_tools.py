"""
Technical-specialist tools (Section 2.3 / 6.x).

Like the legal tools, these are model-backed and fail soft. They give the
technical agent focused capabilities for specifications and architecture docs.
"""
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

from src.models import get_quality_model
from src.tools.legal_specific_tools import _parse_bullets


@tool
def extract_api_specs_tool(text: str) -> list[str]:
    """
    Extracts API endpoints, methods, and parameters described in a technical doc.
    Use this on sections that describe an interface, API, or service contract.
    """
    prompt = (
        f"From this technical text, list every API endpoint or interface mentioned, "
        f"with its method and key parameters if stated.\n\n{text[:3000]}\n\n"
        f"List each as a bullet point."
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return _parse_bullets(response.content)


@tool
def identify_dependencies_tool(text: str) -> list[str]:
    """
    Identifies external systems, services, and libraries a design depends on.
    Use this to map integration and supply-chain risk.
    """
    prompt = (
        f"List every external dependency (service, library, system, vendor) this "
        f"document relies on.\n\n{text[:3000]}\n\nList each as a bullet point."
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return _parse_bullets(response.content)


@tool
def flag_security_concerns_tool(text: str) -> list[str]:
    """
    Flags security and compliance concerns (auth, data handling, GDPR/SOC2/HIPAA).
    Use this on any architecture, data-flow, or design section.
    """
    prompt = (
        f"Review this technical text for security and compliance concerns "
        f"(authentication, data handling, encryption, GDPR/SOC2/HIPAA). For each "
        f"concern, say briefly why it matters.\n\n{text[:3000]}\n\n"
        f"List each as a bullet point."
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    return _parse_bullets(response.content)


@tool
def estimate_complexity_tool(text: str) -> dict:
    """
    Gives a rough complexity/maintainability read on a technical document.
    Returns a level (low/medium/high) and a one-line rationale.
    """
    prompt = (
        f"Rate the implementation complexity implied by this document as low, "
        f"medium, or high, and give a one-sentence rationale.\n\n{text[:2500]}"
    )
    response = get_quality_model(temperature=0).invoke([HumanMessage(content=prompt)])
    content = response.content.lower()
    level = "high" if "high" in content else "medium" if "medium" in content else "low"
    return {"complexity": level, "rationale": response.content.strip()}
