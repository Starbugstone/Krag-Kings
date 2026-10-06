# Actual Unity native strand fixture render

The static12-strand/108-point fixture now passes the visible/hidden image gate on the RTX2060/D3D12 with Unity6000.4.4f1/HDRP17.4. PID28096 closes native/guard0. Actual images were visually inspected: all three four-strand regions appear, and the hidden comparison is an empty uniform background. This is not a full-character groom, attachment or performance result.

Initializing the first actual HDRP camera **before** prewarming selects all10 relevant material passes instead of the fallback single pass. All three native line renderers then have the actual ComputeShader-VertexSetup and are valid at the initial check. The bounded cache-rebind fallback did not execute. Earlier failed attempts remain preserved.

All authored asset positions/diameters remain exact. Visible changed-pixel counts are27,601 /19,584 /7,739 in independent projected region bounds; hidden RGB range0,183 completed camera callbacks, no collected managed errors. Radius rendering still uses the official fitted taper and constant regional colors; full authored color/diameter shading is a separate prepared diagnostic.

Two upstream static allocation reports remain on editor exit (LongOperation cache and CoreUtils.emptyBuffer). The owned188-allocation recreation defect and camera target warning are fixed, but this is not a claim of clean upstream shutdown or absence of every leak. Exact native logs, telemetry, staged source and frames are hashed in files.json. No production project/build changed.
