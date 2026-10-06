# Actual Unity topology diagnostic and independent attribution

PID29352 closes native/guard1 at the original exact-count gate: Unity imports570,008 triangles from570,134. The sole skinned mesh is active,332,538 imported render vertices,23 material slots. All13 anatomical anchors fit within0.128401µm; the fitted coordinate map is approximately(−x,z,−y), checked against actual imported bones rather than assumed.

Independent raw FBX versus captured Unity point/index comparison proves all126 missing triangle multiplicities have **exactly zero area**. Source has128 zero-area faces, import retains2. There are zero added triangles and the entire nondegenerate geometric triangle multiset matches. Every imported point lies within0.480115µm of its source position. The−0.0320000015m mesh-local Z offset is resolved from the authoritative exported world bounds, with both bounds required to agree; no arbitrary rotation/scale fit is used for the mesh comparison. This proof does not validate normals, morph deformation, animation or likeness.

The raw buffers and their hashes are retained. The bounded v3 importer accepts the126-face difference only when current source FBX, actual imported positions/indices and independent zero-area-only proof all match. A count-only relaxation is not used. Full26k curve asset construction and engine binding/rendering remain pending at this checkpoint.
