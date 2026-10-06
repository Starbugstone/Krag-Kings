# TRELLIS route feasibility — read-only, 6 October 2026

**Do not install the full AISmith app for this machine yet.** The inspected sources do not establish a working RTX 2060/Turing 6 GB geometry-plus-PBR route. No weights, binaries or packages were downloaded; no inference or concept upload occurred. The prepared Nib macroface diagnostic remains the next art task.

## What actually runs

AISmith Generate invokes a separate `ilintar/trellis.cpp` executable with `--no-texture`, not its vendored `trellis2cpp`. That upstream repository and GitHub API returned 404 during this check. The model repository still exists but labels its license `other`. [Pinned native worker](https://github.com/intisarGIT/AISmith-3D/blob/8af574dd3011ff5668e572798a644996b79b93d8/backend/app/native.py#L290-L312), [model metadata](https://huggingface.co/ilintar/trellis2-gguf).

The linked public `rms80/trellis2cpp` main is early stage-1 scaffolding: DINO conditioning → sparse occupancy → coarse watertight mesh. It is not a replacement for the complete shape/detail/PBR pipeline. AISmith carries a substantially expanded, different vendored copy; its README cites a 16 GB RTX 50-series test and roughly 10 GB VRAM plus a 14 GB host-RAM spike for the 1024 path, not a 6 GB Turing result. [Public stage-1 README](https://github.com/rms80/trellis2cpp/blob/0196744a1c630fa5c95141d8f6808ba4f7c8e487/README.md), [vendored measured claim](https://github.com/intisarGIT/AISmith-3D/blob/8af574dd3011ff5668e572798a644996b79b93d8/vendor/trellis2cpp/README.md#L110-L113).

## Concrete FP8 compatibility gaps

The short-lived Python worker genuinely selects staged loading (`low_vram=True`, `keep_models_loaded=False`). However, dense `sdpa` does not cover sparse attention: the same call hardcodes `sparse_backend="flash_attn"` and `conv_backend="flex_gemm"`. Its pinned wrapper stores FP8 weights but temporarily converts weights/activations to BF16 for execution. There is no SM7.5/FP16 fallback in that inspected path. [Worker](https://github.com/intisarGIT/AISmith-3D/blob/8af574dd3011ff5668e572798a644996b79b93d8/backend/workers/trellis2_fp8_worker.py#L53-L65), [pinned execution casting](https://github.com/visualbruno/ComfyUI-Trellis2/blob/438fe4e2a15bd29620a1cedad0a87c5afad6f81d/trellis2/modules/utils.py#L74-L137), [sparse calls](https://github.com/visualbruno/ComfyUI-Trellis2/blob/438fe4e2a15bd29620a1cedad0a87c5afad6f81d/trellis2/modules/sparse/attention/full_attn.py#L222-L234).

RTX 2060 is compute capability 7.5. Standard FlashAttention-2 targets Ampere/Ada/Hopper; Turing uses a separate subset implementation. Current upstream Triton lists NVIDIA capability 8.0+, and BF16 Tensor Core support was added with Ampere. Therefore this particular worker needs a proven compatible backend/precision port, not just offload flags. This is a source-based incompatibility assessment, not an executed failure. [NVIDIA GPU table](https://developer.nvidia.com/cuda/gpus?hl=tr), [FlashAttention support](https://github.com/Dao-AILab/flash-attention#nvidia-cuda-support), [Triton support](https://github.com/triton-lang/triton#compatibility), [NVIDIA precision support](https://docs.nvidia.com/cuda/archive/11.0/ampere-tuning-guide/).

The package also is not self-contained as documented: `vendor/ComfyUI-Trellis2` is a gitlink to `438fe4e…`, while the root tree has no `.gitmodules` mapping. A plain clone leaves the required integration unavailable. Its installer expects that source plus exact Python3.12/Torch2.8 CUDA wheels. Resolving this is feasible manual dependency work, but no successful isolated install is claimed. [Installer](https://github.com/intisarGIT/AISmith-3D/blob/8af574dd3011ff5668e572798a644996b79b93d8/backend/app/main.py#L372-L423), saved complete tree/commit metadata here.

## Memory and licensing

The FP8 safetensor files total **8,118,964,605 bytes**, before DINOv3 and the legacy sparse decoder. Stage loading reduces simultaneous model residence, but activations, temporary BF16 conversion, decoding and mesh/PBR processing are not bounded by that file size. No inspected source supplies a reliable peak for our 31.8 GiB host or current guarded headroom. Retain our existing guard; do not infer safety from 32 GB installed RAM. Microsoft's official reference requires at least24 GB GPU memory. [Official prerequisites](https://github.com/microsoft/TRELLIS.2#prerequisites), [FP8 model](https://huggingface.co/visualbruno/TRELLIS.2-4B-FP8).

Microsoft's model and code are MIT, and the FP8 model metadata also says MIT. DINOv3 has its own license and the original weights require an access agreement/contact-sharing step; it is not an all-MIT stack. Model/code licensing alone does not establish output copyright or concept fidelity. No commercial-output restriction was found in the inspected MIT texts, but the unavailable native runtime and its `other` model label prevent a complete license clearance for that path. [Microsoft license statement](https://github.com/microsoft/TRELLIS.2#%EF%B8%8F-license), [DINOv3 model/access/license](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m), [third-party notices](https://github.com/intisarGIT/AISmith-3D/blob/8af574dd3011ff5668e572798a644996b79b93d8/THIRD_PARTY_NOTICES.md).

## Exact conditional pilot command — NOT executed or currently cleared

A future compatible, pinned runtime can call the existing one-shot worker without Node/Vite, a browser or a ComfyUI server. This command matches its actual JSON argument API; it is **not runnable from the incomplete clone alone** and does not fix the Turing backend issues:

```powershell
$spec = @{
  operation = 'generate'
  runtime = 'D:\Dev\Krag-Kings\benchmark\local\tools\trellis2-pilot\runtime'
  source_image = 'D:\Dev\Krag-Kings\benchmark\local\tools\trellis2-pilot\input\nib-single-view.png'
  output_glb = 'D:\Dev\Krag-Kings\benchmark\local\tools\trellis2-pilot\output\nib-512.glb'
  resolution = 512
  gpu_first = $false
} | ConvertTo-Json -Compress
& 'D:\Dev\Krag-Kings\benchmark\local\tools\trellis2-pilot\.venv\Scripts\python.exe' `
  'D:\Dev\Krag-Kings\benchmark\local\tools\trellis2-pilot\AISmith-3D\backend\workers\trellis2_fp8_worker.py' $spec
```

Before scheduling this: resolve the exact backend/precision/kernel compatibility, obtain permitted model access, pin dependencies and run a guarded small kernel probe. Then use512 only, a local single-view crop, one serial process, measured RAM/VRAM and no engine overlap. A successful output would be a provisional shape/PBR study; it supplies neither our anatomical rig nor approved hidden surfaces. Given the current blockers, defer this route rather than spending the next art boundary installing it. TripoSG evaluation, if pursued later, is a separate task.

All small source downloads and hashes are recorded in the adjacent JSON manifests. Upstream source copies are evidence only, never imported or executed.
