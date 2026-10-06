# Actual first Krag bust image-to-3D pilot — rejected

One offline TripoSR inference produced a 213,184-triangle unrigged mesh and eight actual neutral Blender views. The result **fails as a head/bust donor**: it is a thick rectangular plaque with shallow facial relief, incomplete eye/lid anatomy and no believable rear skull. Clay views confirm this is geometry, not merely painted detail. No game asset or rig was changed.

The source crop retains the exact original foreground pixels, beige background and neutral padding. The background rectangle appears in the generated volume. The pinned upstream runner expects gray background when background removal is skipped, so foreground isolation is a justified possible A/B; it has not run. The mesh is preserved intact as failed reference evidence.

Actual free VRAM was 4.99 GiB. The pilot selected FP16-autocast forward, then FP32 field queries in 4096-position batches and a CPU256³ density/marching-cubes stage. Forward took1.97s, extraction10.45s, total68.67s including imports. Torch peak allocation was2.53GiB. This is local inference evidence, not game-render performance or final asset quality.

**Resource telemetry limitation:** the Windows venv executable spawned the real Python worker. The original direct process-private sampler measured the launcher, while global memory/commit safeguards and device-wide GPU telemetry remained active. Worker-private peak/cap enforcement is not established for this run. A late supplemental monitor observed zero samples and supplies no proof. Future Python jobs use process-tree tracking; this inference was not repeated merely for telemetry.

Image-facing relief is `neutral-review/VertexColor_AxisPlusX.png`, sideways under the raw Blender GLB import axes. All six color axis views and both clay views were inspected. Reports preserve the exact input/model/recipe/output hashes; log copies normalize CRLF to LF with both hashes recorded. The saved GLB is an unaccepted study, not a rig-ready character.
