# End-to-end eval: `v1`

16 cases x up to 3 reps = 48 graded runs; 9 failed attempts (not scored). App model `moonshotai/Kimi-K3.1-Pro`, judge `zai-org/GLM-5.3`.

| Metric | Mean | 95% CI | What it measures |
|---|---|---|---|
| Pass | 0.92 | ±0.07 | hard facts all correct AND every rubric criterion met |
| Hard facts | 0.96 | ±0.06 | priority, stop, parts, torque, open question, citations valid |
| Rubric | 0.98 | ±0.03 | share of case rubric criteria met (LLM judge) |
| Faithfulness | 0.99 | ±0.00 | work-order items supported by the chunks they cite |
| Evid. recall | 0.97 | ±0.03 | gold evidence chunks that reached the planner |
| Citations | 0.98 | ±0.04 | every cited ID was supplied and every item cites something |

**Consistency:** pass^3 = **0.75** (passes on all 3 runs), pass@3 = 1.00 (passes on at least one run).

**Cost (measured from `usage`):** app $0.155/run, judge $0.102/run, total $12.34 for this run. **Latency:** median 152s, max 330s per work order.

## Per case

| Case | Tag | Pass | Hard facts | Rubric | Faithful | Failing checks (any rep) |
|---|---|---|---|---|---|---|
| `c01_original` | serial-dependency | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c02_pre_bulletin_serial` | serial-dependency | 1.00 | 1.00 | 1.00 | 0.96 | — |
| `c04_not_dosed` | site-rule-scope | 0.67 | 1.00 | 0.89 | 0.99 | rubric: "Requires a lifting plan and certified lifting equipment for …" |
| `c03_boundary_serial` | serial-dependency | 1.00 | 1.00 | 1.00 | 1.00 | — |
| `c05_zone_c` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c06_exact_zone_boundary` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c07_alarm_temp_only` | severity-threshold | 0.67 | 0.67 | 0.89 | 0.99 | priority_ok, rubric: "Raises the work order as priority 1 within the shift, citing…" |
| `c08_above_trip` | severity-threshold | 0.67 | 0.67 | 1.00 | 0.97 | citations_ok |
| `c10_low_flow` | other-symptom | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c09_bearing_noise` | other-symptom | 1.00 | 1.00 | 1.00 | 0.98 | — |
| `c12_missing_serial` | robustness | 0.67 | 1.00 | 0.83 | 1.00 | rubric: "Does not commit to a single seal part number without stating…" |
| `c11_alignment_after_motor` | other-symptom | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c13_unknown_equipment` | robustness | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c14_conflicting_note` | robustness | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c16_zone_d_not_dosed` | severity-threshold | 1.00 | 1.00 | 1.00 | 0.99 | — |
| `c15_dry_run_only` | other-symptom | 1.00 | 1.00 | 1.00 | 0.99 | — |

## Failed attempts

- `c02_pre_bulletin_serial` rep 0: truncated (Response was cut off at max_tokens)
- `c03_boundary_serial` rep 0: truncated (Response was cut off at max_tokens)
- `c01_original` rep 1: truncated (Response was cut off at max_tokens)
- `c10_low_flow` rep 2: truncated (Response was cut off at max_tokens)
- `c11_alignment_after_motor` rep 1: truncated (Response was cut off at max_tokens)
- `c11_alignment_after_motor` rep 0: truncated (Response was cut off at max_tokens)
- `c14_conflicting_note` rep 2: truncated (Response was cut off at max_tokens)
- `c12_missing_serial` rep 0: grader_error (Response was cut off at max_tokens)
- `c15_dry_run_only` rep 1: truncated (Response was cut off at max_tokens)
