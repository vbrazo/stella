from app.engine.classifier import ClusterScores
from app.engine.recommender import recommend
from app.models.lead import Lead, LeadCluster, LeadObjection
from app.models.recommendation import Product


def _make_lead(**kwargs) -> Lead:
    defaults = {
        "phone": "5511999999999",
        "seniority": "head",
        "cluster": LeadCluster.SPECIFIC_CHALLENGE,
        "objection": LeadObjection.NONE,
        "has_financial_availability": True,
        "has_live_availability": True,
    }
    defaults.update(kwargs)
    return Lead(**defaults)


def _default_scores(**overrides) -> ClusterScores:
    defaults = {
        "structured_evolution": 0.2,
        "specific_challenge": 0.5,
        "flexibility_needed": 0.1,
        "strategic_evaluation": 0.2,
    }
    defaults.update(overrides)
    return ClusterScores(**defaults)


def test_membership_priority_for_senior_with_evolution():
    """Rule 1: Senior + financial + live + evolution → Membership."""
    lead = _make_lead(
        seniority="head",
        cluster=LeadCluster.STRUCTURED_EVOLUTION,
        has_financial_availability=True,
        has_live_availability=True,
    )
    scores = _default_scores(structured_evolution=0.8)
    rec = recommend(lead, scores)
    assert rec.primary in (Product.MEMBERSHIP_HEAD_TECH, Product.MEMBERSHIP_HEAD_DATA)
    assert rec.alternative is None  # No second option when Membership is primary


def test_programa_for_financial_objection_with_live():
    """Rule 6: Financial objection + live (non-specific cluster) → Programa."""
    lead = _make_lead(
        cluster=LeadCluster.STRUCTURED_EVOLUTION,  # Not specific_challenge
        objection=LeadObjection.FINANCIAL_PERSONAL,
        has_financial_availability=False,
        has_live_availability=True,
        seniority="manager",  # Not senior enough for Membership
    )
    scores = _default_scores(structured_evolution=0.6)
    rec = recommend(lead, scores)
    assert rec.primary in (
        Product.PROGRAMA_HEAD_TECH,
        Product.PROGRAMA_HEAD_DATA,
        Product.PROGRAMA_TECH_MANAGER,
        Product.PROGRAMA_DATA_MANAGER,
    )
    assert rec.alternative == Product.TRILHAS
    assert rec.alternative == Product.TRILHAS


def test_trilhas_for_schedule_objection():
    """Rule 5: Schedule objection → Trilhas."""
    lead = _make_lead(
        objection=LeadObjection.SCHEDULE_LIMITATION,
        has_live_availability=False,
    )
    scores = _default_scores()
    rec = recommend(lead, scores)
    assert rec.primary == Product.TRILHAS
    assert rec.alternative == Product.ACERVO_ON_DEMAND


def test_trilhas_for_budget_and_specific_challenge():
    """Rule 4: No financial + specific challenge → Trilhas."""
    lead = _make_lead(
        cluster=LeadCluster.SPECIFIC_CHALLENGE,
        objection=LeadObjection.FINANCIAL_PERSONAL,
        has_financial_availability=False,
    )
    scores = _default_scores(specific_challenge=0.7)
    rec = recommend(lead, scores)
    assert rec.primary == Product.TRILHAS


def test_no_auto_downgrade_without_objection():
    """Anti-cannibalization: never downgrade without explicit objection."""
    lead = _make_lead(
        seniority="head",
        cluster=LeadCluster.SPECIFIC_CHALLENGE,
        has_financial_availability=True,
        has_live_availability=True,
    )
    scores = _default_scores(specific_challenge=0.7)
    rec = recommend(lead, scores)
    # Should recommend Programa (not Trilhas) since no financial objection
    assert rec.primary != Product.TRILHAS
    assert rec.primary != Product.ACERVO_ON_DEMAND


def test_flexibility_cluster_recommends_trilhas():
    """Rule 8: Flexibility needed → Trilhas."""
    lead = _make_lead(cluster=LeadCluster.FLEXIBILITY_NEEDED)
    scores = _default_scores(flexibility_needed=0.8)
    rec = recommend(lead, scores)
    assert rec.primary == Product.TRILHAS


def test_ai_interest_boosts_ai_product():
    """Rule 9: AI interest + senior → AI product."""
    lead = _make_lead(
        seniority="head",
        ai_interest=True,
        cluster=LeadCluster.SPECIFIC_CHALLENGE,
    )
    scores = _default_scores()
    rec = recommend(lead, scores)
    assert rec.primary in (Product.PROGRAMA_AI_TECH, Product.PROGRAMA_AI_BUSINESS)


def test_corporate_dependency():
    """Rule 7: Corporate dependency → Programa (suggest institutional material)."""
    lead = _make_lead(objection=LeadObjection.CORPORATE_DEPENDENCY)
    scores = _default_scores()
    rec = recommend(lead, scores)
    assert rec.primary != Product.TRILHAS
    assert "corporativa" in rec.reasoning.lower() or "corporativo" in rec.reasoning.lower()


# --- Deterministic anti-cannibalization assertions ---


def test_membership_never_has_lower_tier_alternative():
    """When Membership is primary, alternative must be None."""
    lead = _make_lead(
        seniority="head",
        cluster=LeadCluster.STRUCTURED_EVOLUTION,
        has_financial_availability=True,
        has_live_availability=True,
    )
    scores = _default_scores(structured_evolution=0.9)
    rec = recommend(lead, scores)
    assert rec.primary in (Product.MEMBERSHIP_HEAD_TECH, Product.MEMBERSHIP_HEAD_DATA)
    assert rec.alternative is None


def test_schedule_objection_always_trilhas_regardless_of_cluster():
    """Schedule objection ALWAYS produces Trilhas as primary, for every cluster."""
    for cluster in LeadCluster:
        lead = _make_lead(
            cluster=cluster,
            objection=LeadObjection.SCHEDULE_LIMITATION,
            has_live_availability=False,
        )
        scores = _default_scores()
        rec = recommend(lead, scores)
        assert rec.primary == Product.TRILHAS, f"Failed for cluster {cluster}"


def test_trilhas_never_primary_without_flexibility_or_objection():
    """Trilhas should NOT be primary when lead has financial + live + no constraints."""
    lead = _make_lead(
        seniority="manager",
        cluster=LeadCluster.SPECIFIC_CHALLENGE,
        objection=LeadObjection.NONE,
        has_financial_availability=True,
        has_live_availability=True,
    )
    scores = _default_scores(specific_challenge=0.8)
    rec = recommend(lead, scores)
    assert rec.primary != Product.TRILHAS
    assert rec.primary != Product.ACERVO_ON_DEMAND


def test_all_cluster_objection_combinations_produce_valid_product():
    """Every cluster x objection combination must return a valid Product."""
    for cluster in LeadCluster:
        for obj in LeadObjection:
            lead = _make_lead(cluster=cluster, objection=obj)
            scores = _default_scores()
            rec = recommend(lead, scores)
            assert isinstance(rec.primary, Product), (
                f"Invalid primary for cluster={cluster}, objection={obj}"
            )
