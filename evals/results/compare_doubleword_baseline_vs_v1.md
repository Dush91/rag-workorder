# `baseline` vs `v1` (paired over 16 cases)

| Metric | baseline | v1 | Δ | 95% CI of Δ |
|---|---|---|---|---|
| Pass | 0.71 | 0.92 | +0.21 | ±0.21 |
| Hard facts | 0.98 | 0.96 | -0.02 | ±0.04 |
| Rubric | 0.85 | 0.98 | +0.12 | ±0.12 |
| Faithfulness | 0.99 | 0.99 | -0.00 | ±0.01 |
| Evid. recall | 0.88 | 0.97 | +0.09 | ±0.08 |
| Citations | 1.00 | 0.98 | -0.02 | ±0.04 |

`baseline` pass^3 = **0.53** (over the 15 cases with all 3 reps in both variants)

`v1` pass^3 = **0.73** (over the 15 cases with all 3 reps in both variants)

| Case | baseline pass | v1 pass |
|---|---|---|
| `c01_original` | 0.00 | 1.00 ⬆ |
| `c02_pre_bulletin_serial` | 0.00 | 1.00 ⬆ |
| `c03_boundary_serial` | 0.67 | 1.00 ⬆ |
| `c04_not_dosed` | 0.00 | 0.67 ⬆ |
| `c05_zone_c` | 1.00 | 1.00 |
| `c06_exact_zone_boundary` | 0.67 | 1.00 ⬆ |
| `c07_alarm_temp_only` | 0.67 | 0.67 |
| `c08_above_trip` | 1.00 | 0.67 ⬇ |
| `c09_bearing_noise` | 1.00 | 1.00 |
| `c10_low_flow` | 1.00 | 1.00 |
| `c11_alignment_after_motor` | 1.00 | 1.00 |
| `c12_missing_serial` | 1.00 | 0.67 ⬇ |
| `c13_unknown_equipment` | 1.00 | 1.00 |
| `c14_conflicting_note` | 1.00 | 1.00 |
| `c15_dry_run_only` | 1.00 | 1.00 |
| `c16_zone_d_not_dosed` | 0.33 | 1.00 ⬆ |
