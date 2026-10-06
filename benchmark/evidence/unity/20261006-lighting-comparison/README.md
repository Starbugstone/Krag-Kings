# Actual Unity lighting comparison — 6 October 2026

The current pretriangulated Krag v7 / Nib v4b assets were measured in the packaged Unity 6000.4.4f1 demo on the user's i7-10750H / RTX 2060 6GiB laptop. Output and internal resolution were both 1920×1080. Each run warmed for 15 seconds and sampled 30 seconds without capture or input-probe writes. Build `c4767943faf24b91b8fbc5157f46b339`; all runs use the same source content fingerprint. AC was connected and the Windows Performance scheme was active; the ASUS vendor mode was not queried or changed.

| Actual workload / setting | Mean FPS | Mean frame time | p95 | p99 |
| --- | ---: | ---: | ---: | ---: |
| Full, repeated movement/melee/shoot/hit | 40.77 | 24.53ms | 30.73ms | 42.48ms |
| Balanced, same movement/action sequence | 57.95 | 17.26ms | 21.47ms | 24.07ms |
| Balanced, idle pair | 58.15 | 17.20ms | 20.73ms | 23.43ms |

Balanced uses half-resolution screen-space global illumination and disables screen-space reflections. Geometry, textures, native resolution, TAA, skin scattering, ambient occlusion and contact shadows stay the same. Full and Balanced post-sample wide-view images were inspected; the lighting difference is subtle at this framing. Close-up and motion review remain necessary. These results support continuing with Balanced as a candidate; they do not establish a locked 60 FPS, finalized artwork, or a winner over Unreal.

`comparison.json` derives the summaries from the actual reports and telemetry rows inside each UTC sample interval. GPU temperature was 82–83°C in the Full moving sample, 81–85°C in Balanced moving, and 81–84°C in Balanced idle. Graphics clocks varied; these short sequential runs do not isolate thermal effects or establish a sustained-session bound. Device-wide used VRAM was 1842–1843MiB for Full and 1814–1816MiB for Balanced; this includes other GPU use and is not a per-game allocation measurement. Peak sampled game private memory was 3207MiB Full and 3170MiB Balanced. Raw values and run conditions are retained alongside each report.

The screenshots are actual post-sample game captures, not concept art. Visible primitive anatomy, cloth/strap construction and Nib facial/groom defects remain under active source refinement; none of these models has passed likeness review. Timing must be repeated when the improved assets are imported. The earlier dense Full idle baseline belongs to a different build, lighting and workload and is not used as a direct before/after reduction claim here.
