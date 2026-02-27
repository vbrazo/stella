import logging

from pydantic import BaseModel, Field

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.prompts.classifier import CLUSTER_CLASSIFICATION_SYSTEM
from app.models.lead import LeadCluster, LeadObjection

logger = logging.getLogger(__name__)


class ClusterScores(BaseModel):
    structured_evolution: float = Field(ge=0, le=1)
    specific_challenge: float = Field(ge=0, le=1)
    flexibility_needed: float = Field(ge=0, le=1)
    strategic_evaluation: float = Field(ge=0, le=1)


class IntentAnalysis(BaseModel):
    cluster_scores: ClusterScores
    detected_objection: str = "none"
    ai_interest: bool = False
    urgency: str = "medium"  # "low" | "medium" | "high"
    price_request: bool = False


async def classify_intent(
    llm: LLMProvider,
    lead_message: str,
    lead_context: str = "",
) -> IntentAnalysis:
    """Classify lead intent into clusters with confidence scores."""
    system = CLUSTER_CLASSIFICATION_SYSTEM.format(
        lead_message=lead_message,
        lead_context=lead_context,
    )

    try:
        analysis = await llm.complete_json_safe(
            system=system,
            messages=[{"role": "user", "content": lead_message}],
            schema=IntentAnalysis,
            temperature=0.3,
        )
    except Exception:
        logger.exception("Intent classification failed after retries, using fallback")
        # Safe fallback: uniform scores trigger ambiguity → routes to Qualifier
        analysis = IntentAnalysis(
            cluster_scores=ClusterScores(
                structured_evolution=0.25,
                specific_challenge=0.25,
                flexibility_needed=0.25,
                strategic_evaluation=0.25,
            ),
            detected_objection="none",
            ai_interest=False,
            urgency="medium",
            price_request=False,
        )

    logger.info(
        "Intent classification: scores=%s, objection=%s, ai=%s, price=%s",
        analysis.cluster_scores,
        analysis.detected_objection,
        analysis.ai_interest,
        analysis.price_request,
    )
    return analysis


def get_dominant_cluster(scores: ClusterScores) -> tuple[LeadCluster | None, float, bool]:
    """
    Determine dominant cluster and whether confidence is sufficient.
    Returns: (cluster, confidence, is_ambiguous)
    """
    score_map = {
        LeadCluster.STRUCTURED_EVOLUTION: scores.structured_evolution,
        LeadCluster.SPECIFIC_CHALLENGE: scores.specific_challenge,
        LeadCluster.FLEXIBILITY_NEEDED: scores.flexibility_needed,
        LeadCluster.STRATEGIC_EVALUATION: scores.strategic_evaluation,
    }

    sorted_scores = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
    top_cluster, top_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0

    gap = top_score - second_score
    is_ambiguous = top_score < settings.cluster_confidence_threshold or gap < settings.cluster_gap_threshold

    if is_ambiguous:
        logger.info(
            "Ambiguous classification: top=%s (%.2f), gap=%.2f",
            top_cluster,
            top_score,
            gap,
        )
        return top_cluster, top_score, True

    return top_cluster, top_score, False


def map_objection(objection_str: str) -> LeadObjection:
    """Map LLM objection string to LeadObjection enum."""
    mapping = {
        "financial_personal": LeadObjection.FINANCIAL_PERSONAL,
        "corporate_dependency": LeadObjection.CORPORATE_DEPENDENCY,
        "schedule_limitation": LeadObjection.SCHEDULE_LIMITATION,
        "start_smaller": LeadObjection.START_SMALLER,
        "lack_of_conviction": LeadObjection.LACK_OF_CONVICTION,
        "none": LeadObjection.NONE,
    }
    return mapping.get(objection_str, LeadObjection.NONE)
