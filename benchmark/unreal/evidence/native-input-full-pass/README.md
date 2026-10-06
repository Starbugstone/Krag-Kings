# Actual full native input pass

The unchanged Windows package `fe65cc4a…` passes all **40 native mouse/keyboard checks** on 6 October 2026. The game closed normally, the guard and coordinator returned 0, and the original owned-window lease was restored. The run recorded 58 keyboard edges and 17 pointer ownership guards. [Exact result and artifact hashes](summary.json), [original assertions](input-smoke-report.json), [runtime log](runtime.log).

The sequence verifies selection, a Nib shooting while the Krag's melee remains active, both species' melee/shoot/hit keys, bionic switching, applied facial/body morphs, portrait/reset, and terrain Run/Walk commands. Pan, middle-drag orbit and wheel zoom pass while Melee is active. Both actual Krag discharge directions pass the existing 10-degree regression tolerance; this is an animation check, not a gameplay accuracy rule.

The observed-Melee barrier and independent key-release scheduler are exercised here. The requested 250 ms arrow hold measured 256.6288 ms. A passing camera state was observed about 101.6 ms after key-down returned, with a 31.144 cm summed coordinate change while Melee remained active. This measures state-file observation, not exact input-to-photon latency. The earlier 525 ms gap remains unattributed; no game-pan correction was needed to obtain this pass.

Zero-hold clicks also pass. At frame 813, RightShift has already been released when the game dispatches its captured Walk intent (`walk=1`, `currentShift=0`). Frame 929 dispatches an ordinary Run (`walk=0`), and frame 1001 preserves LeftShift Walk after release. These are actual press-time modifier regressions, not longer injected holds.

Three actual F8 images were inspected: [Krag expression](krag-expression.png), [Krag walking state](krag-walk.png), and [Nib expression](nib-expression.png). They retain the old rejected anatomy, eyes, cloth and groom. **Artistic acceptance remains false.** The still images do not establish natural motion. Current shared assets and executable are unchanged; the new 79-bone Nib, whole-body clips and independent Idle offsets are not present in this package.

Movement targets are chosen after the units settle, so this suite does not test active Walk↔Run continuity or a complete breathing cycle. Those need the [separate new-asset motion review](../nib-rig-migration/next-engine-review.md). This diagnostic run includes state writes and screenshots and is not a controlled performance measurement.

The pre-run [frozen recipe](frozen-plan.json) retains its original `executed:false` preparation field; this run's [completion report](native-input-result.json) records actual execution and cleanup. Earlier failed and focused runs remain preserved in their own evidence folders.
