# Actual Unity fixture: first line renderer invalid

PID31376 closes native/guard1 at the unchanged per-region visible gate. Native HDRP reports CreamHead LineRendererIsValid=false with the correct final shader, while both later regions are valid and visible. Hidden control remains empty and all data transfers exact.

Prewarming before the first camera initializes HDRP sees only one shader pass and does not resolve the problem. This unsuccessful timing change is preserved, not reported as a fix. Next work initializes the actual pipeline before prewarming and records the native compute-setup asset and renderer validity. No character/render/performance acceptance. The two upstream static allocation stacks remain.
