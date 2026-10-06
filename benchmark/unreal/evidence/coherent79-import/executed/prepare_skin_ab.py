"""Create isolated renderer-review materials; never mutate baseline meshes/materials."""
import hashlib
import json
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
BENCHMARK = PROJECT.parents[1]
PLAN_PATH = BENCHMARK / "tools" / "unreal" / "skin-ab-plan.json"
DEST = "/Game/Benchmark/Review/SkinAB"
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIBRARY = unreal.MaterialEditingLibrary


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    result = unreal.EditorAssetLibrary.load_asset(path)
    if result is None:
        raise RuntimeError("Required existing asset missing: " + path)
    return result


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError("Failed to save review asset: " + asset.get_path_name())


def package_file(asset_path):
    return PROJECT / "Content" / (asset_path.removeprefix("/Game/") + ".uasset")


def color(values):
    return unreal.LinearColor(*values, 1.0)


def bindings(mat):
    result = {}
    for name in ("BASE_COLOR", "NORMAL", "ROUGHNESS", "METALLIC"):
        prop = getattr(unreal.MaterialProperty, "MP_" + name)
        node = LIBRARY.get_material_property_input_node(mat, prop)
        if not isinstance(node, unreal.MaterialExpressionTextureSample):
            raise RuntimeError("Expected unchanged PBR texture input: " + mat.get_path_name() + " " + name)
        result[name] = {"texture": node.get_editor_property("texture").get_path_name(),
                        "output": LIBRARY.get_material_property_input_node_output_name(mat, prop)}
    return result


def profile_for(entry):
    name = "SP_" + entry["name"]
    path = DEST + "/" + name
    profile = unreal.EditorAssetLibrary.load_asset(path)
    if profile is None:
        profile = TOOLS.create_asset(name, DEST, unreal.SubsurfaceProfile, unreal.SubsurfaceProfileFactory())
    settings = profile.get_editor_property("settings")
    values = {"enable_burley": True, "enable_mean_free_path": True,
              "surface_albedo": color(entry["surfaceAlbedoLinear"]),
              "mean_free_path_color": color(entry["meanFreePathColor"]),
              "mean_free_path_distance": entry["meanFreePathDistanceCm"],
              "world_unit_scale": entry["worldUnitScale"], "tint": color(entry["tint"]),
              "transmission_tint_color": color(entry["transmissionTintColor"]), "ior": entry["ior"]}
    for key, value in values.items():
        settings.set_editor_property(key, value)
    # Reflected structs are copied, so assign the modified struct back explicitly.
    profile.set_editor_property("settings", settings)
    saved = profile.get_editor_property("settings")
    if not saved.get_editor_property("enable_burley") or not saved.get_editor_property("enable_mean_free_path"):
        raise RuntimeError("Burley/MFP profile settings did not persist")
    save(profile)
    return profile


def alternative(original, entry, mode, profile):
    name = "M_" + entry["name"] + "_" + mode
    path = DEST + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not unreal.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError("Cannot replace task-owned review material: " + path)
    mat = TOOLS.duplicate_asset(name, DEST, original)
    if mat is None:
        raise RuntimeError("Material duplication failed: " + path)
    for prop in (unreal.MaterialProperty.MP_SUBSURFACE_COLOR, unreal.MaterialProperty.MP_OPACITY):
        node = LIBRARY.get_material_property_input_node(mat, prop)
        if node is not None:
            LIBRARY.delete_material_expression(mat, node)
    if mode == "Profile":
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
        mat.set_editor_property("subsurface_profile", profile)
        mask = LIBRARY.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 980)
        mask.set_editor_property("r", entry["opacityMask"])
        if not LIBRARY.connect_material_property(mask, "", unreal.MaterialProperty.MP_OPACITY):
            raise RuntimeError("Profile scattering mask connection failed")
    else:
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        mat.set_editor_property("subsurface_profile", None)
    for usage in (unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS):
        LIBRARY.set_base_material_usage(mat, usage, True)
    LIBRARY.recompile_material(mat)
    if bindings(mat) != bindings(original):
        raise RuntimeError("A/B changed a PBR input")
    save(mat)
    return mat


def main():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    baseline = {entry["baselineMaterial"]: digest(package_file(entry["baselineMaterial"])) for entry in plan["profiles"]}
    data = load("/Game/Benchmark/DA_Benchmark")
    # Fail before any changes if this editor still uses the previous native DLL.
    data.get_editor_property("skin_default_lit")
    defaults, profiles, results = {}, {}, []
    for entry in plan["profiles"]:
        for source in entry["sourceTextures"].values():
            if digest(BENCHMARK / source["path"]) != source["sha256"]:
                raise RuntimeError("Source texture changed after preparing A/B plan")
        original = load(entry["baselineMaterial"])
        if original.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_SUBSURFACE:
            raise RuntimeError("Baseline material is no longer the recorded generic subsurface shader")
        profile = profile_for(entry)
        default = alternative(original, entry, "DefaultLit", None)
        candidate = alternative(original, entry, "Profile", profile)
        defaults[original.get_name()] = default
        profiles[original.get_name()] = candidate
        results.append({"baseline": original.get_path_name(), "defaultLit": default.get_path_name(),
                        "profileMaterial": candidate.get_path_name(), "profile": profile.get_path_name(),
                        "unchangedPbrBindings": bindings(original), "settings": entry})
    after = {path: digest(package_file(path)) for path in baseline}
    if after != baseline:
        raise RuntimeError("Baseline material package changed during isolated preparation")
    data.set_editor_property("skin_default_lit", defaults)
    data.set_editor_property("skin_profile", profiles)
    save(data)
    report = {"planSha256": digest(PLAN_PATH), "baselinePackageHashesUnchanged": baseline,
              "alternatives": results, "geometryReimported": False, "rendered": False,
              "artisticAcceptance": False, "defaultSkinMode": "Generic"}
    output = BENCHMARK / "unreal" / "evidence" / "skin-ab-preparation.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("KK_SKIN_AB_READY " + str(output))


if __name__ == "__main__":
    main()
