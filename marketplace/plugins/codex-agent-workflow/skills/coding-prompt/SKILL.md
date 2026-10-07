---
name: coding-prompt
description: Create a concise cross-project coding-agent prompt and model recommendation only when the user explicitly asks for a prompt or handoff; do not use for direct implementation requests.
metadata:
  short-description: Concise cross-project coding prompt
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Coding Prompt

Produce a reusable coding-agent prompt only when explicitly requested. Infer the current project/context and preserve existing decisions. A prompt request does not authorize implementation, task creation or external messaging.

Read [workflow](references/workflow.md) for prompt content, execution context, model recommendation and output requirements. Follow its existing pattern reference only when useful. Keep copyable prompt text together, explanations/model advice outside it.

Return the requested artifact or confirmed operation with actual evidence and concrete gaps. Do not confuse prepared content with execution, parsing with runtime adoption or an intended check with a completed result.
