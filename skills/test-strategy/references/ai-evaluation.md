# AI and stochastic workflow evaluation

Read for changed prompts/models, retrieval, tools, agent state or generated media. Establish the actual model/provider/checkpoint, SDK, parameters, hardware, workflow and allowed data/cost before testing. No reference authorizes paid calls, dataset transfer or downloading models.

## Separate evidence layers

- Deterministic checks: request/schema validation, permissions, tool arguments, error handling, retry/cancellation, budgets, state ownership and output parsing. Mock provider fixtures prove only these boundaries.
- Retrieval: use authorized labeled questions and relevant evidence to measure appropriate recall/ranking plus source freshness and access filtering. Retrieved evidence quality is distinct from answer correctness.
- Model/agent behavior: evaluate representative tasks against task-specific rubric and independent expected evidence, including abstention, unsupported claims, invalid tools, prompt injection and multi-step recovery. Agent tool execution and resulting state need direct verification.
- Operations: measure end-to-end latency/cost, provider failure and retry rate, fallback behavior and actual workload. Include failed attempts, not only accepted outputs.

Keep a versioned development set and held-out acceptance set; do not tune on the latter. Label provenance and authorize all samples, prompts, rubric and derived summaries. Stratify relevant languages, task difficulty and risks; preserve rare mandatory cases rather than letting an overall average hide them. Compare baseline/candidate on the same suitable cases with independent runs and paired analysis when justified. Record nondeterminism, model version and sample counts; temperature zero or a supplied seed is not a universal determinism guarantee.

Calibrate automatic graders against human-reviewed examples, inspect disagreements and document grader/prompt version. Prefer deterministic checks where a rule decides the result. A model judge's probability, Jev ranking or rubric score is not a measured probability of system correctness. Use Jev only for approved finite semantic comparisons that can change the next action; retain unknown outcomes and Main acceptance.

For generated audio/images/video, separately check file/container validity, duration/dimensions/rate, invalid/clipped/nonfinite samples and prompt-specific output criteria. Use authorized perceptual assessment or domain metrics appropriate to the actual task, with human review where necessary; transport success and an attractive sample do not prove fidelity or quality. Distinguish backend/device support, VRAM pressure/OOM, warmup, checkpoint/license and export compatibility. Do not publish sample media, training data or model weights without their actual redistribution rights.

At release, retain reproducible prompt/workflow/checkpoint configuration, regression cases, thresholds, safety/data boundaries, monitoring and recovery/rollback criteria appropriate to the application. Online evaluation and deployment remain separately authorized. Use an available ai-application-engineering Skill for implementation and provider-specific boundaries rather than reproducing its architecture here.

Sources: [OpenAI evaluation practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices), [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework). Consult the actual provider/model documentation for operational capabilities; do not transfer one provider's guarantees to another.
