import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.creator_deduplication import CreatorDeduplicator, CreatorRecord


def local_similarity(left: str, right: str) -> float:
    left_words = set(left.lower().split())
    right_words = set(right.lower().split())
    return len(left_words & right_words) / len(left_words | right_words)


def main() -> None:
    incoming = CreatorRecord("new-42", "Summer pack delivery", "signed asset", "subscriber update", "processed")
    incumbent = CreatorRecord("old-17", "Summer creator pack delivery", "signed asset", "subscriber update", "processed")
    score = local_similarity(incoming.description(), incumbent.description())
    decision = CreatorDeduplicator.decide(score, threshold=0.55)
    print({"incoming": incoming.record_id, "candidate": incumbent.record_id, "score": round(score, 3), "decision": decision})


if __name__ == "__main__":
    main()
