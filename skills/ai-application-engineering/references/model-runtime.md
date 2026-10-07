# Model runtime and local inference

Use this reference for local models, serving runtimes, model selection, or hardware-sensitive inference.

- Resolve the exact model revision, license, runtime, accelerator, driver/toolkit, RAM/VRAM, precision, quantization, context length, batch/concurrency, and deployment target.
- Verify that the runtime supports the requested architecture, quantization, structured output, tool format, multimodal inputs, and streaming behavior.
- Size memory from actual runtime evidence when available. Leave headroom for framework overhead, KV cache, other processes, and peak workload; do not infer support from model size alone.
- Compare quality, latency, throughput, memory, and total task cost using the real workload. A shorter benchmark or lower price does not prove better end-to-end results.
- Preserve reproducibility by recording model revision, runtime version, relevant parameters, seed when supported, hardware, and evaluated dataset.
- Do not download weights, change drivers, install runtimes, or alter machine-wide configuration without explicit authorization.
