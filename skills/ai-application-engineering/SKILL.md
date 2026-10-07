---
name: ai-application-engineering
description: Build, refactor, diagnose, or review production LLM, agent, tool-calling, RAG, embedding, and model-runtime integrations across providers. Use for AI application code and workflow behavior, not ordinary prompt writing or generic image generation.
metadata:
  version: "0.4.12"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# AI Application Engineering

Engineer AI features from the repository's actual provider, model, runtime, data, and permission boundaries. Keep provider-specific details out of reusable application contracts where practical.

## Discover the active system

- Start with the changed path and its actual callers, manifests, configuration examples, and relevant tests; expand to architecture notes or adjacent pipelines only when a dependency or uncertainty requires them.
- Resolve the actual provider, model/API version, SDK, runtime, deployment target, authentication flow, rate limits, streaming/event model, persistence, and available evaluation tooling.
- For local models, also resolve hardware, serving runtime, precision, quantization, context limits, concurrency, and current benchmark evidence. Read [model-runtime.md](references/model-runtime.md) only when local inference or model selection is in scope.
- Do not assume that model names, reasoning controls, structured output, tool calling, embeddings, token accounting, or safety behavior transfer across providers or versions.

## Route the task

- For agents, assistants, tools, approvals, or multi-step state, read [agent-tool-systems.md](references/agent-tool-systems.md).
- For ingestion, chunking, embeddings, vector search, retrieval, reranking, grounding, or citations, read [rag-systems.md](references/rag-systems.md).
- Read both only when the feature actually crosses both boundaries.

## Implement the smallest complete change

- Preserve the current application's architecture and public contracts. Prefer typed provider adapters and explicit application-owned state over provider response objects leaking through the codebase.
- Separate deterministic application logic from model decisions. Validate model and tool inputs and outputs at trust boundaries.
- Keep secrets server-side and out of source, logs, commits, client bundles, examples, and generated artifacts.
- Treat prompts, tool schemas, model parameters, retrieval settings, and evaluation datasets as versioned behavior. Change only the requested layer and document any compatibility impact.
- Do not make nondeterministic output a hidden correctness dependency. Use validation, bounded retry, fallback, approval, or deterministic post-processing when reliability requires it.
- Do not add a framework, vector database, tracing service, or model provider when the existing stack can satisfy the requirement.

## Verify and report

- Use focused unit or contract tests for deterministic code, schema validation for structured boundaries, and recorded fixtures or provider mocks where live calls are unnecessary.
- Run live or end-to-end checks only when the task requires them and credentials, cost, permissions, data handling, and environment access are authorized.
- Evaluate changed behavior against representative cases and explicit failure conditions. Separate code correctness, model/retrieval quality, and provider availability; compare end-to-end latency and total task cost, including retries and recovery, before claiming an efficiency improvement.
- Report the exact provider/model/runtime exercised, actual checks, blocked live boundaries, and any results that remain probabilistic or environment-specific.
