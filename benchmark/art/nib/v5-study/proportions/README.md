# Nib image measurement study

`proportion-review.html` overlays editable pixel landmarks on the original
sheet and two explicitly identified actual renders. The accompanying JSON
preserves source/image hashes, definitions and rough endpoint uncertainty.
The HTML is a prepared local review aid; its browser rendering has not yet
been checked. No generated image is being used as model evidence.

These are approximate manual 2D picks. Camera perspective, head tilt and
expression differ. They establish tendencies to inspect, not new canonical
dimensions or an automatic scale instruction.

| Approximate ratio | Sheet 02 | Actual source view |
| --- | --- | --- |
| Ear span / ear-tip-to-sole height | 0.41 | 0.45, v4b Front |
| Visible face width / same height | 0.11 | 0.12, v4b Front |
| Visible face height / same height | 0.09 | 0.11, v4b Front |
| Shoulder-band width / same height | 0.22 | 0.27, v4b Front |
| Near-eye opening width / height | about 2.3 | about 4.3, v5c Face |

The current eye opening reads too flat even allowing for uncertain endpoints.
The code also compresses orbital height twice: the general vertical landmark
warp and a second local factor of 0.22. Both need review together rather than
simply raising the eyes. The current nose width is narrowed by up to 34% in
`fit_head.py`, followed by a second lower-tip taper and narrow pigment mask.
The next geometric study must inspect pad width, nostril/alar shape and short
muzzle projection as one continuous surface; changing only pigment cannot
turn the current human nose into the concept's animal nose.

No v5c body Front exists, so the body ratios deliberately use v4b. The frozen
v5c Face source still fails likeness; its queued actual profile/three-quarter
captures must establish depth before the next warp is authored. Fuller ear/head
fur and compressed scarf layers remain important, but microdetail does not
resolve the face-volume mismatch. No enlarged head or redesigned species
proportions is authorized by this study.
