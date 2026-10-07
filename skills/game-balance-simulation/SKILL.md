---
name: game-balance-simulation
description: Design, simulate, tune or review game economies, progression, resource loops and stochastic rewards using the actual game's rules. Use for balance and simulation questions across engines, including idle games, not ordinary UI or engine setup.
metadata:
  version: "0.4.13"
  author: "gaze9999"
  repository: "https://github.com/gaze9999/codex-toolkit"
---

# Game Balance Simulation

Begin with the requested player experience and the actual rules, core implementation, save format and numeric representation. Identify which milestones, choices or failure modes the task should evaluate, and keep proposed changes separate from adopted game rules.

## Establish a faithful experiment

- Prefer a headless harness calling the same economy and state-transition functions as the shipped game. Export traces for external analysis instead of silently maintaining a second economy in another language. Where a surrogate is necessary, compare representative traces and boundary cases against the core before relying on its results.
- Fix the source revision or dirty-state hash, configuration, initial state, strategy, time units, RNG implementation, seeds and observation horizon. Inject clock/RNG where supported, retain generated random inputs or action traces when a seed alone cannot replay the run.
- State a measurable hypothesis and baseline before tuning. Start with a representative loop; keep the simulator independent of rendering, real account activity and monetization transactions.
- Use available local calculation, spreadsheet, plotting, symbolic or notebook capabilities by need. Verify spreadsheet recalculation and cached values before treating formulas as results. Keep project libraries in the game's approved dependency environment and preserve existing locks; resolve setup through a maintained catalog when available.

## Choose checks that distinguish real failures

- Progression: measure time to meaningful decisions and milestones under applicable active and return schedules. Record stalled runs and content that is never chosen, as well as throughput, affordability, marginal net-income payback and reset timing. Do not impose a universal target duration or force every option to have equal efficiency.
- Strategies: compare simple, deliberately different purchase/reset policies over matched scenarios. Inspect domination, bottlenecks and degenerate loops, then validate a candidate on separate seeds, horizons and relevant initial states. An optimizer's chosen objective does not establish enjoyable play or a globally optimal policy.
- Random rewards: report sample count, seed set, reached fraction, median and supported tail estimates. Keep unreached milestones as censored outcomes at the stated horizon; do not remove them or report a finite population percentile when too few runs reached it. Include uncertainty and the effect of pity, guarantees or correlated draws when applicable.
- Time settlement: test caps, depletion, queues, completions, unlocks and simultaneous events using the game's specified ordering. Compare long catch-up with segmented advancement where the algorithm promises equivalence and use its defined tolerance. Keep event-indexed random inputs consistent for this comparison; identical seeds alone need not make differently segmented calls equivalent.
- Numerical rules: inspect units, rounding, discounts, bulk-buy definitions, zero/near-one growth factors, overflow, precision and serialization of large values. Preserve the game's exact or approximate representation, avoid converting huge values through a narrower float just to chart them.
- Stateful properties: generate valid action sequences around purchase, wait, reset, save and restore. Check resource bounds as defined by the game, atomic transactions, conservation where intended, bulk purchase semantics and save round trips. Explicit debt mechanics, rounding or reset exceptions belong in the property definition.

## Make failures and comparisons reproducible

Use the project's test framework and property-based tooling when it improves boundary or sequence coverage. Save shrunk counterexamples as readable regression cases alongside tool/runtime versions. Preserve each framework's actual replay information, such as seed/path/action history or saved examples, rather than assuming a fixed seed is sufficient across versions.

For tuning, distinguish an exploratory sweep from an accepted change. Vary a small justified parameter set, respect constraints, and retain baseline and candidate outputs with one comparable metric definition. Stochastic optimization needs an evaluation budget and a separate validation set; changes in sampled runs are not evidence of a parameter improvement.

Report the hypothesis, rules and source used, strategies, horizon, sample/replay details, distributions, counterexamples, accepted changes and unresolved checks. Add a small plot or table when it exposes a choice or bottleneck. Separate rule correctness, simulated pacing and actual player feedback, then propose the next small playtest needed to assess the experience.
