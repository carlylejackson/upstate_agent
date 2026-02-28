from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.services.escalation_service import EscalationService
from app.services.llm_service import LLMService
from app.services.policy_service import PolicyService
from app.services.retrieval_service import RetrievalService


class AgentState(TypedDict, total=False):
    query: str
    channel: str
    session_id: str
    intent: str
    confidence: float
    deterministic_response: str | None
    references: list[dict]
    response_text: str
    escalated: bool
    escalation_reason: str | None


@dataclass
class AgentResult:
    intent: str
    confidence: float
    response_text: str
    escalated: bool
    escalation_reason: str | None
    references: list[dict]


class AgentOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.policy_service = PolicyService(db)
        self.retrieval_service = RetrievalService(db)
        self.llm_service = LLMService()
        self.escalation_service = EscalationService(db)
        self.policies = self.policy_service.get_active_policies()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("deterministic", self._deterministic)
        graph.add_node("intent", self._intent)
        graph.add_node("retrieve", self._retrieve)
        graph.add_node("draft", self._draft)
        graph.add_node("guardrail", self._guardrail)
        graph.add_node("escalate", self._escalate)
        graph.add_node("finalize", self._finalize)

        graph.add_edge(START, "deterministic")
        graph.add_conditional_edges(
            "deterministic",
            self._route_after_deterministic,
            {"finalize": "finalize", "intent": "intent"},
        )
        graph.add_edge("intent", "retrieve")
        graph.add_edge("retrieve", "draft")
        graph.add_edge("draft", "guardrail")
        graph.add_conditional_edges(
            "guardrail",
            self._route_after_guardrail,
            {"finalize": "finalize", "escalate": "escalate"},
        )
        graph.add_edge("escalate", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    def run(self, session_id: str, channel: str, query: str) -> AgentResult:
        state = self.graph.invoke({"session_id": session_id, "channel": channel, "query": query})
        return AgentResult(
            intent=state.get("intent", "other_unknown"),
            confidence=float(state.get("confidence", 0.0)),
            response_text=state.get("response_text", ""),
            escalated=bool(state.get("escalated", False)),
            escalation_reason=state.get("escalation_reason"),
            references=state.get("references", []),
        )

    def _deterministic(self, state: AgentState) -> AgentState:
        response = self.policy_service.deterministic_response(state["query"], self.policies)
        if response:
            return {
                "deterministic_response": response,
                "response_text": response,
                "intent": "hours_location_contact",
                "confidence": 1.0,
                "references": [],
                "escalated": False,
            }
        return {"deterministic_response": None}

    def _intent(self, state: AgentState) -> AgentState:
        intent, confidence = self.llm_service.classify_intent(state["query"])
        return {"intent": intent, "confidence": confidence}

    def _retrieve(self, state: AgentState) -> AgentState:
        if state.get("intent") in {"hours_location_contact", "clinical_risk_or_emergency"}:
            return {"references": []}
        refs = self.retrieval_service.search(state["query"], top_k=5)
        return {"references": refs}

    def _draft(self, state: AgentState) -> AgentState:
        if state.get("deterministic_response"):
            return {}
        text = self.llm_service.generate_response(
            query=state["query"],
            intent=state.get("intent", "other_unknown"),
            references=state.get("references", []),
            policies=self.policies,
        )
        return {"response_text": text}

    def _guardrail(self, state: AgentState) -> AgentState:
        query = state["query"].lower()
        emergency_terms = [
            "chest pain",
            "can't breathe",
            "cannot breathe",
            "stroke",
            "severe dizziness",
            "suicidal",
        ]
        if any(term in query for term in emergency_terms):
            return {
                "escalated": True,
                "escalation_reason": "clinical_risk_or_emergency",
                "response_text": self.policies.get(
                    "emergency_disclaimer",
                    "If this is urgent, call 911 immediately.",
                ),
                "intent": "clinical_risk_or_emergency",
                "confidence": 1.0,
            }

        references = state.get("references", [])
        confidence = float(state.get("confidence", 0.0))
        intent = state.get("intent", "other_unknown")

        if (
            not references
            and intent
            not in {"hours_location_contact", "appointment_request", "clinical_risk_or_emergency"}
        ):
            return {
                "escalated": True,
                "escalation_reason": "low_confidence",
                "response_text": (
                    "I want to make sure you get an accurate answer. "
                    "I can escalate this to our team and collect callback details."
                ),
            }

        if confidence < 0.45:
            return {
                "escalated": True,
                "escalation_reason": "low_confidence",
            }

        if not self.policy_service.is_open_now(self.policies):
            callback_hint = (
                " We're currently outside business hours, but I can collect your details "
                "for callback during office hours."
            )
            return {"response_text": f"{state.get('response_text', '').strip()}{callback_hint}".strip()}

        return {"escalated": state.get("escalated", False)}

    def _escalate(self, state: AgentState) -> AgentState:
        ticket = self.escalation_service.create_ticket(
            session_id=state["session_id"],
            channel=state["channel"],
            reason=state.get("escalation_reason") or "manual_review",
            conversation_excerpt=state["query"],
        )
        response = state.get("response_text") or (
            "I have escalated this to our team. "
            "Please share your best callback number if you'd like follow-up."
        )
        return {
            "escalated": True,
            "response_text": f"{response} (Ticket {ticket.id})",
        }

    def _finalize(self, state: AgentState) -> AgentState:
        return {
            "intent": state.get("intent", "other_unknown"),
            "confidence": float(state.get("confidence", 0.6)),
            "references": state.get("references", []),
            "response_text": state.get("response_text", ""),
            "escalated": bool(state.get("escalated", False)),
            "escalation_reason": state.get("escalation_reason"),
        }

    @staticmethod
    def _route_after_deterministic(state: AgentState) -> str:
        if state.get("deterministic_response"):
            return "finalize"
        return "intent"

    @staticmethod
    def _route_after_guardrail(state: AgentState) -> str:
        if state.get("escalated"):
            return "escalate"
        return "finalize"
