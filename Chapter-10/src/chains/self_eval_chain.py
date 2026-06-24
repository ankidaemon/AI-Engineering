"""
Self-evaluation wrapper (Chapter 10, §4.4).

Wraps any generation chain in a generate -> evaluate -> (maybe) retry loop. A
cheap evaluator on the fast model scores the output; if it falls below the
threshold, revision guidance is fed back and the generation chain runs again,
up to `max_retries`.

This demonstrates the self-critique pattern with LCEL. The production workflow
expresses the same idea as an explicit LangGraph cycle (re_classify -> classify)
with a hard revision cap — see graph.py and Failure 1 (infinite agent loops).
"""
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.models import get_fast_model


class QualityEvaluation(BaseModel):
    score:             int       = Field(description="Quality score 1-10")
    issues:            list[str] = Field(description="Specific quality issues found")
    is_acceptable:     bool      = Field(description="True if score >= threshold and no critical issues")
    revision_guidance: str       = Field(description="Specific guidance for improvement if needed")


class SelfEvaluatingChain:
    def __init__(self, generation_chain, max_retries: int = 2, min_score: int = 7):
        self._chain       = generation_chain
        self._max_retries = max_retries
        self._min_score   = min_score
        self._eval_chain  = self._build_eval_chain()

    def _build_eval_chain(self):
        parser = JsonOutputParser(pydantic_object=QualityEvaluation)
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a quality evaluator. Assess the AI-generated content below. "
             "{format_instructions}"),
            ("human",
             "Original task: {task}\n\n"
             "Generated content:\n{content}\n\n"
             "Evaluate quality (1-10) and identify any issues."),
        ])
        return (
            prompt.partial(format_instructions=parser.get_format_instructions())
            | get_fast_model()
            | parser
        )

    def invoke(self, inputs: dict) -> dict:
        task   = inputs.get("task", "Document analysis")
        result = self._chain.invoke(inputs)
        evaluation: dict = {}

        for attempt in range(self._max_retries):
            evaluation = self._eval_chain.invoke({"task": task, "content": str(result)})

            if evaluation.get("is_acceptable", False):
                return {"result": result, "evaluation": evaluation, "attempts": attempt + 1}

            # Not acceptable — feed guidance back and retry (unless out of budget)
            if attempt < self._max_retries - 1:
                inputs = {
                    **inputs,
                    "revision_guidance": evaluation.get(
                        "revision_guidance", "Improve quality and completeness."
                    ),
                }
                result = self._chain.invoke(inputs)

        return {"result": result, "evaluation": evaluation, "attempts": self._max_retries}
