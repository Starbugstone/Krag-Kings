# Nib v4 motion review

Actual source: `Nib_HumanMotion_Study_v4.blend`, SHA256 `e1fb8ea30d0fb7243f182752b7bd42dd4477930525448802cd21e470ee524fbc`.

This retarget uses the saved continuous anatomical body and 79-bone rig. Geometry, shape coordinates and bind are unchanged. The guarded source and full-cycle render jobs exited 0, peaking at 542 MiB and 1,257 MiB private memory respectively. The full 204-frame render receipt is preserved; 24 selected frames are retained in `poses/` and the full sequence remains in the local review directory.

Actual front Walk, front Run and side Run sequences show coordinated hips/trunk/arms and improved forearm continuity. Side review rejects the inherited head calibration: approximately 17 degrees upward during running and 16 degrees downward during walking. Clothing intersections, open/cupped free fingers, face likeness and groom remain failed. Source contact and loop checks do not establish engine slope behavior.

The attempted export launch stopped before starting Blender because 9,700 MiB available RAM was below its 10 GiB launch requirement. No v4 FBX export or roundtrip exists. Later bounded v5 jobs use measured per-job budgets; the global guard and user applications were unchanged.
