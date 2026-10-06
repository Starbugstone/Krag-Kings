# Original TRELLIS — actual isolated environment and kernel checks

The separate Windows Python environment installed successfully and passed dependency consistency checks. Installation and the bounded native GPU probe exited with native/guard exit 0. Existing reconstruction and engine environments were not modified.

Actual FP16 attention and sparse convolution produced finite outputs within the declared 0.01 absolute tolerance of FP32 references. The tiny FlexiCubes sphere produced 128 vertices and 252 triangles. Exact versions, results, logs and resource samples are retained here.

This proves only the tested small kernels work on the RTX 2060. No trained-model weights were downloaded and no concept reconstruction was run at this checkpoint. Full staged inference and dense extraction remain untested; the upstream 16GB recommendation exceeds this machine’s 6GB VRAM. No production asset or artistic acceptance is claimed.
