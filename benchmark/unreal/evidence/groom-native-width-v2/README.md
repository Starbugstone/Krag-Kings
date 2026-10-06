# Native groom width adapter: actual data pass

All three guarded stages pass with native and guard exit 0: editor-module compilation, three regional Alembic imports, then a separate Unreal process reopening the saved assets. The original [constant-width failure](../groom-native-fixture-v1/README.md) remains preserved.

The adapter checks counts, strand topology and actual point order/space before writing the pinned sidecar diameters to native `FHairDescription` vertex widths. It commits the description and rebuilds derived data through public Groom APIs. All 12 curves/108 authored points retain their varying widths. Maximum diameter error is `3.8743e-10 cm`; maximum position-component error is `4.0867e-7 cm`. Fresh-process readback matches the saved counts, positions, widths and built radius range exactly. Native triangle-strip construction adds one terminal point per curve, yielding 120 built CPU points; the 108-point source topology is unchanged.

This is an explicit importer adapter, not a repaired Alembic schema or engine patch. Blender 5.2's native standard-width array remains in the original ABC; its missing explicit vertex scope is preserved. No original ABC, production project, shared model or executable changed. Generic ABC root UV/color attributes are still absent.

These are CPU asset-data and native rebuild checks, **not rendered taper, character attachment, frame-time or VRAM proof**. The fixture uses retained ABC axes at 100x scale; alignment to the actual skeletal mesh remains a separate gate. Artist acceptance remains false. Raw logs retain incidental editor-startup `LogAutomationTest: Condition failed` entries, separate from the three explicit successful completion markers.

`result.json` records measured process headroom. `execution/` preserves original output and telemetry bytes; `executed-source/` and `executed-plan/` preserve the exact frozen recipe. `artifacts.json` records curated file hashes.
