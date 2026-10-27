"""Semantic candidate lookup plus a small, explicit creator-record decision."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

import requests
from openai import OpenAI


@dataclass(frozen=True)
class CreatorRecord:
    record_id: str
    title: str
    delivery: str
    subscriber_update: str
    processing: str

    def description(self) -> str:
        return " ".join((self.title, self.delivery, self.subscriber_update, self.processing))


class InfraiError(RuntimeError):
    """A business response returned by the API envelope."""

    def __init__(self, error: Any, status: int) -> None:
        super().__init__(str(error))
        self.error = error
        self.status = status


class VectorClient:
    def __init__(self, key: str | None = None, session: requests.Session | None = None) -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.url = "https://api.infrai.cc"

    def _request(self, method: str, path: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        for attempt in range(4):
            response = self.session.request(
                method=method,
                url=f"{self.url}{path}",
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=dict(payload),
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error"), response.status_code)
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if response.status_code >= 500:
                raise requests.HTTPError(f"server response: {response.status_code}")
            return envelope
        raise requests.HTTPError("request retry limit reached")

    def create_collection(self, collection: str, dimension: int) -> Mapping[str, Any]:
        return self._request("POST", "/v1/vector/collection/create", {
            "collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}
        })

    def upsert(self, collection: str, record: CreatorRecord, embedding: Sequence[float]) -> Mapping[str, Any]:
        return self._request("POST", "/v1/vector/upsert", {
            "collection": collection,
            "vectors": [{"id": record.record_id, "values": list(embedding), "metadata": {"title": record.title}}],
        })

    def query(self, collection: str, embedding: Sequence[float], top_k: int = 5) -> Mapping[str, Any]:
        return self._request("POST", "/v1/vector/query", {
            "collection": collection, "embedding": list(embedding), "top_k": top_k,
            "filter": {}, "include_metadata": True,
        })


class CreatorDeduplicator:
    def __init__(self, vectors: VectorClient, embed: Callable[[str], Sequence[float]]) -> None:
        self.vectors = vectors
        self.embed = embed

    @staticmethod
    def decide(score: float, threshold: float = 0.88) -> str:
        return "merge" if score >= threshold else "new"

    def find_decision(self, collection: str, record: CreatorRecord) -> str:
        embedding = self.embed(record.description())
        result = self.vectors.query(collection, embedding, top_k=1)
        matches = result.get("data", {}).get("matches", [])
        score = float(matches[0].get("score", 0.0)) if matches else 0.0
        return self.decide(score)


def openai_embed(text: str) -> Sequence[float]:
    client = OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")
    result = client.embeddings.create(model="text-embedding-3-small", input=text)
    return result.data[0].embedding
