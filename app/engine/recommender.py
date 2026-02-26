"""
Product recommendation engine with anti-cannibalization rules.

This is a deterministic rules engine — no LLM needed.
Implements the priority chain from the Stella v2.0 spec.
"""

import logging

from app.engine.classifier import ClusterScores
from app.models.lead import Lead, LeadCluster, LeadObjection
from app.models.recommendation import Product, ProductRecommendation

logger = logging.getLogger(__name__)

# Seniority levels that qualify for premium products
SENIOR_ROLES = {"head", "director", "c_level", "vp", "cto", "cdo", "cio"}
MANAGER_ROLES = {"manager", "lead", "senior"}

# Qualification community-to-product mapping
COMMUNITY_PRODUCT_MAP = {
    "Head de Tecnologia": Product.PROGRAMA_HEAD_TECH,
    "Head de Dados": Product.PROGRAMA_HEAD_DATA,
    "Tech Manager": Product.PROGRAMA_TECH_MANAGER,
    "Data Manager": Product.PROGRAMA_DATA_MANAGER,
    "AI for Tech Leaders": Product.PROGRAMA_AI_TECH,
    "AI for Business Leaders": Product.PROGRAMA_AI_BUSINESS,
}

MEMBERSHIP_PRODUCTS = {Product.MEMBERSHIP_HEAD_TECH, Product.MEMBERSHIP_HEAD_DATA}
PROGRAMA_PRODUCTS = {
    Product.PROGRAMA_HEAD_TECH,
    Product.PROGRAMA_HEAD_DATA,
    Product.PROGRAMA_TECH_MANAGER,
    Product.PROGRAMA_DATA_MANAGER,
    Product.PROGRAMA_AI_TECH,
    Product.PROGRAMA_AI_BUSINESS,
}


def recommend(lead: Lead, scores: ClusterScores) -> ProductRecommendation:
    """
    Determine the best product recommendation based on cluster scores,
    objection, qualification, and seniority.
    """
    cluster = lead.cluster or LeadCluster.SPECIFIC_CHALLENGE
    objection = lead.objection or LeadObjection.NONE
    seniority = (lead.seniority or "").lower()
    is_senior = seniority in SENIOR_ROLES

    has_financial = lead.has_financial_availability is not False
    has_live = lead.has_live_availability is not False
    has_financial_objection = objection in (LeadObjection.FINANCIAL_PERSONAL, LeadObjection.START_SMALLER)
    has_schedule_objection = objection == LeadObjection.SCHEDULE_LIMITATION
    has_corporate_objection = objection == LeadObjection.CORPORATE_DEPENDENCY

    # Determine best-fit programa from qualification scores
    best_programa = _best_programa_from_qualification(lead)

    # Determine membership type
    membership = _membership_for_profile(lead)

    # --- Anti-Cannibalization Priority Chain ---
    # Rules are ordered from most specific to least specific.
    # Objection-based rules take priority over cluster-based rules.

    # Rule 1: Structured evolution + financial + live + seniority → Membership
    if (
        cluster == LeadCluster.STRUCTURED_EVOLUTION
        and has_financial
        and has_live
        and is_senior
        and not has_financial_objection
    ):
        return ProductRecommendation(
            primary=membership,
            alternative=None,  # Don't add second option when Membership is primary
            reasoning="Evolução estruturada + disponibilidade financeira + senioridade elevada",
        )

    # Rule 2: Schedule objection → Trilhas (alt: Acervo) — check early
    if has_schedule_objection:
        return ProductRecommendation(
            primary=Product.TRILHAS,
            alternative=Product.ACERVO_ON_DEMAND,
            reasoning="Objeção de agenda declarada",
        )

    # Rule 3: Corporate dependency → Programa + institutional material
    if has_corporate_objection:
        programa = best_programa or Product.PROGRAMA_HEAD_TECH
        return ProductRecommendation(
            primary=programa,
            alternative=None,
            reasoning="Dependência de aprovação corporativa — sugerir material institucional",
        )

    # Rule 4: AI interest + senior → AI product (before generic rules)
    if lead.ai_interest and is_senior:
        ai_product = _best_ai_product(lead)
        return ProductRecommendation(
            primary=ai_product,
            alternative=best_programa or membership,
            reasoning="Interesse em IA + perfil sênior — prioridade estratégica AI",
        )

    # Rule 5: Specific challenge + financial objection → Trilhas
    if cluster == LeadCluster.SPECIFIC_CHALLENGE and has_financial_objection:
        return ProductRecommendation(
            primary=Product.TRILHAS,
            alternative=Product.ACERVO_ON_DEMAND,
            reasoning="Desafio específico + restrição financeira",
        )

    # Rule 6: Generic financial objection + live → Programa Executivo
    if has_financial_objection and has_live:
        programa = best_programa or Product.PROGRAMA_HEAD_TECH
        return ProductRecommendation(
            primary=programa,
            alternative=Product.TRILHAS,
            reasoning="Restrição financeira declarada + disponibilidade para ao vivo",
        )

    # Rule 7: Specific challenge + financial available → Programa Executivo
    if cluster == LeadCluster.SPECIFIC_CHALLENGE and has_financial and not has_financial_objection:
        programa = best_programa or Product.PROGRAMA_HEAD_TECH
        alt = None
        # For senior tech/data leaders, mention Membership as alternative
        if is_senior:
            alt = membership
        return ProductRecommendation(
            primary=programa,
            alternative=alt,
            reasoning="Desafio específico + disponibilidade financeira",
        )

    # Rule 8: Strategic evaluation → Programa + Trilhas as alt
    if cluster == LeadCluster.STRATEGIC_EVALUATION:
        programa = best_programa or Product.PROGRAMA_HEAD_TECH
        return ProductRecommendation(
            primary=programa,
            alternative=Product.TRILHAS,
            reasoning="Lead em fase de avaliação estratégica",
        )

    # Rule 9: Flexibility needed → Trilhas
    if cluster == LeadCluster.FLEXIBILITY_NEEDED:
        return ProductRecommendation(
            primary=Product.TRILHAS,
            alternative=Product.ACERVO_ON_DEMAND,
            reasoning="Necessidade de flexibilidade declarada",
        )

    # Default: Programa Executivo based on qualification
    programa = best_programa or Product.PROGRAMA_HEAD_TECH
    alt = membership if is_senior and has_financial else None
    return ProductRecommendation(
        primary=programa,
        alternative=alt,
        reasoning="Recomendação padrão baseada em qualificação",
    )


def _best_programa_from_qualification(lead: Lead) -> Product | None:
    """Pick the best Programa Executivo based on existing qualification scores."""
    if not lead.qualification_scores:
        return None

    best_score = 0
    best_product = None

    for entry in lead.qualification_scores:
        community = entry.get("community", "")
        score = entry.get("score", 0)
        review = entry.get("lead_review", "")

        if review != "FIT" or score < 3:
            continue

        product = COMMUNITY_PRODUCT_MAP.get(community)
        if product and score > best_score:
            best_score = score
            best_product = product

    return best_product


def _membership_for_profile(lead: Lead) -> Product:
    """Determine which Membership product fits the profile."""
    role = (lead.role or "").lower()
    qualifications = [q.get("community", "") for q in lead.qualification_scores] if lead.qualification_scores else []

    if any("dados" in q.lower() or "data" in q.lower() for q in qualifications):
        return Product.MEMBERSHIP_HEAD_DATA
    if "data" in role or "dados" in role or "analytics" in role:
        return Product.MEMBERSHIP_HEAD_DATA

    return Product.MEMBERSHIP_HEAD_TECH


def _best_ai_product(lead: Lead) -> Product:
    """Determine best AI product based on profile."""
    role = (lead.role or "").lower()

    # Business leaders without tech background
    non_tech_signals = any(
        kw in role for kw in ("marketing", "produto", "product", "growth", "financeiro", "jurídico", "operações", "cx")
    )
    if non_tech_signals:
        return Product.PROGRAMA_AI_BUSINESS

    # Default: AI for Tech Leaders
    return Product.PROGRAMA_AI_TECH
