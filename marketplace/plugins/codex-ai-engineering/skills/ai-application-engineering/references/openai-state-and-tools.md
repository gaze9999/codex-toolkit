# OpenAI state and tool discovery

Read only for OpenAI Responses/Agents API history replay, compaction, early stopping or deferred discovery. Identify the API, exact model, SDK and state owner before changing a request. These API rules do not describe Codex App internals.

## Responses history and completion

Keep the original output items needed by the next request, including reasoning and tool call/result relationships; `output_text` alone is not replayable history. For the documented GPT-5.4/GPT-5.5 tool-heavy or long-running flows, preserve assistant `phase` values when replaying history: `commentary` denotes an intermediate update and `final_answer` a completed answer. Do not add the field to user messages or invent a missing value. Diagnose serialization loss before changing prompts/models. With `previous_response_id`, let the API retain prior assistant state.

## Compaction modes

| Existing chaining mode | Next-request handling |
|---|---|
| Standalone `/responses/compact` | Send the entire returned window as-is, including retained items and the opaque compaction item; do not extract only the encrypted item |
| Server-side compaction with an input array | Follow the documented array chaining; items before the latest compaction item may be dropped |
| Server-side compaction with `previous_response_id` | Send the new message with the response ID; do not manually prune prior state |

Keep encrypted state separate from a human-readable handoff. Check item order, required tool results and the original task's acceptance after recovery. Preserve the original response/receipt and stop custom pruning when the mode or required items are unclear.

## Deferred tool discovery

- Responses API: add `tool_search` and mark selected functions or MCP server definitions with `defer_loading: true` on a supported model. Inside namespaces, mark the functions, not the namespace object. Names/descriptions remain visible at the searchable surface; schemas arrive after discovery.
- Agents API functions: tool definitions are eager by default. Explicit deferral also needs `tool_search` plus each selected function's flag; the session still submits the full definitions to the service.
- Agents API MCP/plugin tools: the runtime handles discovery when the model/provider supports it. Use that API's MCP connection schema; do not copy the Responses MCP declaration or put a function flag on the server.

Discovery changes model-context loading, not data-transfer authority or permission to execute. Compare actual loaded tools, successful calls, input/cached-input usage and latency under matching tasks; changed loaded sets may affect caching. Preserve the existing loading strategy if tools become undiscoverable or required behavior regresses. Live calls and paid comparisons need the task's existing authorization.

## Sources and scoped verification

Official documentation checked 2026-10-27: [assistant phase](https://developers.openai.com/api/docs/guides/reasoning#phase-parameter), [conversation state](https://developers.openai.com/api/docs/guides/conversation-state), [compaction](https://developers.openai.com/api/docs/guides/compaction), [tool search](https://developers.openai.com/api/docs/guides/tools-tool-search).

For a changed adapter, start with its captured non-sensitive items or offline fixtures. Verify phase/item preservation, mode-specific next input and discovery configuration independently. Fixture success does not establish live model completion, tool authorization or savings.
