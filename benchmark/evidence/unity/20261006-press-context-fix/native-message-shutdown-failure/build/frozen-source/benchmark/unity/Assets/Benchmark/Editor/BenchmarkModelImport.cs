using System;
using UnityEditor;

namespace KragKings.Editor
{
    // Apply the runtime contract before the first import, not after an expensive
    // generic/default import has already allocated the high-resolution model.
    public sealed class BenchmarkModelImport : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if(!assetPath.StartsWith("Assets/Benchmark/Imported/characters/",StringComparison.Ordinal))return;
            var importer=(ModelImporter)assetImporter;
            importer.animationType=ModelImporterAnimationType.Legacy;
            importer.importAnimation=true;
            importer.importCameras=false;importer.importLights=false;
            importer.isReadable=false;importer.generateSecondaryUV=false;
            importer.importBlendShapes=true;
            importer.optimizeGameObjects=false;importer.optimizeBones=false;
            importer.skinWeights=ModelImporterSkinWeights.Custom;
            importer.maxBonesPerVertex=8;importer.minBoneWeight=.001f;
            importer.importNormals=ModelImporterNormals.Import;
            importer.importTangents=ModelImporterTangents.CalculateMikk;
            // The first full-assembly import exceeded the 8 GiB task limit.
            // Keep all position correctives but omit per-shape normal/tangent
            // buffers for this candidate. Bone-deformed base normals remain.
            // Facial lighting must be reviewed; regional meshes can later
            // restore shape normals without duplicating them over rigid gear.
            importer.importBlendShapeNormals=ModelImporterNormals.None;
            importer.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
        }
    }
}
