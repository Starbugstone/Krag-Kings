# Actual native run stopped on lost foreground

Existing Unity build `c394a9ba909b477fb315daa0072f83c7` passed two native check groups: Nib shooting while Krag Melee continued, and orbit/zoom/arrow pan while Melee was active. The new observation barriers recorded fresh Melee at frames 283 and 319. The requested 90 ms keyboard holds, mouse holds and camera thresholds were unchanged. [Original assertions](windows-input-verification.json), [summary and artifact hashes](summary.json).

Before the species-specific controls, the foreground and pointer window changed from game HWND 2362016/PID 6556 to HWND 5704170/PID 8684. The guard stopped before sending further input. A later read-only query identifies the still-valid owner as `explorer`, class `XamlExplorerHostIslandWindow`; only process/window metadata was read. The reason it became foreground is not established. Per-key edge timestamps were not recorded in this attempt.

The game closed normally, launcher exit was 0, and the owned-window lease was restored. The coordinator correctly returned 1 because the full suite was incomplete. No focus retry or unrelated-window intervention occurred. Quick-Shift checks were not reached, so no Unity rapid-modifier defect is established. No player rebuild, new asset import, performance result or artistic acceptance is implied.
