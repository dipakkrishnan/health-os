# Timeline output format

```
## Coverage
<connections, last sync, datasets with errors, missing datasets relevant to the question>

## Timeline
### 2020
- 2020-03-10 — Kidney transplant status recorded (active, confirmed) [ci:4f2a91c07d3e]
### 2026
- 2026-07-01 — Creatinine 1.42 mg/dL (final) [ci:c906417c572e]
...

## Undated
- <items with unknown time; why they lack a date if evident>

## Interpretation (not in record)
- <optional; clearly derived observations, no uncited numerics>
```

Guidance:

- Group by year, then month/day as density warrants. The user's question decides
  which kinds and date ranges matter.
- For broad questions ("show me my history"), lead with a one-paragraph orientation:
  counts per kind, overall date span, connections covered — then the detail.
- Keep lines tight: date — display (status/summary) — citation. Use the `summary`
  field from the timeline command (lab value+unit, dosage text, assertion status).
- Omit empty sections except Coverage, which always appears.
