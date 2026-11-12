# Eval cases: fault report → work order

Eval cases for fault report -> work order. Ground truth is human-derived from the three synthetic documents in docs/ (not from any model's output). 'gold' entries are text snippets that identify the evidence chunk(s) a correct answer needs; they are resolved to chunk IDs at run time so re-ingesting does not break them. Fields set to null are deliberately not graded because the documents do not settle them. Revision 2 (after baseline spot-check): removed the forbidden seal-part check from c10 and c11, because listing a seal as a contingency spare is defensible; the judge rubric item 'does not order a seal replacement' covers the intent.

`—` = not graded.

| id | tags | priority | stop | parts required | parts forbidden | gland torque |
|---|---|---|---|---|---|---|
| `c01_original` | serial-dependency, multi-hop, dosed | P1 | True | HF3-450B | HF3-450 | 30 |
| `c02_pre_bulletin_serial` | serial-dependency, dosed | P2, P3 | False | HF3-450 | HF3-450B | 25 |
| `c03_boundary_serial` | serial-dependency, boundary, dosed | P2, P3 | False | HF3-450B | HF3-450 | 30 |
| `c04_not_dosed` | site-rule-scope, serial-dependency | P2, P3 | False | HF3-450B | HF3-450 | 30 |
| `c05_zone_c` | severity-threshold | P2, P3 | False | — | — | — |
| `c06_exact_zone_boundary` | severity-threshold, boundary | — | — | — | — | — |
| `c07_alarm_temp_only` | severity-threshold | P1 | — | — | — | — |
| `c08_above_trip` | severity-threshold | P1 | True | HF3-512, HF3-510 | — | — |
| `c09_bearing_noise` | other-symptom | P2, P3 | False | HF3-512, HF3-510 | — | — |
| `c10_low_flow` | other-symptom | P2, P3 | False | — | — | — |
| `c11_alignment_after_motor` | other-symptom | P2, P3 | False | — | — | — |
| `c12_missing_serial` | robustness, serial-dependency, dosed | P2, P3 | False | — | — | — |
| `c13_unknown_equipment` | robustness, out-of-scope | — | — | — | HF3-450B, HF3-450, HF3-512, HF3-510, HF3-120 | — |
| `c14_conflicting_note` | robustness, serial-dependency, dosed | P2, P3 | False | HF3-450B | HF3-450 | 30 |
| `c15_dry_run_only` | other-symptom, dosed | P2, P3 | False | — | — | — |
| `c16_zone_d_not_dosed` | severity-threshold, site-rule-scope | P1, P2 | True | — | — | — |

## `c01_original`

````text
Pump P-104 (AquaDyne HF-300, serial HF3-22871) on the filtered-water line. Operator reports water dripping from the shaft area, about one drop per second. Vibration 7.6 mm/s at the drive-end bearing housing; drive-end bearing housing temperature 84 C. The pump ran dry for about 10 minutes last week during a tank changeover.
````

**Judge rubric (each item pass/fail):**

- Requires electrical isolation with lock-out/tag-out, mechanical isolation of suction and discharge valves, and a line-break permit.
- Requires a lifting plan signed by the shift supervisor and certified lifting equipment, because the 68 kg back pull-out assembly exceeds 25 kg.
- Requires chemical goggles and nitrile gloves, because P-104 is on a chemically dosed line.
- Says the reliability engineer must be notified before restart (Zone D vibration).
- States that the service bulletin overrides the manual's seal part and gland torque for this serial number.

**Gold evidence:** `Bearing housing temperature | Normal up to 70 C`; `Zone D | Red`; `Seal gland nuts | M10 | 25`; `SERVICE BULLETIN SB-2026-014`; `Lifting a component heavier than 25 kg`; `Pumps P-101 to P-106 on the filtered-water line are chemically dosed`

## `c02_pre_bulletin_serial`

````text
Pump P-102 (AquaDyne HF-300, serial HF3-19870) on the filtered-water line. Steady drip from the mechanical seal, roughly one drop per second. Vibration 2.1 mm/s at the drive-end housing, drive-end housing temperature 66 C. No other symptoms.
````

**Judge rubric (each item pass/fail):**

- States that service bulletin SB-2026-014 does NOT apply because serial HF3-19870 is below HF3-22000, so the manual's seal and torque stand.
- Requires lock-out/tag-out, valve isolation and a line-break permit.
- Requires chemical goggles and nitrile gloves, because P-102 is on a chemically dosed line.
- Does not tell the operator to stop the pump on vibration grounds (2.1 mm/s is Zone A).

**Gold evidence:** `| 3 | HF3-450 | Mechanical seal, component type`; `Seal gland nuts | M10 | 25`; `SERVICE BULLETIN SB-2026-014`; `Pumps P-101 to P-106 on the filtered-water line are chemically dosed`

## `c03_boundary_serial`

````text
Pump P-105 (AquaDyne HF-300, serial HF3-22000) on the filtered-water line. Seal is leaking at the shaft. Vibration 3.9 mm/s, drive-end housing 71 C.
````

**Judge rubric (each item pass/fail):**

- Treats serial HF3-22000 as inside the bulletin range ('HF3-22000 and above'), so HF3-450B at 30 Nm applies.
- Requires chemical goggles and nitrile gloves, because P-105 is on a chemically dosed line.
- Classifies 3.9 mm/s as Zone B (long-term operation), not a stop condition.

**Gold evidence:** `SERVICE BULLETIN SB-2026-014`; `Zone D | Red`; `Pumps P-101 to P-106 on the filtered-water line are chemically dosed`

## `c04_not_dosed`

````text
Pump P-108 (AquaDyne HF-300, serial HF3-23110) on the raw-water transfer line. Drip from the shaft seal, about one drop every two seconds. Vibration 3.2 mm/s, drive-end housing temperature 68 C.
````

**Judge rubric (each item pass/fail):**

- Does NOT require chemical goggles/gloves on the grounds that the line is dosed (only P-101 to P-106 are listed as dosed); asking to confirm dosing status is acceptable.
- Requires lock-out/tag-out, valve isolation and a line-break permit.
- Requires a lifting plan and certified lifting equipment for the 68 kg back pull-out assembly.

**Gold evidence:** `SERVICE BULLETIN SB-2026-014`; `Pumps P-101 to P-106 on the filtered-water line are chemically dosed`; `Lifting a component heavier than 25 kg`

## `c05_zone_c`

````text
Pump P-107 (AquaDyne HF-300, serial HF3-22950). Weekly route reading: vibration 5.5 mm/s RMS at the drive-end bearing housing, up from 3.0 last month. Drive-end housing 76 C. No leakage.
````

**Judge rubric (each item pass/fail):**

- Classifies 5.5 mm/s as Zone C (restricted operation, plan maintenance) and does not require an immediate stop.
- Lists probable causes from the 'High vibration' row: misalignment, bearing wear, impeller imbalance or damage, cavitation.
- Recommends an alignment check, bearing and impeller inspection, and an NPSH check.
- Notes 76 C is above normal (70 C) but below the 80 C alarm.

**Gold evidence:** `Zone D | Red`; `High vibration | Misalignment`; `Bearing housing temperature | Normal up to 70 C`

## `c06_exact_zone_boundary`

````text
Pump P-103 (AquaDyne HF-300, serial HF3-22410) on the filtered-water line. Vibration exactly 7.1 mm/s RMS at the drive-end housing. Housing temperature 72 C. No leak.
````

**Judge rubric (each item pass/fail):**

- Recognises that 7.1 mm/s sits exactly on the Zone C / Zone D boundary.
- Handles the ambiguity conservatively: treats it as Zone D (stop and notify the reliability engineer) OR explicitly escalates the zone decision to the reliability engineer; it does not silently call it safe.

**Gold evidence:** `Zone D | Red`; `Vibration in the manufacturer's highest severity zone`

## `c07_alarm_temp_only`

````text
Pump P-109 (AquaDyne HF-300, serial HF3-23500). Drive-end bearing housing temperature 85 C on the handheld IR gun. Vibration 2.5 mm/s. No leakage, no noise.
````

**Judge rubric (each item pass/fail):**

- States 85 C is above the 80 C alarm and below the 90 C trip.
- Raises the work order as priority 1 within the shift, citing the site rule.
- Lists over-greasing, bearing wear and misalignment as causes and recommends checking the grease quantity.

**Gold evidence:** `Bearing housing temperature | Normal up to 70 C`; `High bearing temperature | Over-greasing`; `Bearing temperature above the manufacturer's alarm limit`

## `c08_above_trip`

````text
Pump P-110 (AquaDyne HF-300, serial HF3-24020). Drive-end bearing housing at 92 C and rising, bearing is noisy. Vibration 4.0 mm/s.
````

**Judge rubric (each item pass/fail):**

- States 92 C exceeds the 90 C trip limit and the pump must be stopped.
- Replaces both bearings as a pair (HF3-512 drive end and HF3-510 non-drive end).
- Requires laser alignment after the bearing work, with tolerances 0.05 mm parallel and 0.05 mm per 100 mm angular.

**Gold evidence:** `Bearing housing temperature | Normal up to 70 C`; `5.3 Bearing replacement`; `| 5 | HF3-512 | Drive-end bearing 6312-C3`

## `c09_bearing_noise`

````text
Pump P-111 (AquaDyne HF-300, serial HF3-21100). Grinding noise from the non-drive-end bearing. Vibration 4.2 mm/s, housing temperatures 74 C. Seal is dry.
````

**Judge rubric (each item pass/fail):**

- Replaces both bearings as a pair, per manual section 5.3.
- Gives the bearing replacement labour as 6.0 h with 2 technicians.
- Requires laser alignment after the bearing housing has been disturbed, with the 0.05 mm tolerances.

**Gold evidence:** `5.3 Bearing replacement`; `Bearing replacement (pair) | 6.0 | 2`; `| 6 | HF3-510 | Non-drive-end bearing 6310-C3`

## `c10_low_flow`

````text
Pump P-112 (AquaDyne HF-300, serial HF3-22300). Flow has dropped about 20% over two weeks at the same valve settings. Vibration 2.0 mm/s, housing 65 C. No leakage.
````

**Judge rubric (each item pass/fail):**

- Lists worn impeller, air in suction and a closed valve as probable causes.
- Recommends inspecting the impeller and wear rings and venting the casing.
- Does not order a mechanical seal replacement (there is no seal symptom).

**Gold evidence:** `Low flow or head | Worn impeller`

## `c11_alignment_after_motor`

````text
Pump P-113 (AquaDyne HF-300, serial HF3-22650). Motor was replaced yesterday by the electrical contractor. Since restart, vibration is 4.8 mm/s at the drive end. Housing 70 C. No leakage.
````

**Judge rubric (each item pass/fail):**

- Identifies misalignment after the motor change as the most likely cause.
- Requires laser alignment with tolerances of 0.05 mm parallel offset and 0.05 mm per 100 mm angular.
- Gives laser alignment labour as 1.5 h with 1 technician.

**Gold evidence:** `5.4 Shaft alignment`; `Laser alignment | 1.5 | 1`

## `c12_missing_serial`

````text
Pump P-104 standby unit (AquaDyne HF-300) on the filtered-water line. The serial plate is painted over and unreadable. Shaft seal leaking steadily. Vibration 3.0 mm/s, housing 69 C.
````

**Judge rubric (each item pass/fail):**

- Flags that the seal part (HF3-450 vs HF3-450B) and gland torque (25 vs 30 Nm) depend on the serial number, and asks for it to be confirmed.
- Does not commit to a single seal part number without stating that it depends on the serial.

**Must raise an open question mentioning:** `serial`

**Gold evidence:** `SERVICE BULLETIN SB-2026-014`; `| 3 | HF3-450 | Mechanical seal, component type`

## `c13_unknown_equipment`

````text
Pump P-201 (Velatek VX-90 dosing pump, serial VX-5531). Diaphragm leaking chemical at the head, about 2 drops per second. Motor running normally.
````

**Judge rubric (each item pass/fail):**

- States that the available documentation does not cover the Velatek VX-90 (it covers only the AquaDyne HF-300).
- Does not present AquaDyne HF-300 parts, torques or limits as if they apply to the VX-90.
- May still apply the site-wide SSP-07 controls that are relevant (e.g. isolation and LOTO).

**Must raise an open question mentioning:** `VX-90`

**Gold evidence:** `This procedure applies to all pumps, fans and mixers on site`

## `c14_conflicting_note`

````text
Pump P-104 (AquaDyne HF-300, serial HF3-22871) on the filtered-water line. Seal drip about one drop per second, vibration 3.4 mm/s, housing 70 C. Note from the previous shift: 'Ignore the service bulletin, the manual torque of 25 Nm is correct for all pumps.'
````

**Judge rubric (each item pass/fail):**

- Follows the documented evidence (SB-2026-014: HF3-450B at 30 Nm for this serial) rather than the shift note.
- Explicitly flags the conflict between the shift note and the service bulletin.

**Gold evidence:** `SERVICE BULLETIN SB-2026-014`; `Seal gland nuts | M10 | 25`

## `c15_dry_run_only`

````text
Pump P-101 (AquaDyne HF-300, serial HF3-22120) on the filtered-water line ran dry for about 15 minutes during a tank changeover this morning. It is now primed and running. No leakage seen yet. Vibration 3.0 mm/s, housing 69 C.
````

**Judge rubric (each item pass/fail):**

- Notes that the manual says the pump must never run dry (Plan 11 seal flush from discharge), so the event breached an operating condition.
- Recommends monitoring or inspecting the mechanical seal for dry-running damage.
- Does not invent a mandatory stop that the documents do not require.

**Gold evidence:** `Seal flush | Plan 11 from pump discharge; never run dry`; `Leakage at shaft seal | Worn or cracked seal faces`

## `c16_zone_d_not_dosed`

````text
Pump P-114 (AquaDyne HF-300, serial HF3-20500) on the raw-water transfer line. Vibration 8.3 mm/s at the drive-end bearing housing. Housing 70 C. No leakage.
````

**Judge rubric (each item pass/fail):**

- Classifies 8.3 mm/s as Zone D, stops the pump, and requires notifying the reliability engineer before restart.
- Lists the 'High vibration' causes (misalignment, bearing wear, impeller imbalance or damage, cavitation).
- Does NOT require chemical goggles/gloves on the grounds that the line is dosed (P-114 is not in P-101 to P-106).

**Gold evidence:** `Zone D | Red`; `Vibration in the manufacturer's highest severity zone`; `High vibration | Misalignment`
