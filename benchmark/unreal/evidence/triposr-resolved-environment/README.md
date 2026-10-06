# Actual isolated dependency resolution

The Windows-only task venv now contains four bootstrap tools: pip25.3, setuptools75.6.0, wheel0.45.1 and packaging24.2. The actual pip dry-run resolved60 runtime packages with exact archive SHA-256 values. The lock, original metadata and license inventory are preserved here; the official local Torch wheel is reused.

The first wrapper exited1 **after pip completed**, because Windows cp1252 could not decode the UTF-8 report. That exact executed recipe/log is retained. A separate explicit UTF-8 finalizer verifies the existing report/input hashes and exits0 with a fresh marker; it did not resolve or download again.

Package metadata records the license terms; llvmlite0.50.0 did not include an expression/classifier, so its exact tagged upstream BSD-2-Clause and LLVM-exception third-party texts are retained separately. Installation preserves original notices. No runtime dependency/native extension/model inference has executed, and no tool executable is committed or shipped. Existing Python environments, global PATH, GPU drivers and game assets remain unchanged. The bounded install/CPU-extension smoke is next; model inference remains a separate scheduled step.
