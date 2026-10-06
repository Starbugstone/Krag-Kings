# Preserved cached-binding diagnostic failure

The diagnostic helper compiled with native/guard exit0. Its next head-only process exited native/guard3 at `GroomBindingBuilder.cpp:2596`: the probe called `GetRootData` while a cached render-root bulk buffer was not loaded. The earlier uncached build happened to leave that CPU data resident; finishing asset compilation does not guarantee residency on the cache path. This is a probe readback defect, not a measured character or width failure.

No worst-triangle diagnostic, accepted binding, saved Groom/Binding, image or performance result was produced. The original 0.1mm gate was unchanged. Exact executed source and failure logs are preserved.

The supported repair identified in installed5.8 headers is `UGroomBindingAsset::StreamInForCPUAccess(true)`, followed by explicit required-buffer checks before `GetRootData`. It loads CPU data through the native DDC/IO path; no engine patch, DDC deletion or source geometry change is needed. A corrected actual diagnostic remains pending.
