from dataclasses import dataclass
from app.core.config import settings
from app.core.schemas import ChatRequest


@dataclass(frozen=True)
class RouteDecision:
    tier: str
    provider: str
    model: str
    reason: str


class ModelRouter:
    ACTION_BOOSTS = {
        "summarize_file": 0,
        "debug_file": 2,
        "explain_architecture": 2,
        "refactor_plan": 2,
        "release_readiness": 3,
        "incident_prevention": 3,
        "prd_to_architecture": 3,
        "brownfield_impact": 2,
        "security_review": 3,
        "performance_review": 2,
        "onboarding_explainer": 1,
        "pm_repo_analysis": 3,
        "reverse_prd": 3,
        "ui_reverse_prd": 3,
        "ui_release_audit": 3,
        "ui_incident_repro": 3,
        "admin_console_verifier": 3,
        "ux_accessibility_review": 3,
        "brownfield_flow_mapper_ui": 3,
        "onboarding_capture_ui": 3,
        "visual_regression_audit": 3,
        "api_contract_review": 2,
        "legacy_modernization_plan": 3,
        "test_strategy": 2,
    }

    def route(self, request: ChatRequest) -> RouteDecision:
        if request.route_preference != "auto":
            return self._from_tier(request.route_preference, "user override")

        message = request.message.lower()
        score = self.ACTION_BOOSTS.get(request.action_key or "", 0)

        if any(x in message for x in ["fix", "patch", "refactor", "run tests", "debug", "security", "performance", "contract"]):
            score += 2
        if any(x in message for x in ["architecture", "roadmap", "release", "incident", "migration", "brownfield", "greenfield", "prd", "product", "journey", "persona"]):
            score += 2
        if any(x in message for x in ["customer impact", "rollback", "tradeoff", "risk", "nonfunctional", "accessibility", "ux", "staging", "live ui"]):
            score += 1
        if request.repo_path:
            score += 1
        if request.computer_use and request.computer_use.start_url:
            score += 2
        if request.ide_context and request.ide_context.selected_text and len(request.ide_context.selected_text) > 2500:
            score += 2

        if score >= 6:
            return self._from_tier("premium", "complex code and reasoning task")
        if score >= 3:
            return self._from_tier("mid", "coding or tool-using request")
        return self._from_tier("cheap", "lightweight request")

    def _from_tier(self, tier: str, reason: str) -> RouteDecision:
        cheap_provider = getattr(settings, "cheap_provider", "mock")
        mid_provider = getattr(settings, "mid_provider", "openai_responses")
        premium_provider = getattr(settings, "premium_provider", "openai_responses")

        cheap_model = getattr(settings, "cheap_model", "gpt-4.1-mini")
        mid_model = getattr(settings, "mid_model", "gpt-4.1")
        premium_model = getattr(settings, "premium_model", "gpt-5")

        if tier == "premium":
            return RouteDecision("premium", premium_provider, premium_model, reason)
        if tier == "mid":
            return RouteDecision("mid", mid_provider, mid_model, reason)
        return RouteDecision("cheap", cheap_provider, cheap_model, reason)