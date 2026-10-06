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

Existing short transition blends remain 0.12 s in Unity and 0.16 s for Unreal idle/locomotion / 0.10 s for actions. Unreal still has one moving sequence player: the phase correction below does not add a separate Walk/Run pose crossfade. Its contact cooldown is 0.15 s per foot, so it does not cap the proposed 0.8–1 s per-foot cycles; very close multiple same-foot contact events would need review. Its contact-speed gate is 0.15 m/s, versus Unity's 0.05 m/s. These are effect filters, not the authored cycle clock. Unreal ramps foot IK over 0.06/0.08 normalized cycle spans; these track cycle duration rather than fixed seconds. The candidate authoring edge fades (Walk 0.055 / Run 0.04) are not yet shared runtime metadata and have not silently replaced these settings.

## Prepared gait-switch behavior

Both engines now prepare an active Walk↔Run switch using `wrap(oldNormalizedPhase - oldFirstLeftContact + newFirstLeftContact)`, then seek to that phase multiplied by the new clip's actual length. This preserves progress relative to the same foot's authored cycle origin, including differing clip lengths and contact offsets. It does not guarantee an identical pose or stance duration between different gaits. For the provisional left contacts Walk 0.01 / Run 0.58, Walk phase 0.10 maps to Run 0.67 rather than restarting at zero or retaining the wrong accumulated seconds. Returning to Walk maps back to 0.10.

Starting locomotion from idle still seeks to phase zero. The seek clears old terrain anchors and does not synthesize a footfall by crossing the intervening timeline. Unreal tags the evaluated phase with its gait and a seek serial so a pending new input command cannot compare old Run time against new Walk contact events before the animation graph updates. Unity suppresses the crossing check on the switch frame and retains its existing pose crossfade.

## Validation implications

- Body clips still need authored facial performance. Unity's import gate requires varying FaceRoot transform curves in every clip. Unreal similarly requires varying facial bones and a pelvis track for each body clip. A raw mocap-only replacement without the face layer should fail import.
- Unity Verify samples a complete actual Idle duration, each Melee/Shoot/Hit duration plus 0.2 s, the active FacePerformance interval, and the actual Walk/Run route. A six-second Idle therefore increases the variant verification time naturally. Its facial maxima are measured per action; the body-corrective maximum is aggregated across the three actions.
- Unreal's legacy smoke sequence checks movement/action/weapon events on fixed demonstration times. It does **not** provide the same complete per-action morph time series as Unity. The input state records applied body/facial maxima only at observed moments. Existing technical smoke success must not be presented as full revised-animation or deformation acceptance.
- Both runtimes move the actor separately. Retargeted body clips must remain in-place: remove linear horizontal root travel while retaining intentional local body sway and vertical weight transfer. Root confirmed this for the current candidate.
- The current packaged engines still use the prior gait-switch behavior. The prepared source change above needs actual native compilation, packaging and a reviewed active Walk↔Run sequence using the new clips; do not describe source-level phase alignment as validated smooth movement.
- The 72-second showcase and 12-second performance workload are scenario schedules, not gait clocks. Different travel/clip durations can alter which pose is visible at a scheduled event. Recheck framing/event overlap when new assets are actually integrated.

Prepared changes cover metadata validation/reporting, metadata-driven Unreal foot support, and the scoped phase/foot-event transition handling above. Python syntax and pure metadata/phase checks pass. The updated Unity runtime and Editor source compile against the exact cached compiler/references from the real project; that is not an Editor import or player build. Unreal native compilation and actual contact/deformation review remain pending. No shared asset or current package was modified.
