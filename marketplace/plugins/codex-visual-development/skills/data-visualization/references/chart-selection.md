# Select by the reader's question

| Question | Useful form | Decision-changing check |
|---|---|---|
| Compare categories or rank values | Bar or dot plot | Stable units/order; bars start at zero; highlight meaningful comparisons |
| Track time | Line or step chart | Ordered timestamps, timezone and gaps; step form for discrete state changes |
| Inspect distribution/outliers | Histogram, box plot or empirical cumulative curve | Bin/quantile definitions, sample count, tails and missing observations |
| Explore relationships | Scatter plot; bubble size for a justified third measure | Overplotting, scale and confounders; size maps to area; association described separately from causation |
| Compare parts of a whole | Stacked bar; 100% stacked bar for proportions; pie for a few distinct parts | Common denominator, complete categories, rounding and totals |
| Compare a matrix or repeated groups | Heatmap or small multiples | Shared scale and ordering; separate missing cells; diverging midpoint has a defined meaning |
| Show hierarchy | Tree; treemap for hierarchical magnitude | Parent identity, depth and totals; use a table/tree when exact lookup matters |
| Explain process and responsibility | Flowchart or swimlane | Decision branches, loops, owner boundaries and failure/recovery paths |
| Explain calls and state | Sequence or state diagram | Call direction, asynchronous completion, transitions, guards and state owner |
| Explain system/data relationships | Architecture, dependency graph or ER diagram | Edge meaning, producer/consumer, cardinality and cycles grounded in evidence |
| Show schedule and dependencies | Gantt chart | Timezone, dates, dependency meaning and actual vs planned status |
| Explain quantities moving between stages | Sankey diagram | Compatible units and balanced inflow/outflow, explicitly identified loss or gain |
| Explain geographic variation | Map when location is part of the question | Geographic identifiers, missing regions, rates vs totals and appropriate normalization |
| Retrieve exact values | Table with useful ordering | Units, precision, aligned columns and searchable text |

Choose the smallest set of complementary views that resolves the question. Dense categories may need filtering, grouping or small multiples. Preserve excluded categories and aggregation rules in the source/caption. A logarithmic scale needs positive-domain handling and an explicit label. Show uncertainty when the source provides it, with the interval definition.

## Interaction and output

Use interaction for questions that change by category, time range or scenario. Show active filters, units and a reset path; provide keyboard-accessible controls and text/table access to meaningful values. Static documents receive a legible snapshot of the selected state with those filters recorded. Technical diagrams use labeled edges and direction; numerical charts use data-aware plotting so labels and geometry share the same source.

## Representative routing cases

| Request | Expected choice and evidence |
|---|---|
| Compare monthly totals with one missing month | Time series with a visible gap, defined month/timezone and source totals |
| Compare category shares before and after a change | Paired 100% stacked bars with denominators and consistent categories |
| Explain a frontend request cancelled by navigation | Sequence/state diagram covering cancellation and ownership |
| Inspect latency tails | Distribution view with units, sample count and percentile definition |
| Explore a forecast under selectable assumptions | Interactive scenarios with assumptions, source data and a static export of the selected state |
| Look up exact prices from a small list | Table |
| State one confirmed count | Sentence |

These cases support source review of routing choices. Exercise the actual renderer and data transformations for a delivered visual.
