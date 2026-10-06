# Actual focused pan diagnostic

The unchanged `fe65cc4a…` Windows package passes all 11 focused checks. During active Melee, the first pan observation records an 8.06 cm camera delta approximately 72.6 ms after Right-arrow key-down. Both injected edges use scan `0xE04D`, are accepted by Windows, and record the game's foreground HWND. This verifies a prompt pan response in this run; the full native suite remains incomplete.

The 250 ms request actually held the key for 319.6 ms because PowerShell observation delayed release. That overrun is preserved explicitly. It did not create the early passing observation, which already satisfies the unchanged >5 cm/active-Melee predicate before 250 ms. No game control code was changed. See [summary](summary.json), [original diagnostic report](input-smoke-report.json) and [runtime log](runtime.log).

PID 2712 closed gracefully, guard/coordinator exit 0, and the original window lease was restored. No screenshot or video capture ran. `LogPSOHitching Verbose` records four 20–49 ms creation hitches at startup frame 0 and none during this tested action/pan interval. The earlier 525 ms/four-frame gap remains unattributed; this run does not prove it was PSO compilation or that all gameplay hitches are resolved.

The next prepared helper schedules release on a dedicated C# worker independently of observation. A small isolated fixture replaced native injection with a stub, blocked its observer for 450 ms, and measured release at 258.08 ms: it occurred before the observer resumed. PowerShell parsing and C# compilation also pass. [Fixture result](timer-source-fixture.json). Real input using the new scheduler is still pending; recorded timestamps will remain authoritative rather than promising exact operating-system timing. JSON depth was also raised so nested diagnostic arrays remain arrays in later reports.

This evidence establishes focused input behavior only. It is not a performance measurement, a completed full native suite, or artistic acceptance.
