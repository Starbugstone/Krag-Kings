# Orbit correction verified; native suite still incomplete

Actual Windows package `f15ff67b…` passes 31 native input checks. Middle-drag moves yaw from 75° to 87.58° while melee remains active; all four native samples show raw=processed mouse axes and sensitivity 1. Wheel zoom and pan during actions also pass. Selection, independent actions, both Krag discharges, both species' action keys, variants, facial controls, portraits and Krag run/walk pass.

The suite stopped at the later Nib RMB run check. Its down/up events arrive in frame 502 immediately after an F8/Home sequence with no observed camera-reset wait; no accepted-movement log follows. Event dispatch uses IE_Pressed, and installed engine source retains same-frame press/release events, so dropped fast-click handling is not established. The prepared verifier keeps its 60ms tap and now observes the actual wide camera and another fresh state before that click. This retry has not yet run.

The coordinator retained the failure, closed only its owned game and restored its window lease. Guard exit 0 confirms readiness and normal shutdown; coordinator exit 1 preserves the failed suite. The actual Nib portrait is unedited runtime output and still fails the character-art gate.
