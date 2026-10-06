# Current-package native input: incomplete

The actual Windows package `4ef237f0…` received owned-window mouse and keyboard events after the user dismissed the picker. Ten checks passed: selection, independent overlapping actions, Krag melee/shoot/hit, both authored discharges with actual aim errors below 2.48°, and camera pan during an action.

The suite stopped at its orbit threshold. Native middle-button and mouse-axis events reached the game, but the saved camera moved only 0.942° from its default yaw; the gate required more than 1°. The archived state was copied later, so it is not an immediate before/after pair. Template axis sensitivity 0.07, FOV scaling and smoothing compound the controller's own sensitivity. The final injected move also shared a frame with button release. Neither a zero-motion claim nor a full input pass is supported.

The owned game closed normally and the window lease was restored. Guard exit 0 means the fresh readiness marker was present; the input script itself exited 1. Remaining checks were not executed. Corrected explicit orbit settings and stronger action-active input evidence are prepared separately for the next build/test. Character art remains unaccepted.
