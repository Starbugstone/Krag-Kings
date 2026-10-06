# New human motion — integration audit

Source review only; no new clips are promoted and no engine was launched for this audit. The provisional Krag values supplied by root are Walk **1.000 s / 1.114 m/s**, Run **0.800 s / 3.003 m/s**, and Idle **6 s**. They remain review candidates. Nib must use its own retargeted stride measurements.

| Concern | Unity | Unreal |
| --- | --- | --- |
| Authored speeds | `BenchmarkBuild.CreateUnit` assigns `locomotion.Walk/Run.speedMetersPerSecond` to `DemoUnit.walkSpeed/runSpeed`. | `import_shared_assets.character/import_variant` assigns the same fields to `FKKCharacterVariant`. `AKKBenchmarkUnit::MoveTo/Tick` converts metres to centimetres. |
| Gait cadence | `DemoUnit.Update`: travelSpeed / nominal × actual clip length / `cycleSeconds`. | `FKKBenchmarkAnimProxy::PreUpdate`: velocity/nominal × actual clip length / `cycleSeconds`. |
| Idle/action duration | Direct imported clip length. Action/Face timers use `ActionDuration`. | Direct imported clip length. Action/Face timers use `GetPlayLength`. No fixed six-second limit needs changing. |
| Foot contact events | `DemoUnit.LateUpdate` crosses authored left/right normalized contacts. | `AKKBenchmarkUnit::UpdateFootContacts` crosses authored left/right normalized contacts. |
| Foot support phase | Already checks time since each authored contact against `stanceFraction`. | Previously hardcoded L0/R0.5 despite the event metadata. Prepared source now passes all four existing contact arrays into the animation graph and uses them for support phase. |
| Corrective deformation | `DemoDeformation.LateUpdate`, after body animation/terrain IK: bind-relative rotation magnitude or scale-aware local translation. | `FKKMorphCurveNode`, after the final local pose: same bind-relative rules, with ancestor/component scaling and cm→m conversion. Neither uses a fixed action phase or old clip duration. |

The new speeds/cycles require **manifest values**, not new hardcoded runtime speeds. The prepared Unreal importer now rejects missing/nonfinite/nonpositive cadence data and unsorted, duplicate or out-of-range contact phases instead of silently substituting the previous gait. Import reports will also include actual clip lengths and the consumed locomotion values. Existing defaults in asset constructors are fallback values; validated manifest fields replace them before runtime.

Existing short transition blends remain 0.12 s in Unity and 0.16 s for Unreal locomotion / 0.10 s for actions. Unreal's contact cooldown is 0.15 s per foot, so it does not cap the proposed 0.8–1 s per-foot cycles; very close multiple same-foot contact events would need review. Its contact-speed gate is 0.15 m/s, versus Unity's 0.05 m/s. These are effect filters, not the authored cycle clock. Unreal ramps foot IK over 0.06/0.08 normalized cycle spans; these track cycle duration rather than fixed seconds.

## Validation implications

- Body clips still need authored facial performance. Unity's import gate requires varying FaceRoot transform curves in every clip. Unreal similarly requires varying facial bones and a pelvis track for each body clip. A raw mocap-only replacement without the face layer should fail import.
- Unity Verify samples a complete actual Idle duration, each Melee/Shoot/Hit duration plus 0.2 s, the active FacePerformance interval, and the actual Walk/Run route. A six-second Idle therefore increases the variant verification time naturally. Its facial maxima are measured per action; the body-corrective maximum is aggregated across the three actions.
- Unreal's legacy smoke sequence checks movement/action/weapon events on fixed demonstration times. It does **not** provide the same complete per-action morph time series as Unity. The input state records applied body/facial maxima only at observed moments. Existing technical smoke success must not be presented as full revised-animation or deformation acceptance.
- Both runtimes move the actor separately. Retargeted body clips must remain in-place: remove linear horizontal root travel while retaining intentional local body sway and vertical weight transfer. Root confirmed this for the current candidate.
- Unity resets clip time when changing Walk/Run. Unreal's current standalone sequence player retains its accumulated time when its sequence pointer changes. This can change normalized phase when clips have different lengths, and contact crossing should be inspected during start/stop/gait switches with the revised clips. No speculative transition rewrite was included in this preparation.
- The 72-second showcase and 12-second performance workload are scenario schedules, not gait clocks. Different travel/clip durations can alter which pose is visible at a scheduled event. Recheck framing/event overlap when new assets are actually integrated.

Prepared changes are limited to metadata validation/reporting and metadata-driven Unreal foot support. Python syntax and pure metadata/phase checks pass; native compilation and actual contact/deformation review remain pending. No shared asset or current package was modified.
