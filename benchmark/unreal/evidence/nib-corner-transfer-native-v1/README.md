# Actual corner-preservation fixture

Blender 5.2 and the real FBX exporter pass this bounded hard-edge fixture with native/guard exit0 and the fresh completion marker. Two quads share vertices while retaining different per-corner normals, UVs and materials; one authored morph is also present. The disposable triangulation produces four triangles with unchanged oriented boundaries and exact point/morph/mapped-normal payloads (normal error 0).

The executed recipes, actual source/target FBXs, corner provenance, raw comparison and telemetry are preserved. This proves the small native path, not the full Nib candidate. The subsequent full-character raw gate additionally requires byte-identical mapped corner normals; older no-map validation retains its existing tolerance.
