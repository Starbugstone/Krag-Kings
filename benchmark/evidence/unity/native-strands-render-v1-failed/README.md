# Native Unity strand rendering — first attempt failed

Actual D3D12 process32048 and its guard exited1 before the curve assets or rendered images were produced. The physical-hair Shader Graph import reports a duplicate `PROCEDURAL_INSTANCING_ON` directive. The earlier package/128-strand asset-construction check remains valid; it did not exercise this graphics path.

The native log, telemetry, exact failed graph/source and failure are preserved. The diagnostic points to the official HairVertex subgraph declaring the built-in procedural-instancing keyword as MultiCompile while injecting procedural instancing options. A scoped local subgraph using a predefined keyword is being prepared; no installed engine or upstream package code has been edited. It is not a validated repair yet.

No fur rendering, skin binding, appearance or performance success is claimed for this attempt.
