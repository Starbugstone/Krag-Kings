# First coherent79 package launch: input stopped before delivery

The actual `6926aba6…` executable reached `KK_READY`, loaded both Natural units, emitted current state, and closed normally with native/guard exit0. The existing full native suite stopped at its initial foreground ownership gate before acquiring a window lease or delivering any mouse/keyboard input. **0/40 checks completed; the suite is incomplete.** The wrapper correctly exits1 rather than reporting a readiness marker as a controls pass.

The ownership failure does not establish a game input defect. No unrelated window was altered, no lease restoration was needed, and no automatic focus retry occurred. The raw `windowLeaseRestored:false` means no lease was acquired in this attempt. A subsequent read-only query records process/class identity only, without title/content; its explicitly later timestamp cannot prove which application held foreground at the earlier abort.

This establishes current-package startup/state/normal shutdown only. Current-content native controls, full action/terrain verification, movement/Idle/facial review, video and controlled performance remain pending. The previous40-check pass still belongs to the preserved fe65 package. No source-art acceptance is implied.
