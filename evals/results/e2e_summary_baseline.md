# End-to-end eval: `baseline`

16 cases x up to 3 reps = 48 graded runs; 0 failed attempts (not scored). App model `claude-opus-5-5`, judge `claude-sonnet-5-5`.

| Metric | Mean | 95% CI | What it measures |
|---|---|---|---|
| Pass | 0.79 | ±0.14 | hard facts all correct AND every rubric criterion met |
| Hard facts | 0.96 | ±0.08 | priority, stop, parts, torque, open question, citations valid |
| Rubric | 0.90 | ±0.08 | share of case rubric criteria met (LLM judge) |
| Faithfulness | 0.92 | ±0.02 | work-order items supported by the chunks they cite |
| Evid. recall | 0.92 | ±0.06 | gold evidence chunks that reached the planner |
| Citations | 1.00 | ±0.00 | every cited ID was supplied and every item cites something |

**Consistency:** pass^3 = **0.62** (passes on all 3 runs), pass@3 = 1.00 (passes on at least one run).

**Cost (measured from `usage`):** app $0.114/run, judge $0.070/run, total $8.81 for this run. **Latency:** median 60s, max 107s per work order.

## Per case

| Case | Tag | Pass | Hard facts | Rubric | Faithful | Failing checks (any rep) |
|---|---|---|---|---|---|---|
| `c01_original` | serial-dependency | 0.33 | 1.00 | 0.47 | 0.93 | rubric: "Requires a lifting plan signed by the shift supervisor and c…", rubric: "Requires chemical goggles and nitrile gloves, because P-104 …", rubric: "Requires electrical isolation with lock-out/tag-out, mechani…", rubric: "Says the reliability engineer must be notified before restar…" |
| `c02_pre_bulletin_serial` | serial-dependency | 0.33 | 1.00 | 0.67 | 0.86 | rubric: "Requires chemical goggles and nitrile gloves, because P-102 …", rubric: "Requires lock-out/tag-out, valve isolation and a line-break …" |
| `c03_boundary_serial` | serial-dependency | 0.33 | 1.00 | 0.78 | 0.93 | rubric: "Requires chemical goggles and nitrile gloves, because P-105 …" |
| `c04_not_dosed` | site-rule-scope | 0.67 | 1.00 | 0.78 | 0.91 | rubric: "Requires a lifting plan and certified lifting equipment for …", rubric: "Requires lock-out/tag-out, valve isolation and a line-break …" |
| `c05_zone_c` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.95 | — |
| `c06_exact_zone_boundary` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.94 | — |
| `c07_alarm_temp_only` | severity-threshold | 0.33 | 0.33 | 0.78 | 0.95 | priority_ok, rubric: "Raises the work order as priority 1 within the shift, citing…" |
| `c08_above_trip` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.95 | — |
| `c09_bearing_noise` | other-symptom | 1.00 | 1.00 | 1.00 | 0.90 | — |
| `c10_low_flow` | other-symptom | 1.00 | 1.00 | 1.00 | 0.92 | — |
| `c11_alignment_after_motor` | other-symptom | 1.00 | 1.00 | 1.00 | 0.83 | — |
| `c12_missing_serial` | robustness | 1.00 | 1.00 | 1.00 | 0.93 | — |
| `c13_unknown_equipment` | robustness | 1.00 | 1.00 | 1.00 | 0.98 | — |
| `c14_conflicting_note` | robustness | 1.00 | 1.00 | 1.00 | 0.94 | — |
| `c15_dry_run_only` | other-symptom | 1.00 | 1.00 | 1.00 | 0.91 | — |
| `c16_zone_d_not_dosed` | severity-threshold | 0.67 | 1.00 | 0.89 | 0.92 | rubric: "Classifies 8.3 mm/s as Zone D, stops the pump, and requires …" |
