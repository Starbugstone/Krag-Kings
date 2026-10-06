# Sand material source review — first scan candidate

Actual matching Blender renders from 6 October 2026, generated using the scripts committed in `34a585a`. Geometry, camera and lighting are identical in each baseline/candidate pair. This is source-material evidence, not a game screenshot or performance measurement.

The scan adds convincing irregular grains, but this first candidate is too grey/damp for the dry-desert palette. It was **not promoted**. The next candidate keeps the physical scan detail, uses a warmer proposed tan palette and reduces the normal intensity. A small actual Blender/Windows bitmap check also established that the pixel API here returns encoded byte values; v2 explicitly decodes sRGB before filtering and encodes it on save. The first version's recipe incorrectly described its direct-byte box average as linear.

The generated isolated source remains in `benchmark/local/candidates/sand-scan-v1/`; its render-time hash is preserved in `source-review.json`. The original editable terrain, retained scans and reproducible source scripts remain in version control. No character or shared runtime material changed during this study.
