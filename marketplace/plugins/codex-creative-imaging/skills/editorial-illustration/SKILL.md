---
name: editorial-illustration
description: Generate editorial illustrations from user-provided images using optional adjustments and the bundled editorial-illustration base prompt.
metadata:
  short-description: Direct editorial-illustration generation from images and optional adjustments
  version: "0.4.12"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Editorial Illustration

This is an image-generation pipeline. When requirements are sufficient, generate the image directly; do not make the final prompt, assembly steps, or analysis the primary output.

## Input and handling

- A usable `SOURCE_IMAGE` must be accessible in the current task as an attachment, authorized workspace file, or supported tool reference. If it is missing or inaccessible, ask only for the image or a usable reference.
- The user may specify composition, subject, whitespace, scene, color, mood, texture, typography, or style adjustments in natural language. Do not infer omitted adjustments.
- Resolve [Base Prompt](references/base-prompt.md) relative to this Skill for generation. It supplies default art direction, explicit user choices override visual defaults including composition, aspect ratio and output grouping.

## Default visual direction

- The source image supplies visual evidence for the subject, pose, objects, relationships, mood, and color.
- Produce one complete illustration for each source image. Do not create collages, split screens, or before-and-after comparisons.
- Do not directly show or blend in the original photograph.
- For multiple images, create a composite only when the user explicitly requests one; otherwise apply the Base Prompt and relevant adjustments independently.

When a usable image and executable request are present, use the available image-generation capability and deliver the result directly. Provide a prompt-only deliverable when the user requests one; otherwise report an unavailable compatible generation capability as the execution boundary.
