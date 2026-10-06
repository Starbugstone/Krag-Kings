# Native Unity strand compatibility — actual result

The isolated Unity6000.4.4f1/HDRP17.4.0 project compiled the official Demo Team Hair0.19.0-preview.1 and Digital Human0.2.1-preview packages and built a real128-strand asset with8 points per strand. Native process21072 and the existing heavy guard both exited0, with `KK_STRAND_COMPATIBILITY_COMPLETE` in the actual log.

The first fresh import emits GUID API compilation errors; Unity's API Updater resolves them, recompiles successfully, runs the probe and exits normally. Those intermediate diagnostics remain in the complete log. No hand-edited package compatibility fork was needed for this check. The resolved versions and source pins are included.

This establishes package compilation and strand-asset construction only. The process used `-nographics`: GPU strand rendering, native physical-hair shading, skin attachment, ear twitch deformation, artistic acceptance and frame cost remain untested. The main benchmark project, shared character assets and Windows build are unchanged by this isolated probe.

Prepared follow-up: use the actual Blender native-curve fixture with explicit metre/diameter conversion, then the Nib regional groom, under the same memory guard.
