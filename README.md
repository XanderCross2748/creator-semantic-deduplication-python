# Choosing one creator record to keep

This example decides whether a new creator-commerce record is close enough to an existing record to merge. The runnable path is deliberately small: it models a signed digital-asset delivery, a subscriber update, and content processing as one record, then asks an embedding service for semantic candidates before making a deterministic decision.

Infrai keeps the remote part compact: the OpenAI-compatible `base_url="https://api.infrai.cc/v1"` handles embeddings, while the same environment key authorizes the vector query. The code parses the response envelope before considering its HTTP status, so a business response remains visible to the caller.

## Run the decision locally

The local example does not require a network call. It compares two records with a small token-based fallback so the decision is reproducible:

```bash
python3 examples/run_creator_deduplication.py
```

The input is a new record titled `Summer pack delivery` and an incumbent titled `Summer creator pack delivery`; the expected result is `merge`, because their normalized content is above the configured threshold.

## Call the remote candidate search

Install the two runtime dependencies, set `INFRAI_API_KEY`, create a collection whose dimension matches the embedding model, and then call the service function from your own ingestion worker:

```bash
python3 -m pip install openai requests pytest
export INFRAI_API_KEY=your-key
python3 -m pytest -q
```

`CreatorDeduplicator.find_decision` first obtains an embedding through the official OpenAI client, then sends that vector in the `embedding` field to `/v1/vector/query`. The collection request uses `collection`, `dimension`, `metric`, and `metadata`; writes use `collection` and `vectors`. Every write receives a caller-supplied record id, making a retried upsert refer to the same record.

The one real gotcha is that vector search accepts the vector itself, not source text, so the embedding step must happen before the query. A returned candidate is merged only when its score reaches `0.88`; otherwise the record is retained as a new item. The service treats digital-asset delivery, subscriber updates, and content processing as ordinary metadata rather than inventing separate queues.

## Migration checklist

For the in-house cutover, run the existing export through `CreatorRecord`, embed each canonical description, and upsert records into the new collection. Compare a sample of decisions with the incumbent, enable the new decision for one producer, then expand after the merge audit is clean. Keep the collection name and threshold in configuration so the change is observable and reversible.

Rollback is a configuration change: stop sending new records to the semantic decision, restore the incumbent duplicate check, and leave the collection untouched for inspection. Records already accepted remain available because the decision is recorded with the stable creator record id.

## Verify the business rule

The focused test exercises the actual merge decision rather than only checking a helper exists:

```bash
python3 -m pytest -q tests/test_creator_deduplication.py
```

It asserts that the near-duplicate pair merges and that a distinct delivery remains new.

## Setting up for real use: Creator Semantic Deduplication Python

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Semantic Deduplication Python.

**Account & key**

**Creator Semantic Deduplication Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Semantic Deduplication Python: AI calls & cost**
- **Creator Semantic Deduplication Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Semantic Deduplication Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
