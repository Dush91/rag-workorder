# End-to-end eval: `baseline`

16 cases x up to 3 reps = 47 graded runs; 8 failed attempts (not scored). App model `moonshotai/Kimi-K3.1-Pro`, judge `zai-org/GLM-5.3`.

| Metric | Mean | 95% CI | What it measures |
|---|---|---|---|
| Pass | 0.71 | ±0.20 | hard facts all correct AND every rubric criterion met |
| Hard facts | 0.98 | ±0.04 | priority, stop, parts, torque, open question, citations valid |
| Rubric | 0.85 | ±0.12 | share of case rubric criteria met (LLM judge) |
| Faithfulness | 0.99 | ±0.00 | work-order items supported by the chunks they cite |
| Evid. recall | 0.88 | ±0.09 | gold evidence chunks that reached the planner |
| Citations | 1.00 | ±0.00 | every cited ID was supplied and every item cites something |

**Consistency:** pass^3 = **0.53** (passes on all 3 runs), pass@3 = 0.80 (passes on at least one run).

**Cost (measured from `usage`):** app $0.138/run, judge $0.088/run, total $10.62 for this run. **Latency:** median 159s, max 308s per work order.

## Per case

| Case | Tag | Pass | Hard facts | Rubric | Faithful | Failing checks (any rep) |
|---|---|---|---|---|---|---|
| `c02_pre_bulletin_serial` | serial-dependency | 0.00 | 1.00 | 0.50 | 0.99 | rubric: "Requires chemical goggles and nitrile gloves, because P-102 …", rubric: "Requires lock-out/tag-out, valve isolation and a line-break …" |
| `c01_original` | serial-dependency | 0.00 | 1.00 | 0.20 | 0.99 | rubric: "Requires a lifting plan signed by the shift supervisor and c…", rubric: "Requires chemical goggles and nitrile gloves, because P-104 …", rubric: "Requires electrical isolation with lock-out/tag-out, mechani…", rubric: "Says the reliability engineer must be notified before restar…" |
| `c03_boundary_serial` | serial-dependency | 0.67 | 1.00 | 0.89 | 0.98 | rubric: "Requires chemical goggles and nitrile gloves, because P-105 …" |
| `c04_not_dosed` | site-rule-scope | 0.00 | 1.00 | 0.56 | 0.99 | rubric: "Requires a lifting plan and certified lifting equipment for …", rubric: "Requires lock-out/tag-out, valve isolation and a line-break …" |
| `c05_zone_c` | severity-threshold | 1.00 | 1.00 | 1.00 | 1.00 | — |
| `c06_exact_zone_boundary` | severity-threshold | 0.67 | 1.00 | 0.83 | 0.99 | rubric: "Handles the ambiguity conservatively: treats it as Zone D (s…" |
| `c07_alarm_temp_only` | severity-threshold | 0.67 | 0.67 | 0.89 | 1.00 | priority_ok, rubric: "Raises the work order as priority 1 within the shift, citing…" |
| `c08_above_trip` | severity-threshold | 1.00 | 1.00 | 1.00 | 1.00 | — |
| `c09_bearing_noise` | other-symptom | 1.00 | 1.00 | 1.00 | 0.98 | — |
| `c10_low_flow` | other-symptom | 1.00 | 1.00 | 1.00 | 1.00 | — |
| `c11_alignment_after_motor` | other-symptom | 1.00 | 1.00 | 1.00 | 0.98 | — |
| `c12_missing_serial` | robustness | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c14_conflicting_note` | robustness | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c13_unknown_equipment` | robustness | 1.00 | 1.00 | 1.00 | 1.00 | — |
| `c16_zone_d_not_dosed` | severity-threshold | 0.33 | 1.00 | 0.78 | 1.00 | rubric: "Classifies 8.3 mm/s as Zone D, stops the pump, and requires …" |
| `c15_dry_run_only` | other-symptom | 1.00 | 1.00 | 1.00 | 1.00 | — |

## Failed attempts

- `c03_boundary_serial` rep 0: grader_error (judge returned indices [0, 1] for 3 criteria)
- `c09_bearing_noise` rep 1: grader_error (judge returned indices [0] for 3 criteria)
- `c10_low_flow` rep 1: grader_error (judge returned 0 verdicts for 34 items)
- `c11_alignment_after_motor` rep 1: grader_error (judge returned indices [0] for 3 criteria)
- `c10_low_flow` rep 2: grader_error (judge returned 0 verdicts for 28 items)
- `c15_dry_run_only` rep 1: truncated (Response was cut off at max_tokens)
- `c15_dry_run_only` rep 2: truncated (Response was cut off at max_tokens)
- `c15_dry_run_only` rep 1: truncated (Response was cut off at max_tokens)
