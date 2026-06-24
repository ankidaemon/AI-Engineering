"""
Conversation layer — a stateful wrapper around the LangGraph workflow.

Each WorkflowConversation owns one graph thread (thread_id) plus a summary-buffer
memory for post-analysis Q&A. It exposes three actions:

    analyze_document()    run the graph; may pause for human review
    submit_human_review() inject the reviewer's decision and resume
    ask()                 answer follow-up questions about the finished report

The graph's checkpointer (keyed by thread_id) holds the workflow state across a
human-review pause; the ConversationSummaryBufferMemory holds the Q&A history.
"""
import uuid
import logging

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage

from src.models import get_quality_model
from src.memory.conversation_memory import build_conversation_memory
from src.graph import workflow_app

logger = logging.getLogger(__name__)


class WorkflowConversation:
    _qa_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are an AI workflow assistant. A document has been analyzed and a "
         "report generated. Help the user understand the report and answer "
         "questions about it.\n\n"
         "Current report summary:\n{report_summary}\n\n"
         "Risk level: {risk_level}\n"
         "Key risk flags: {risk_flags}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    def __init__(self):
        self._memory          = build_conversation_memory()
        self._session_id      = str(uuid.uuid4())
        self._workflow_config = {"configurable": {"thread_id": self._session_id}}
        self._current_report  = None

    @property
    def session_id(self) -> str:
        return self._session_id

    def analyze_document(self, document_text: str, document_id: str = "DOC-001") -> dict:
        """Run the workflow. Returns 'awaiting_review' if it paused, else 'complete'."""
        initial_state = {
            "document_text":  document_text,
            "document_id":    document_id,
            "revision_count": 0,
            "errors":         [],
            "messages":       [HumanMessage(content=f"Analyze document: {document_id}")],
        }

        events = list(workflow_app.stream(
            initial_state, self._workflow_config, stream_mode="values"
        ))
        final_event = events[-1] if events else {}
        self._current_report = final_event.get("final_report")

        state = workflow_app.get_state(self._workflow_config)
        is_paused = bool(state.next)

        if self._current_report:
            self._memory.save_context(
                {"input": f"Analyze document {document_id}"},
                {"output": (f"Analysis complete. Risk level: "
                            f"{self._current_report.get('risk_level', 'unknown')}. "
                            f"Summary: {self._current_report.get('summary', '')[:200]}")},
            )

        return {
            "status":          "awaiting_review" if is_paused else "complete",
            "report":          self._current_report,
            "report_markdown": final_event.get("report_markdown", ""),
            "session_id":      self._session_id,
        }

    def submit_human_review(self, decision: str, feedback: str = "") -> dict:
        """Inject the human decision (approved | needs_revision) and resume."""
        workflow_app.update_state(
            self._workflow_config,
            {"human_decision": decision, "human_feedback": feedback},
            as_node="human_review_gate",
        )

        events = list(workflow_app.stream(
            None, self._workflow_config, stream_mode="values"
        ))
        final_event = events[-1] if events else {}
        self._current_report = final_event.get("final_report")

        state = workflow_app.get_state(self._workflow_config)
        is_paused = bool(state.next)   # a revision loop can pause for review again

        return {
            "status":          "awaiting_review" if is_paused else "complete",
            "report":          self._current_report,
            "report_markdown": final_event.get("report_markdown", ""),
            "session_id":      self._session_id,
        }

    def ask(self, question: str) -> str:
        """Answer a follow-up question grounded in the current report."""
        if not self._current_report:
            return "No document has been analyzed yet. Please submit a document first."

        history  = self._memory.load_memory_variables({})
        qa_chain = self._qa_prompt | get_quality_model() | StrOutputParser()

        answer = qa_chain.invoke({
            "report_summary": self._current_report.get("summary", ""),
            "risk_level":     self._current_report.get("risk_level", "unknown"),
            "risk_flags":     ", ".join(self._current_report.get("risk_flags", [])),
            "chat_history":   history.get("chat_history", []),
            "question":       question,
        })

        self._memory.save_context({"input": question}, {"output": answer})
        return answer
