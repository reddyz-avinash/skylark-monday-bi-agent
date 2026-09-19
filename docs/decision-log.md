# Skylark Drones — Decision Log

## Assumptions

- Deals and Work Orders are separate Monday.com boards and Monday.com is the runtime system of record.
- The agent is read-only.
- Missing values are not treated as zero.
- Sector/status matching is normalized for case and spacing.
- Cross-board customer joins are not invented when no reliable mapping exists.
- Leadership updates mean a concise commercial + operational + billing snapshot with data-quality caveats.

## Trade-offs

**Deterministic analytics + optional LLM:** Python calculates business numbers so an LLM cannot invent totals. The optional LLM improves natural-language presentation.

**Monday API rather than Excel runtime reads:** The assignment explicitly requires dynamic Monday.com queries.

**React + FastAPI:** Lightweight, understandable, and suitable for the six-hour timeline.

## Data quality

The supplied datasets contain many incomplete fields. The agent therefore reports available populations and caveats rather than silently filling missing data.

## Leadership updates

The feature produces an executive summary covering open pipeline, work-order execution, billing/collection/receivables and important data-quality caveats.

## With more time

- richer schema-aware LLM tool calling
- source-record drill-down
- configurable fiscal-quarter logic
- authentication and role-based access
- automated tests with a sanitized Monday fixture
- richer visualizations
- a verified customer/deal mapping table for stronger cross-board joins
