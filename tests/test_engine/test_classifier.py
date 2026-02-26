from app.engine.classifier import ClusterScores, get_dominant_cluster
from app.models.lead import LeadCluster


def test_clear_dominant_cluster():
    """High confidence, large gap → not ambiguous."""
    scores = ClusterScores(
        structured_evolution=0.8,
        specific_challenge=0.3,
        flexibility_needed=0.1,
        strategic_evaluation=0.1,
    )
    cluster, confidence, is_ambiguous = get_dominant_cluster(scores)
    assert cluster == LeadCluster.STRUCTURED_EVOLUTION
    assert confidence == 0.8
    assert not is_ambiguous


def test_ambiguous_when_low_confidence():
    """Low top score → ambiguous."""
    scores = ClusterScores(
        structured_evolution=0.4,
        specific_challenge=0.2,
        flexibility_needed=0.1,
        strategic_evaluation=0.1,
    )
    _, _, is_ambiguous = get_dominant_cluster(scores)
    assert is_ambiguous


def test_ambiguous_when_small_gap():
    """Close scores → ambiguous."""
    scores = ClusterScores(
        structured_evolution=0.7,
        specific_challenge=0.65,
        flexibility_needed=0.1,
        strategic_evaluation=0.1,
    )
    _, _, is_ambiguous = get_dominant_cluster(scores)
    assert is_ambiguous


def test_not_ambiguous_with_sufficient_gap():
    """Large enough gap → not ambiguous."""
    scores = ClusterScores(
        structured_evolution=0.7,
        specific_challenge=0.4,
        flexibility_needed=0.1,
        strategic_evaluation=0.1,
    )
    cluster, confidence, is_ambiguous = get_dominant_cluster(scores)
    assert cluster == LeadCluster.STRUCTURED_EVOLUTION
    assert not is_ambiguous
