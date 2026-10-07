# RAG systems

Use this reference only when the task includes retrieval, embeddings, grounding, or citations.

## Trace the pipeline

Inspect each stage independently:

1. source authorization, freshness, normalization, and deletion handling
2. document segmentation and metadata retention
3. embedding model, dimensions, normalization, batching, and versioning
4. index or vector-store schema, namespaces, filters, and tenant isolation
5. query transformation, retrieval, hybrid search, and candidate count
6. reranking, deduplication, diversity, and score thresholds
7. context assembly, token budget, ordering, truncation, and citation mapping
8. generation behavior, refusal or no-answer behavior, and output validation
9. offline and online evaluation, latency, cost, and observability

Do not attribute a failed answer to generation before checking whether the required evidence was ingested, retrieved, ranked, and included in context.

## Change safely

- Preserve stable source identifiers and metadata needed for access control, citations, refresh, and deletion.
- Version incompatible chunking, embedding, or index changes and define reindex or migration behavior.
- Enforce authorization before or during retrieval, not after unauthorized content reaches the prompt.
- Keep citations tied to retrieved source spans. Do not fabricate a citation when grounding is missing.
- Define empty, low-confidence, conflicting, stale, and oversized result behavior.

## Evaluate

- Use representative queries with expected relevant sources, difficult negatives, missing-answer cases, and permission boundaries.
- Measure retrieval and generation separately. Useful signals can include recall, ranking quality, groundedness, citation correctness, answer usefulness, latency, and cost.
- Treat threshold and prompt tuning results as dataset- and model-specific. Record the versioned configuration actually evaluated.
