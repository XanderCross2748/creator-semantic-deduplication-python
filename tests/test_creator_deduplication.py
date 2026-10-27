from src.creator_deduplication import CreatorDeduplicator


def test_near_duplicate_merges_and_distinct_record_is_new() -> None:
    assert CreatorDeduplicator.decide(0.91) == "merge"
    assert CreatorDeduplicator.decide(0.42) == "new"
