# Deliver a reproducible visual

## Data and relationships

Confirm field types, units, observation period, timezone, identifiers and join cardinality. Define filters, aggregation, denominators, duplicate handling, sorting and missing values. For large inputs, make sampling or aggregation explicit and retain enough lineage to reproduce the plotted values. Label illustrative or synthetic inputs at their use site.

For diagrams, identify each node and the meaning/direction of every edge from the relevant specification or implementation. Mark proposed relationships as proposed. Read the affected source revision when a changed interface or state invalidates an existing diagram.

## Build for the destination

Preserve the editable figure source, transformation and required rendering parameters at the project's existing artifact location. Use stable identifiers and relative references for portable sources. Select SVG/PDF for supported vector delivery, PNG for raster-compatible destinations, or interactive HTML/native artifacts for exploration according to the target surface. Choose font support and dimensions for the actual language and reading size.

Use color, labels, line style or symbols together so categories and states remain distinguishable. Keep captions, legends, units and filter state readable. Prefer a shared axis for directly compared panels. Place uncertainty and interpretation-changing conditions next to the affected result. Document prose explains the finding and links the source; the figure retains its own useful title/caption when shared separately.

## Verify and update

1. Reconcile source row counts, grouped totals, denominators and representative plotted points, including relevant missing, zero, duplicate and boundary cases
2. Check diagram edge direction, state transitions and owner boundaries against the source
3. Render/open the intended artifact and inspect labels, units, scales, clipping, overlap, legend mapping, font glyphs and target-size readability
4. Exercise applicable filters, empty states, reset, keyboard operation, tooltip/value access and export; verify that the displayed filter state matches the data
5. Read back the exported artifact and its link in the destination document, checking that the selected state and caption survived export

Apply the checks relevant to the chosen form and record actual outcomes. If the renderer is unavailable, retain the editable source and identify the exact pending render check. On a source revision or changed question, update the affected transformation/figure and repeat its checks. Keep previous accepted evidence associated with its original revision.
