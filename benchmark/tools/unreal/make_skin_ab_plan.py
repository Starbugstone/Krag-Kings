"""Prepare explicit, provisional skin-profile settings from unchanged source maps.

Requires Pillow; for example: uv run --with pillow make_skin_ab_plan.py
This reads pixels for statistics only; it never changes source images.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image

BENCHMARK = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_linear_rgb(path):
    with Image.open(path) as image:
        channels = image.convert("RGB").split()
        result = []
        for channel in channels:
            histogram = channel.histogram()
            linear = [(v / 255 / 12.92 if v / 255 <= .04045 else ((v / 255 + .055) / 1.055) ** 2.4) for v in range(256)]
            result.append(sum(n * v for n, v in zip(histogram, linear)) / sum(histogram))
        return result


def main():
    candidates = []
    for folder in ("krag", "nib"):
        root = BENCHMARK / "shared" / "characters" / folder
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8-sig"))
        for mat in manifest["materials"]:
            name = mat["name"]
            if mat.get("alphaMode") == "MASK" or not (name == "Nib_v5_DustyPinkEar" or any(word in name.lower() for word in ("skin", "muzzle", "earinner"))):
                continue
            paths = {kind: root / mat[kind] for kind in ("baseColor", "normal", "roughness", "metallic")}
            candidates.append({
                "name": name, "folder": folder,
                "baselineMaterial": f"/Game/Benchmark/Characters/{folder}/Materials/M_{name}",
                "sourceTextures": {key: {"path": str(path.relative_to(BENCHMARK)).replace("\\", "/"), "sha256": sha(path)} for key, path in paths.items()},
                "surfaceAlbedoLinear": [max(.01, value) for value in mean_linear_rgb(paths["baseColor"])],
                "meanFreePathDistanceCm": .10 if folder == "krag" else .18,
                "meanFreePathColor": [1, .55, .28] if folder == "krag" else [1, .46, .24],
                "worldUnitScale": .1, "opacityMask": .25 if folder == "krag" else .6,
                "tint": [1, 1, 1], "transmissionTintColor": [1, 1, 1], "ior": 1.4,
            })
    plan = {
        "schemaVersion": 1, "recipe": "skin-ab-v1-defaultlit-burley-profile",
        "status": "Provisional renderer experiment; not an accepted material/design",
        "changes": "Alternative materials only; original generic materials, textures, meshes, lighting and exposure remain unchanged.",
        "interpretation": "UE factory Burley/MFP enabled. Mean-free-path distances use documented cm fields. Default worldUnitScale .1 is retained. Per-species distances/masks are tuning candidates, not numerical equivalence to Unity diffusion profiles.",
        "surfaceAlbedoMethod": "Per-channel mean after exact sRGB-to-linear decoding of all BaseColor pixels, clamped to UE profile field minimum .01; no image edits or tint multiplier.",
        "profiles": candidates,
    }
    path = Path(__file__).with_name("skin-ab-plan.json")
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(candidates)} skin materials at {path}; Unreal import/render remains unexecuted.")


if __name__ == "__main__":
    main()
