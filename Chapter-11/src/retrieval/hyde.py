"""
HyDE — Hypothetical Document Embeddings (Section 4.3, Strategy 4; fix for Failure 6).

Questions and answers are written in different styles, so a question's embedding
may not land near the answer's. HyDE first asks a model to *write a fake answer*,
then embeds and searches with that — because the fake answer is written like a
real answer-document, it often lands closer to the genuine passages.

The catch: a confident-but-wrong hypothesis biases search toward false positives.
So `should_use_hyde` gates it to descriptive/content queries and disables it for
existence and comparison queries.
"""
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from src.models import get_fast_model, get_embeddings

_HYPOTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Generate a hypothetical document excerpt that would perfectly answer the "
     "question. Write 3-4 sentences as if you were the document being searched for. "
     "Use vocabulary appropriate to the domain."),
    ("human", "Question: {question}\n\nHypothetical document excerpt:"),
])


def build_hyde_retriever(vectorstore, model_name: str | None = None):
    model = get_fast_model(temperature=0.4)
    embeddings = get_embeddings()
    hypothesis_chain = _HYPOTHESIS_PROMPT | model | StrOutputParser()

    def hyde_search(query: str, k: int = 5) -> list[Document]:
        hypothesis = hypothesis_chain.invoke({"question": query})  # fake answer
        vector = embeddings.embed_query(hypothesis)                # embed the fake answer
        return vectorstore.similarity_search_by_vector(vector, k=k)

    return RunnableLambda(lambda q: hyde_search(q))


def should_use_hyde(query: str, model) -> bool:
    """
    True only for descriptive/content queries. HyDE hurts on existence and
    comparison queries, where a wrong guess biases search toward false positives.
    """
    response = model.invoke([HumanMessage(content=(
        f"Is this query asking whether something EXISTS, or asking to RETRIEVE / "
        f"DESCRIBE something?\n\nQuery: {query}\n\nAnswer with one word: EXISTS or RETRIEVE"
    ))])
    return "RETRIEVE" in response.content.upper()
