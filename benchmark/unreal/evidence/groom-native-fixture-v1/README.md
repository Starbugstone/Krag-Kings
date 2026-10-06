# Actual native Groom fixture: width gate failed

The isolated UE 5.8.3 editor module compiled successfully. The native Groom importer created the first CreamHead asset with four curves and 36 points; positions match the source after declared metre-to-centimetre conversion within the measured error in result.json.

**The strict taper check failed.** The description contains four constant strand diameters of approximately 0.008 cm and no per-point width attribute, while the source has 36 distinct radii. Unreal exits 0 after Python failure, but the fresh completion-marker guard correctly returns 89. The other two region files were not imported after the failure.

The installed translator dispatches width handling by Alembic geometry scope. Blender 5.2's source writer populates the per-point array without explicitly setting vertex scope; this matches the observed constant-width branch. Blender's own zero-error radius roundtrip does not establish Unreal taper interoperability. An explicit exact-sidecar restoration is being prepared through native HairDescription commit/rebuild APIs after verifying point order, topology, scale and source hashes. No width approximation or successful adapter is claimed.

This is CPU import evidence only. No strand rendering, character binding, GPU memory, frame rate or artistic quality was tested. The production project, package and shared assets are unchanged. Both owned native jobs/processes closed normally; the preserved import remains failed.
