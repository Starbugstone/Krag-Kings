# Complete organic anatomy study — ungenerated

This separate source branch prepares an editable continuous body beneath the
existing clothing, including hips, legs and feet. It does not modify the frozen
v9d head/cloth recipe or the current shared runtime package.

`complete_body_fit.py` warps the retained CC0 Blender Studio body cage into the
existing Krag upper-body shape and provisional lower-body landmarks.
`measure_complete_body.py` has run as a small read-only NumPy calculation. Its
report records dimensions and normalized weights, not a generated model or a
successful deformation test.

`append_complete_body.py` is syntax checked but has not run. It will save a new
master containing a hidden, separately named full organic study. It deliberately
has no runtime `module` tag. The visible established clothing/armor assembly
remains available for comparison. The study uses live subdivision and the
current skeleton plus explicit body corrective keys created from Basis.

Before accepting this anatomy, inspect neutral front/side/back and bare feet,
then Walk, Run, Melee and Shoot. The current Foot control is at z=0.24 m; a bare
foot review must determine whether its bend/roll pivot needs refinement. Foot
and hidden pelvic details are provisional because the approved sheet covers
them with boots and clothing. No new anatomy is claimed as approved canon.

The v9d scarf also remains unreviewed. If its gathered strip still looks rigid,
the next separate cloth study should use a sparse, nonintersecting control
surface, rear-neck pins defined by strip coordinates, torso/neck collision
geometry, and 3–4 mm self-collision spacing. The old `settle()` numeric pin
indices refer to a different mesh layout and must not be reused. Settle the
control cloth before adding subdivision and thickness, then inspect actual
front, side and back renders. This is a prepared fallback, not a completed
simulation.
