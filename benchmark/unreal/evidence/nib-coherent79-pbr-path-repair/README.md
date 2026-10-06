# Actual portable texture repair and matched views

The path-only derivative `2a3ab470…` passes reopened image validation: all98 maps decode from the new relative root, with original SHA-256 values and color spaces. No maps were rebaked. A separate saved-file comparison passes the exact79-bone hierarchy/bind, seven canonical action curves/17 poses per take and mesh/weight/morph payloads.

All three actual repaired Face/Tongue/Front renders were inspected against the [unchanged source views](../nib-coherent79-pbr-reopen-failure/source/). Nose pigment, skin/ear separation, pale/tawny groom, eye/goggle response, dark-blue tongue and clothing retain the source appearance without an obvious new transfer regression. These are Blender material-transfer checks, not engine evidence or artistic acceptance. The face, anatomy, groom and hand/clothing failures remain open; back/UV seams and engine shaders still need review.

The original magenta file/frame remains preserved. The first correction attempt (v2) stopped with code2 on a Windows-path validator bug: `pathlib` treated Blender's `//textures\filename` as a UNC share. The v3 helper normalizes Blender slashes before parsing the basename. The saved-path failure and this validation failure are both retained; neither is erased by the later pass. All final guard/native exits are0. No shared package or existing engine asset changed.
