---
name: comfyui-workflow
description: Build, modify, diagnose, or document local Stable Diffusion and ComfyUI workflows with reproducible graph, model, custom-node, and hardware settings. Do not use for ordinary image generation that does not require workflow engineering.
metadata:
  version: "0.4.12"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# ComfyUI Workflow

Work from the actual workflow graph and local runtime. Preserve reproducibility and compatibility instead of guessing popular checkpoints, nodes, or settings.

## Inspect before changing

- Resolve the ComfyUI revision or release, Python and accelerator stack, installed custom-node versions, model files or identifiers, available VRAM/RAM, and workflow JSON or image metadata.
- Identify checkpoint, VAE, CLIP/text encoders, LoRA or other adapters, ControlNet/IP-Adapter models, sampler, scheduler, steps, CFG, seed, dimensions, batch settings, and output nodes that affect the result.
- Confirm whether the graph is text-to-image, image-to-image, inpainting, upscaling, animation, or another pipeline. Do not assume compatible nodes or tensor shapes across workflows.
- Distinguish editable UI workflow JSON (`nodes`/`links`) from the executable API prompt graph (`class_type`/`inputs`). Use the installed runtime's export or supported conversion and node definitions; do not submit one format where the other is expected.
- Treat checkpoint names and local paths as environment facts. Do not invent downloads, filenames, hashes, node inputs, or version compatibility.

## Modify safely

- Make the smallest connected graph change that satisfies the request. Preserve unrelated node IDs, links, groups, labels, bypass states, widgets, output paths, and embedded metadata.
- Keep model family, latent format, VAE, resolution constraints, conditioning shape, and custom-node API compatible across each link.
- Balance dimensions, batch size, precision, attention/offload options, and high-resolution stages against measured hardware limits. Prefer a smaller deterministic test before expensive output.
- Record or preserve seed and all generation parameters when reproducibility matters. If a node is inherently nondeterministic, say so.
- Do not install custom nodes, download weights, alter drivers, or execute untrusted workflow code without explicit authorization. Note license and redistribution constraints when packaging workflows or model references.

## Diagnose by stage

- Graph load failure: check JSON shape, missing node types, renamed inputs, custom-node versions, and model paths.
- Execution failure: locate the first failing node and inspect type/shape/device/dtype assumptions, memory pressure, and upstream values.
- Output mismatch: compare model and adapter compatibility, prompt conditioning, seed, sampler/scheduler, denoise, resolution, preprocessing, and post-processing independently.
- Performance or out-of-memory issues: measure the failing stage and peak memory before changing precision, tiling, offload, batch, or resolution.

## Verify and deliver

- Describe the requested outcome, confirmed facts, decisions, actual checks and concrete unresolved items. Support comparisons with evidence and applicable conditions, and retain limitations that affect correctness, safety, compatibility, requirements or execution.
- Validate that the workflow loads without missing nodes or broken links, then run the smallest representative execution permitted by the task. For queued execution, track the returned job identifier through completion/error and verify output artifacts; queue acceptance alone is not execution success.
- For visual-quality work, compare outputs using the same seed and controlled parameter differences. A successfully parsed graph does not prove visual quality.
- Return the updated workflow or precise node changes plus the ComfyUI/custom-node/model assumptions, actual checks, output location, and unverified hardware or quality boundaries.
