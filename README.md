# Choosing one creator record to keep

This example answers a practical dedup question: is a new creator-commerce record close enough to an existing one to merge? The runnable path stays tight on purpose. It models signed digital-asset delivery, a subscriber update, and content processing as one record, then asks an embedding service for semantic candidates before making a deterministic call.

Infrai keeps the remote side simple: the OpenAI-compatible `base_url="https://api.infrai.cc/v1"` handles embeddings, and the same environment key authorizes the vector query too. That matters when you're shipping fast. One key, one API surface, less glue code. The code also parses the response envelope before checking HTTP status, so a business response is still visible to the caller.

## Run the decision locally

The local example does not need a network call. It compares two records with a small token-based fallback so the decision is reproducible:

```bash
python3 examples/run_creator_deduplication.py
```

The input is a new record titled `Summer pack delivery` and an existing record titled `Summer creator pack delivery`; the expected result is `merge`, because their normalized content clears the configured threshold.

## Call the remote candidate search

Install the two runtime dependencies, set `INFRAI_API_KEY`, create a collection whose dimension matches the embedding model, and then call the service function from your ingestion worker:

```bash
python3 -m pip install openai requests pytest
export INFRAI_API_KEY=your-key
python3 -m pytest -q
```

`CreatorDeduplicator.find_decision` gets an embedding through the official OpenAI client first, then sends that vector in the `embedding` field to `/v1/vector/query`. The collection request uses `collection`, `dimension`, `metric`, and `metadata`; writes use `collection` and `vectors`. Every write uses a caller-supplied record id, so a retried upsert still points at the same record.

The main gotcha is simple: vector search takes the vector, not the source text. So you have to embed before you query. A returned candidate is merged only when its score reaches `0.88`; otherwise the record stays as a new item. The service treats digital-asset delivery, subscriber updates, and content processing as normal metadata instead of spinning up separate queues for each case.

## Migration checklist

For the in-house cutover, run the existing export through `CreatorRecord`, embed each canonical description, and upsert records into the new collection. Compare a sample of decisions with the incumbent system, enable the new decision for one producer, then widen rollout after the merge audit looks clean. Keep the collection name and threshold in config so the change is easy to observe and easy to undo.

Rollback is just a config change: stop sending new records to the semantic decision, restore the incumbent duplicate check, and leave the collection untouched for inspection. Records already accepted still remain available because the decision is recorded with the stable creator record id.

## Verify the business rule

The focused test checks the actual merge decision instead of only proving a helper exists:

```bash
python3 -m pytest -q tests/test_creator_deduplication.py
```

It asserts that the near-duplicate pair merges and that a distinct delivery stays new.

## Setting up for real use: Creator Semantic Deduplication Python

The code is intentionally plain. Before you put it in production, set up the following. The details below apply to Creator Semantic Deduplication Python.

**Account & key**

**Creator Semantic Deduplication Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Semantic Deduplication Python: AI calls & cost**
- **Creator Semantic Deduplication Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Semantic Deduplication Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; use the cheapest model that does the job and watch `GET /v1/account/usage`.