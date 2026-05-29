from src.config import settings

SYSTEM_PROMPT = """You are Research Assistant — a specialized AI that helps researchers conduct structured literature reviews.

Your responses follow four strict rules:

RULE 1 — GROUNDING
Answer questions using ONLY the information in the RETRIEVED PAPERS section below.
Do not use knowledge from your training that is not reflected in the retrieved papers.
If you know something from training but it is not in the retrieved papers, do not say it.

RULE 2 — CITATION
When you state a finding from a paper, cite it immediately after using this format: [Author et al., Year].
If the metadata does not include authors, use [Source: <title fragment>].
Every factual claim must have a citation. Uncited claims will be considered hallucinations.

RULE 3 — UNCERTAINTY
If the retrieved papers do not contain enough information to answer the question,
write exactly: "The retrieved papers do not address [specific aspect of the question]."
Do not speculate, infer, or complete the answer using training knowledge.

RULE 4 — SYNTHESIS
When multiple papers address the same topic, synthesize them rather than listing each separately.
Explicitly note agreements and contradictions between papers.

OUTPUT FORMAT:
- Use markdown headers (##, ###) to structure your response.
- Lead with a direct answer or executive summary (2-3 sentences).
- Follow with detailed supporting evidence.
- End with a ## Gaps in Retrieved Literature section if relevant gaps exist.
"""


def build_rag_messages(
    query: str,
    chunks: list[dict],
    conversation_history: str = ""
) -> list[dict]:
    context_section = _format_retrieved_context(chunks)
    user_content = _build_user_content(query, context_section, conversation_history)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content}
    ]


def _format_retrieved_context(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant papers were retrieved."

    lines = ["## RETRIEVED PAPERS\n"]
    for i, chunk in enumerate(chunks, start=1):
        meta    = chunk.get("metadata", {})
        title   = meta.get("title", "Unknown Title")
        authors = meta.get("authors", "Unknown Authors")
        pub     = meta.get("published", "")[:10]
        section = meta.get("section", "")
        score   = chunk.get("rrf_score", chunk.get("score", 0.0))

        lines.append(
            f"### Paper {i}\n"
            f"**Title:** {title}  \n"
            f"**Authors:** {authors}  \n"
            f"**Published:** {pub}  \n"
            f"**Section:** {section}  \n"
            f"**Relevance score:** {score:.4f}\n\n"
            f"{chunk['content']}\n"
            f"---\n"
        )
    return "\n".join(lines)


def _build_user_content(
    query: str,
    context: str,
    history: str
) -> str:
    parts = []
    if history.strip():
        parts.append(f"## CONVERSATION HISTORY\n{history}")
    parts.append(context)
    parts.append(f"## RESEARCH QUESTION\n{query}")
    return "\n\n".join(parts)


def build_query_expansion_messages(query: str) -> list[dict]:
    """
    Asks Llama 3.1 to generate three reformulations of the user's query.
    Query expansion increases retrieval recall by covering different phrasings
    of the same underlying research question.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are a search query specialist. "
                "Rewrite the given research question in three alternative ways "
                "to maximize retrieval coverage. "
                "Output exactly three numbered queries and nothing else. "
                "Do not include explanations or introductory text."
            )
        },
        {
            "role": "user",
            "content": (
                f"Original query: {query}\n\n"
                "Generate 3 reformulations using:\n"
                "1. Different technical vocabulary\n"
                "2. More specific framing\n"
                "3. Broader conceptual framing"
            )
        }
    ]
