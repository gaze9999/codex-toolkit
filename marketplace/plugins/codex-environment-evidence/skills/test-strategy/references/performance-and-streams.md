# Performance and streaming updates

Read for an authorized performance comparison, polling/notification/streaming change, burst regression or sustained-resource check. Select the cases needed to resolve the actual risk. Reuse the application's existing test/diagnostic entry points and isolated fixtures.

## Resolve the measured system

Record the baseline and candidate source/artifact hashes, runtime, served revision, fixture/workload, cache state, observation interval and enabled features. Include relevant dirty inputs in source identity. Verify that the running process loaded the candidate before attributing a result to it.

Separate source notifications and collection, persistence/projection, transport and presentation. SSE delivers server-to-client events; source collection still follows its own implementation. A keepalive comment, reconnect timer or diagnostic sample has a different purpose from collecting source data. Trace which operation each wakeup actually starts.

| Layer | Useful measurements and invariants |
|---|---|
| Source and collection | Notifications, checks, collections, bytes parsed, backlog progress and final source watermark |
| Persistence and projection | Connections/transactions, queries, bytes written, unchanged-input skips, failed-save retry and complete history |
| Transport | Active connections, payload bytes, received/completed events, duplicates, reconnects and queued/coalesced/dropped work |
| Presentation | Applied revisions, renders, frame/action latency, visible record identity and hidden-tab recovery |
| Resources | Attributed process CPU time, elapsed time, I/O, RSS/heap, owned DOM/listeners/tasks and diagnostic file size |

Coalesce replaceable complete-state snapshots only when the final state and required freshness survive. Ordered deltas, audit records and commands need their declared sequencing/replay semantics. Bound pending work for slow clients and hidden pages; verify recovery and owned connection cleanup. Check the negotiated HTTP version and connection behavior when multiple tabs matter.

## Choose a comparable experiment

- Separate first collection/startup from warm incremental work. Compare idle with idle and the same active or burst workload with itself, using paired baseline/candidate blocks and alternating or randomized order when practical.
- Verify equal inputs, accepted operations and final watermarks. Report totals and per-operation cost together: a more responsive collector may perform more rounds. Include failures, timeouts and backfill drain time.
- Select relevant cases: unchanged sources, steady changes, bursts, slow/disconnected clients, hide/show, restart and Debug off/on. Keep source generation, instrumentation and unrelated services attributable; record interference that remains.
- Capture CPU time and elapsed time separately. Label counter units/resolution; a zero observed increment is bounded by that resolution. Record process I/O reads/writes/other separately. Windows `IO_COUNTERS` describes process/job accounting; physical storage claims require separate storage evidence with cache conditions.
- Define duration and stopping conditions from the risk and available resources. Keep small repeated runs descriptive; use the available evidence-review workflow for sampling/uncertainty interpretation when needed. Measure the same workload's accepted result before claiming improvement.

## Sustained diagnostics

Make ongoing diagnostics opt-in within the authorized duration, data and storage scope. Prefer numeric counters and opaque version identifiers, with bounded in-memory tails, file rotation/retention and visible write failures. Exclude source contents, credentials and private request bodies. Check that diagnostic writes cannot feed the source watcher or create new collection loops.

Compare matched post-warmup checkpoints across update/open/close cycles: heap/RSS, owned nodes/listeners/controllers, pending callbacks, active streams and retained files. Inspect reference/trace evidence for an increasing retained baseline. Separate application retention from debugger event history, caches and instrumentation overhead. Preserve cleanup failures and close only owned resources.

## Primary sources

Checked 2026-10-10. These provide API semantics and measurement methods; choose equivalent supported tools in the target environment.

- [MDN SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events): event format, keepalive, reconnect/close and HTTP connection limits
- [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame): repaint scheduling and background-tab suspension
- [Microsoft process times](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes) and [I/O counters](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters): process attribution and counter units
- [Google Benchmark](https://google.github.io/benchmark/user_guide.html): warmup, repetitions, interleaving and CPU/elapsed measurements
- [Chrome memory diagnostics](https://developer.chrome.com/docs/devtools/memory-problems): live heap, retained nodes and comparable collection checkpoints
