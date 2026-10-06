# Unchanged-package retry: Shift intent lost

The second actual run of package `f15ff67b…` passed 23 checks, then failed the Krag Shift+RMB Walk check before reaching the later Nib camera-reset probe. Its RMB press/release both arrived in frame 403. `KK_MOVE` proves that the terrain command was accepted; Walk was never observed before the unit returned to Idle. The owned game closed normally and the coordinator retained exit 1.

The source samples Shift during deferred input-delegate processing, after a same-frame release can clear it. A prepared correction captures the platform's event-time left/right Shift state and cursor position per press, then consumes contexts through the existing event binding. Focus/flush and end-of-frame cleanup prevent stale contexts. New logs will expose both captured and dispatch-time modifiers and terrain rejection reasons. This source has not yet compiled or run.

The verifier keeps normal 60ms taps and its explicit camera observation. Separate immediate unmodified/right-Shift/left-Shift tests will check rapid intent changes. The earlier Nib failure remains unresolved; this run did not reach it.
