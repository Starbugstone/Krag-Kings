# Unity press-time movement context — source correction

The existing Windows build `c394a9ba909b477fb315daa0072f83c7` is unchanged. Its foreground-interrupted native run is separate evidence; it did not reach the quick-Shift checks and does not prove their behavior.

The installed Input System 1.19.0 invokes `onEvent` before applying an event to device state. The former scene code read `wasPressedThisFrame`, the current cursor and current Shift state during `Update`; a later release/motion can replace the context of an earlier click. The five-case [source-derived fixture](source-fixture/result.json) uses the exact installed `UpdateWasPressed` method with minimal device/value stubs. It is explicitly **not** a native Unity result.

The source correction retains each rising right-button event's cursor and left/right Shift state in order. Scene Update consumes those commands. Focus/pause, disable, reset and device removal clear pending intent. No game movement or raycasting runs inside the input callback. The input probe records the retained context and dispatch result for native verification.

The [first real queued-event attempt](first-editor-attempt/queued-event-report.json) ran the installed Input System with temporary devices in batch edit mode. It retained one correct `Walk=true` command at `(100,200)` after Shift was released and the pointer moved to `(900,950)`. The check nevertheless failed because it also required the old `wasPressedThisFrame` poll to return true; it returned false. The remaining checks and Windows build **did not run**. Guard/process exit was 1. The old package was preserved in a hash-verified local archive (173 files).

Installed `InputManager.defaultUpdateType` chooses Editor outside play mode; `FlipBuffersForDeviceIfNecessary` swaps editor buffers per event and returns before updating the player step count. The old-poll expectation was inappropriate as a pass requirement for retained intent. The corrected check records that poll, update type and count as diagnostics while strictly asserting released Shift, command order and captured positions. It also checks duplicate held-button reports, reset/removal clearing, inactive capture, and reactivation without inherited Shift. Eight corrected cases are prepared; their real execution remains pending.

Both runtime and Editor sources compile using the cached project compiler/references. The prepared native helper has a focused `-ModifierOnly` path with zero-hold Right Shift, ordinary, Left Shift, ordinary batches. It asserts one accepted command, actual projected cursor, Walk/Run and completion; it records key edges/foreground/modifiers and aborts before new input if foreground or external Windows/Ctrl/Alt state conflicts. It has passed PowerShell parsing and C# helper compilation only. No new native input was sent.

All raw first-attempt artifacts and its exact executed sources remain immutable below this directory. These checks do not establish new character/motion integration, visual acceptance, or a completed new Windows build.

## Second real queued-event attempt

The [corrected v2 run](second-editor-attempt/queued-event-report.json) passed both Shift-release cases and ordered Walk/Run/Walk. Its added held-button report case retained one command, but at the later pointer `(920,960)` instead of the first press `(120,220)`. The strict cursor assertion failed, the editor exited 1, and the build did not run. Remaining lifecycle cases were not reached.

The [installed merger audit](second-editor-attempt/merger-attribution.json) attributes this to FastMouse coalescing adjacent same-button reports before `onEvent`. The setting and per-device interfaces were inspected; no settings were changed during the audit. A supported, scoped preservation setting and bounded dispatch-cost check are proposed. The unchanged existing package remains the only current Windows build.

## Scoped merger correction prepared

The compiled source now leases `InputSettings.disableRedundantEventsMerging` while an interactive movement queue exists. Overlapping leases share ownership and the final disposal restores the exact original value. Automated views retain their prior setting. The standard performance launcher explicitly requests the shipped interactive input profile; startup/profile-change JSON records the actual setting, and performance results also record it. Timed samples still exclude captures and probe writes.

The next frozen v3 job retains all eight strict event cases and checks nested ownership/restoration from both original values. One bounded editor diagnostic queues 1000 pointer reports across 60 updates with merging, then with the production queue/unmerged setting. Its timings measure editor backend dispatch only, without real-time cadence or rendering; they cannot establish native FPS or high-frequency-mouse responsiveness. Real v3 execution, Windows rebuilding and focused native regression remain pending. See the [source preparation receipt](merger-lease-prepared/preparation.json).

## Third real check and Windows build passed

Build `b54531eae98c42ac9f0f20cf513bb0db` now exists. The [third editor run](third-editor-pass/queued-event-report.json) passes all eight real Input System cases, including the original `(120,220)` press cursor, both Shift keys and lifecycle clearing. Nested leases restore both original setting values correctly. Windows BuildPrepared and the guard exit 0 with a fresh success marker. The [receipt](third-editor-pass/build-receipt.json) pins all 174 package files and the unchanged shared fingerprint. No new character assets were imported.

The editor-only diagnostic observed 60 merged and 1000 unmerged callbacks from 1000 reports across 60 updates. Aggregate dispatch times were approximately 0.80 and 0.67 ms respectively. This tiny, single-pass, order-sensitive measurement includes warmup effects and is not evidence that unmerged input is faster, nor any native FPS result.

## First new-package native regression failed

The [focused native run](native-rightshift-failure/native-input-result.json) stopped on its first zero-hold RightShift case. It retained exactly one accepted move, but captured `walk=false` and entered Run; the reported press cursor `(730,208)` also differed from the planned `(689.54,197.65)`. The keyboard probe observed RightShift. Foreground/pointer ownership checks passed and no Windows/Ctrl/Alt modifier was observed held. This is distinct from the passing queued backend checks: native backend event order has not been established.

Actual profile evidence records unmerged reports enabled during play and the original disabled-setting value restored on shutdown. The owned game closed, launcher exited 0, and window restoration passed. The suite is **incomplete/failed**, with no passing native group. No held duration or cursor/modifier threshold has been relaxed.

InputProbe-only Shift/RMB event-edge diagnostics and helper client/DPI/pointer observations are now prepared to attribute native ordering versus coordinate/injection behavior. They have not been built or executed. These diagnostics record only relevant modifiers and pointer/button events, never general typed text. Existing current art remains rejected, and the previous 17 functional checks belong to the earlier c394 build until repeated.

## Actual native event order established

The [diagnostic build and focused run](native-event-order-failure/attribution.json) are now actual evidence. Windows build `b5ca1584d97449cab6fd30c77b82e8f7` succeeds; it contains event tracing but retains the previous Input System movement route. Its first RightShift native case fails again, with one accepted Run command and no passing native group. The owned game closes, its guard exits 0, and the window lease restores.

The helper sent RightShift-down, RMB-down, RMB-up, Shift-up as one zero-hold batch. The actual Input System delivered RightShift-down in frame 199, then RightShift-up, RMB-down, RMB-up in frame 200. Its own event timestamps also place the release before the mouse press. Current keyboard state in `onEvent` therefore cannot recover this press's modifier. Sorting those timestamps or extending a hold would not fix the demonstrated semantics.

This run's requested and observed cursor agree: screen/client `(690,882)` maps to Unity `(690,197)`, within the unchanged two-pixel projected-target tolerance. Client/output dimensions are 1920×1080 and window DPI is 96. The earlier b545 cursor discrepancy remains unexplained; it is not being attributed to this now-proven event-order defect.

## Windows message adapter prepared, not yet run

The [prepared build recipe](windows-message-prepared/preparation.json) now uses the Windows player's own `WM_RBUTTONDOWN`/double-click message, whose `MK_SHIFT` and signed client coordinates describe the press together. The adapter subclasses only the visible `UnityWndClass` belonging to this process, retains the managed delegate, and forwards every message through the preserved original procedure. Its callback contains no Unity API calls. A locked value queue transfers intent to the scene; focus loss, cancellation, device change, pause and disable clear pending intent. Disposal restores the previous procedure when this adapter is still at the top of the chain. If another subclass interposes, the disabled callback stays rooted until window destruction rather than overwriting that chain.

Windows player movement uses only this queue. Input System is an optional diagnostic observer; editor/non-Windows movement retains the explicit existing fallback. The Windows path leaves normal mouse-report merging enabled. Profile evidence records the selected backend and actual setting; the next native coordinator will also require numeric equality between the original and restored window procedure. See Microsoft's [message contract](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-rbuttondown), [subclass operation](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw), and [forwarding contract](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-callwindowprocw).

Both assemblies compile with cached Unity references, and the changed PowerShell helpers parse. The next guarded build archives the exact 174-file b5ca package first. Its focused native check requires both Shift keys and subsequent ordinary clicks, exact single-command dispatch, the original cursor/zero-hold thresholds, matching native modifier evidence, normal merging and safe procedure restoration. **This new Windows adapter has not yet been built or executed.** Existing 17 functional checks remain attributed to c394; new character assets and artistic acceptance remain pending.

## Native message movement passes; shutdown fails

The [actual Windows message build/run](native-message-shutdown-failure/attribution.json) uses GUID `6f623598978b49e69cab5d5bc0b05287`. All four focused native cases pass: zero-hold RightShift, ordinary after RightShift, zero-hold LeftShift, ordinary after LeftShift. Each retains one accepted command, the correct press coordinates and authoritative `MK_SHIFT`, plays the expected Walk/Run and completes. Normal mouse merging stays enabled, no duplicate route dispatches, and the final window procedure numerically matches the original.

The overall result is nevertheless **failed**. Closing the owned game exits with access violation `0xc0000005` (`-1073741819`), after input and code-reload shutdown. Windows records an execute fault at an unknown/JIT address; no symbolized stack or retained dump is available. Numeric restoration does not prove that an already-running managed callback has returned. Forwarding `WM_CLOSE` through that frame while Unity unloads Mono is the concrete lifecycle hypothesis; the exact faulting frame is not proven. Previous package/source/evidence remain preserved.

The [next source correction](windows-close-prepared/preparation.json) retains `WM_CLOSE` as a value request and returns from the callback. Scene Update then detaches the hook and reposts the original close to the restored procedure. ESC and every scene quit path detach before `Application.Quit`. It never overwrites a later subclass, calls no Unity APIs from the native callback, and refuses unsafe close forwarding if restoration fails. Both cached assemblies compile and helpers parse. The next frozen build archives all 174 current package files first. The same strict four-case native test must now additionally prove the close was reposted after detachment and that the game exits normally. **This correction has not yet been built or run.**

## Current d431 close passes; native input is interrupted

Build `d4315c2b22dd47328984db4acf9bbc22` and its [actual native run](native-close-pass-input-interruption/result-summary.json) now prove the revised owned-window close path: restoration precedes the reposted close, the procedure matches the original, the game/guard exit 0, and the window lease restores. The first zero-hold RightShift case also passes. Before the second case, the external-modifier guard stops further input; the final probe reports LeftAlt, which this helper did not send. The cause of that external activity is not established. The suite remains **incomplete, 1/4**, and has not been blindly retried.

The earlier four movement passes belong to 6f62, whose shutdown failed. They are not reattributed to d431. Full native and 17-check functional regression of d431 remain pending, as does an actual ESC-specific lifecycle check. The helper now records the exact modifier that triggers a future guard, without sending extra input or changing thresholds. An unchanged-package full-suite recipe is frozen locally for a later quiet-desktop slot. New character/animation imports and artistic acceptance remain pending.

The close path follows the documented [WM_CLOSE handling](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-close) and [asynchronous PostMessage behavior](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew); documentation did not substitute for the actual normal-exit result above.
