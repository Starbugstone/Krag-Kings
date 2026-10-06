# Actual cleaned Nib mask and origin check

The isolated Unreal 5.8.3 process completed with native/guard exit 0 and the fresh `KK_GROOM_CHARACTER_MESH_COMPLETE` marker. It saved the Natural skeletal mesh and its skeleton after all 79 authored bone origins and the actual binary float32 `KKGroomBindable` render buffer passed. The previous strict-wrapper failure remains in `../groom-character-mask-v1`.

The exact raw FBX identifies `Nib_Rig` as the top-level Null armature container. The retry accepts only this explicitly audited wrapper, verifies its zero origin/uniform scale and sole Root child, and normalizes only the authored Root parent label for comparison. Actual component transforms remain intact. All authored origins match `(100x, -100y, 100z)` with no fitted translation or arbitrary scale; the largest component residual is 0.0000124054 cm (0.124 micrometers). This is an origin/hierarchy check, not full rotational bind parity.

The imported mesh has 350,779 render vertices, 60,420 eligible mask vertices, 102,736 eligible triangles and 25 morph targets. The source has 79 bones; Unreal retains the additional verified armature wrapper. Generated package hashes are recorded in `result.json`, with packages remaining local/generated. The compiled native module was reused from the successful v1 compile after exact source/binary checks.

No strand binding, posed attachment, image, frame-time or runtime Skin Cache claim follows from this check. Fresh-process package reload and animation import remain pending. The frozen source's known groom and character-art failures remain; shared assets and production packages were untouched.
