# Actual isolated TripoSR setup

The guarded Windows installation exited 0 with a fresh completion marker. All 60 resolved package versions match the reviewed hash lock, and `pip check` reports no broken requirements. The historical MIT CPU marching-cubes sources compiled with the existing VS2022 toolchain and two workers. A real CPU sphere extraction produced 480 vertices and 956 triangles with Torch 2.5.1+cu121.

The environment is confined to `benchmark/local/triposr-reference-v1`; existing Python environments, PATH, drivers, engine tools and shared character assets are unchanged. The local checkpoint is hard-linked and its exact hash remains pinned. No image-model inference or generated reference mesh exists yet. The next separate pilot uses the approved Krag bust crop, checks actual free VRAM, and bounds extraction memory. Installation success does not establish model compatibility, visual quality or rig suitability.

The original Windows receipt is preserved byte-for-byte. Curated logs normalize CRLF to LF only; raw and curated hashes are recorded in `result.json`. Executed source and the installed distribution metadata inventory are included. Tool binaries and model weights remain local and are not committed.
