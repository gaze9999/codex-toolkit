# Statistical interpretation of test evidence

Read for repeated browser automation, load/stress/soak evidence, resource cleanup or performance comparisons affected by concurrent activity. Review supplied evidence and recommend only the checks that close a concrete gap. This reference does not authorize execution, telemetry installation, process termination or shared environment changes.

## Identify the estimand and evidence unit

Separate requirement/branch coverage, sampled failure rate, throughput/latency and retained resources. There is no single system-wide correctness percentage derived from passing tests, coverage, CPU use or an LLM score. Record the tested source/artifact, oracle, input distribution, seed, runtime/browser/device, workload, warmup, run boundaries, sample unit and acceptance condition. Keep blocked/unrun cases outside a pass numerator, but visible as acceptance gaps.

A browser test using mocks proves only that exercised mock/isolated flow; role visibility does not prove server authorization, persistence or API success. Review existing results against governing rules, not implementation-derived expected values alone. Distinguish cases, combinations, requests, independent runs and retries. A first-attempt failure remains a failure even if a retry passes.

## Functional coverage and sampled failures

- Build a decision table from the actual requirements and valid constraints. For high-risk combinations such as role, stage, action, record type and required fields, retain explicit expected outcomes and negative cases. Pairwise or higher-strength covering arrays help select interaction cases; they are not proof of complete coverage or a probability of correctness. Preserve required higher-order combinations and exclude impossible inputs.
- For generated/stateful tests, use justified properties and invariants: no lost or duplicated IDs, aggregate totals reconcile with source rows, reopening preserves authorized saved values, stale callbacks cannot overwrite a new state, cleanup restores owned-resource bounds. Replay seed and operation sequence. A transformation should preserve an outcome only when the specification defines that relationship; use boundary and error cases with an independent oracle.
- A curated deterministic suite reports observed passes and covered rules. Do not apply a binomial interval to different hand-picked cases and call it production reliability. Statistical rate inference needs a defined sampled workload, sufficiently independent trials and an adequate oracle. Correlated requests from one session or run are not independent repetitions; analyze at the independent session/run level or use a justified clustered method.
- For representative independent Bernoulli trials, report failures `k/n`, population/workload, confidence level and interval method. A Wilson two-sided interval is useful near 0 or 1, unlike the naive symmetric normal interval. For `n>0` and `0<=k<=n`, let `p=k/n`, `d=1+z*z/n`, `c=(p+z*z/(2*n))/d`, `h=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/d`; bounds are `c-h, c+h`. For two-sided 95%, `z` is approximately 1.96. Small samples or few failures may need exact binomial bounds.
- With zero failures, the exact one-sided upper bound is `1-alpha**(1/n)`, not zero. At 95% confidence, 100 independent trials give about 2.95%, 300 about 0.994%; `3/n` is an approximation. A target upper rate `q` requires `n >= ceil(log(alpha)/log(1-q))` zero-failure trials under those assumptions. These are sampling bounds for that workload, not guarantees or prescribed test counts. Set precision/threshold before sampling; arbitrary repeated peeking or stopping after a pass invalidates ordinary fixed-sample claims.

## Performance under concurrent activity

Record wall time separately from attributable process/thread CPU time, heap/RSS, long tasks, frame delays, throughput and timeouts, using available supported observations. A browser page timestamp or host-wide CPU reading is not process attribution. Shared browser processes, workers and rendering costs may not be separable; mark missing attribution. Keep failures/timeouts in the workload report, not only successful-request latency.

Prefer comparable paired blocks: same device/runtime, data, font size, rendering state and load stratum, with baseline/candidate order randomized or counterbalanced within each block. Warmup policy and cold-start measurements are separate. Record concurrent-load state and time; compare idle with idle and loaded with loaded. Independent batches capture drift better than many tightly correlated iterations. Report median and spread, with p95/p99 only when sample size and tail evidence support them, plus the quantile convention. Keep outliers or explain a predeclared measurement-invalid exclusion; never remove slow runs merely to show an improvement.

When enough independent blocks exist, report paired effects and a justified confidence interval; resample complete paired blocks rather than individual correlated events if using a bootstrap. Statistical detectability and a practically meaningful change are separate. Predeclare primary metrics and material effect thresholds; exploratory comparisons across many font sizes, datasets or metrics need explicit multiplicity handling before confirmatory significance claims. Too few blocks or no comparable baseline means observed timings and uncertainty, not an improvement claim. Do not force a universal repetition count or p-value threshold.

CPU utilization and memory use cannot subtract scheduler waits, contention, GC, GPU, thermal throttling, clock changes or I/O effects to reveal unloaded latency. A regression with measured covariates is only a conditional estimate: it needs repeated observations, load overlap, a suitable model and validation, and must not extrapolate to an unobserved idle state or imply causality. Without those data, recommend a bounded separate idle measurement when authorized; do not interrupt another owner's work.

For arrival-driven API load, inspect open versus closed workload semantics and offered/completed/dropped rates. Waiting for each slow operation before issuing the next can hide load-induced latency (coordinated omission). Keep sequential browser interaction realistic; do not replace a human-flow test with arrival-rate traffic merely for statistics. Stress performance beyond intended load is different from an SLO at intended load.

## Resource and UI stability

Compare post-cleanup heap/RSS and owned DOM/listener/controller/task counts at equivalent checkpoints across independent update/open/close cycles after warmup. A rising slope is a retention signal needing source/trace evidence; RSS growth alone does not prove a leak because caches, allocators and GC differ. Stable count alone does not prove absence of leaks.

Keep exact visual/state assertions independent of timing: card bounds before/during/after refresh, font-size overflow, tooltip ownership, retained chart nodes, canceled callbacks and loading/empty/error transitions. Synthetic UI checks do not establish physical-device or production-volume performance. Report source, oracle, workload and concurrency conditions, actual counts/results, inference assumptions, uncertainty and the smallest remaining acceptance check. Example numbers above are illustrative, not evidence from any project.

## Primary sources

Checked 2026-10-07. These are method references, not required dependencies or a mandate to install the named tools.

- [NIST proportion intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm): Wilson and exact binomial methods
- [NIST randomized blocks](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm): control nuisance factors and randomize remaining variation
- [NIST combinatorial testing](https://csrc.nist.gov/projects/automated-combinatorial-testing-for-software): interaction coverage methods
- [Google Benchmark guide](https://google.github.io/benchmark/user_guide.html): warmup, CPU/real time, repetitions, random interleaving and variance
- [Grafana k6 workload models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/): arrival-driven versus completion-driven load and coordinated omission

- [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html): paired resampling and interval limitations; choose the actual independent unit rather than treating repeated correlated events as separate samples
