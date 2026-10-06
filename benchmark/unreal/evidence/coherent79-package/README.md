# Coherent79 Nib Windows package

Unreal 5.8.3 compiled, cooked, staged and archived the updated content successfully. Native and guard exit were 0, with fresh `BUILD SUCCESSFUL` and `KK_PACKAGE_COMPLETE` markers. The complete package is at `benchmark/builds/unreal/Windows`; its real executable SHA-256 is `6926aba6478bc42cd8db6eda6c234a3c2f4ff88184922f069deb2d19ca873a8b`. The source snapshot SHA is `1191f86f6279ce8848319b54bfd516b1604f4cb75ccf998b7fbc330e3d65498e`.

All three new Nib mesh/Skeleton/animation sets and the four unchanged Krag variants are included. The new Nib has 79 authored bones, 25 morphs, 27 material slots and seven matching clips. Native changes include independent Idle initialization and the audited imported-rig getters. Profile/DefaultLit alternatives are cooked, while ordinary startup remains Generic until an explicit `-KKSkinMode=Profile` override is provided.

The build took 187.31 seconds. The observed descendant-process private-memory sum peaked at 5759 MiB; system available memory stayed at or above 6737 MiB. The unchanged 10 GiB tree cap remained active. Packaging verifies nonempty PE/data containers and the bundled x64 CRT installer. It is not clean-machine or runtime proof.

The preceding fe65 package is preserved with all 96 files and 1,221,401,716 bytes verified individually in `prior-package-archive.json`. Its 40-check native pass remains attached to that earlier executable/content. This new package has not yet run; functional/native controls, motion review, showcase and performance remain pending. The nine new-content images in `../coherent79-editor-review` came from actual editor game mode. Character art remains failed, including Nib groom/cowl and old Krag anatomy/likeness.
