using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Unity.DemoTeam.Hair;

namespace KragKings.StrandPilot
{
    public sealed class NativeCharacterImport : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if(assetPath!="Assets/NativeGroom/Character/Nib_Natural.fbx")return;
            var m=(ModelImporter)assetImporter;
            m.animationType=ModelImporterAnimationType.Legacy;m.importAnimation=true;
            m.importCameras=false;m.importLights=false;m.isReadable=true;m.generateSecondaryUV=false;
            m.importBlendShapes=true;m.optimizeGameObjects=false;m.optimizeBones=false;
            m.skinWeights=ModelImporterSkinWeights.Custom;m.maxBonesPerVertex=8;m.minBoneWeight=.001f;
            m.importNormals=ModelImporterNormals.Import;m.importTangents=ModelImporterTangents.CalculateMikk;
            m.importBlendShapeNormals=ModelImporterNormals.None;m.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
        }
    }
    public static class CharacterImportProbe
    {
        [Serializable] public class Anchor { public string name; public float[] source; }
        [Serializable] public class InputFile { public string path,sha256; }
        [Serializable] public class Region { public string name,prefix; public int curves,points; }
        [Serializable] public class Config { public string fbx,sourceSha256; public Anchor[] anchors; public InputFile[] files; public Region[] regions; public string[] bones; public int expectedTriangles; }
        [Serializable] public class AnchorResult { public string name; public Vector3 source,imported; public float errorMeters; }
        [Serializable] public class RegionResult { public string name; public int curves,points; public float maxPointErrorMeters,maxDiameterErrorMeters; }
        [Serializable] public class MeshInspection { public string name; public bool active,enabled; public int vertices,triangles,submeshes; public Matrix4x4 localToWorld; }
        [Serializable] public class TopologyInspection { public int expectedTriangles,activeTriangles,allTriangles; public Matrix4x4 sourceToUnity; public AnchorResult[] anchors; public MeshInspection[] meshes; }
        [Serializable] public class TopologyAttribution
        {
            public string sourceSha256,importPositionsSha256,importIndicesSha256;
            public bool matchedNondegenerateTriangleMultiset;
            public int sourceTriangles,importedTriangles,removedTriangleMultiplicity,addedTriangleMultiplicity,removedNonzeroAreaCandidateCount;
        }
        [Serializable] public class Receipt
        {
            public string status,engine,sourceSha256;
            public Matrix4x4 sourceToUnity;
            public float maxAnchorErrorMeters,determinant;
            public AnchorResult[] anchors;public RegionResult[] regions;
            public int canonicalBones,triangles,vertices,morphs,colorAlphaZero,colorAlphaOne,colorAlphaOther;
            public string[] clips;
            public int independentlyVerifiedZeroAreaTrianglesRemoved;
            public string topologyAttributionSha256;
            public bool bindingMaskVerified=false,rootAttachmentVerified=false,rendered=false;
        }
        static Vector3 Position(Anchor a)=>new Vector3(a.source[0],a.source[1],a.source[2]);
        static string Hash(string path)
        {using(var stream=File.OpenRead(path))using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();}
        static Matrix4x4 Basis(Vector3 a,Vector3 b,Vector3 c,Vector3 d)
        {
            var m=Matrix4x4.identity;m.SetColumn(0,(Vector4)(b-a));m.SetColumn(1,(Vector4)(c-a));m.SetColumn(2,(Vector4)(d-a));m.SetColumn(3,new Vector4(a.x,a.y,a.z,1));return m;
        }
        public static void Run()
        {
            string output=Path.GetFullPath("../character-import-v3");GameObject character=null;
            try
            {
                if(Directory.Exists(output))throw new Exception("Preserve prior character import evidence");Directory.CreateDirectory(output);
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var config=JsonUtility.FromJson<Config>(File.ReadAllText("Assets/NativeGroom/Character/config.json"));
                foreach(var file in config.files)
                {
                    using(var stream=File.OpenRead(file.path))using(var sha=SHA256.Create())
                        if(BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant()!=file.sha256)throw new Exception("Staged source drift: "+file.path);
                }
                var model=AssetDatabase.LoadAssetAtPath<GameObject>(config.fbx);if(!model)throw new Exception("Cleaned Natural FBX import missing");
                character=(GameObject)PrefabUtility.InstantiatePrefab(model);
                var all=character.GetComponentsInChildren<Transform>(true).GroupBy(x=>x.name).ToDictionary(x=>x.Key,x=>x.ToArray());
                foreach(string bone in config.bones)if(!all.ContainsKey(bone)||all[bone].Length!=1)throw new Exception("Missing/ambiguous imported bone "+bone);
                var source=config.anchors.ToDictionary(x=>x.name,Position);
                // Four non-coplanar anatomical anchors establish the full affine
                // mapping; all thirteen anchors independently check it afterward.
                string[] fit={"Root","Head","Hand_L","WeaponAim"};
                var a=Basis(source[fit[0]],source[fit[1]],source[fit[2]],source[fit[3]]);
                var b=Basis(all[fit[0]][0].position,all[fit[1]][0].position,all[fit[2]][0].position,all[fit[3]][0].position);
                if(Mathf.Abs(a.determinant)<1e-6f)throw new Exception("Degenerate anatomical fit");
                var transform=b*a.inverse;var checks=new List<AnchorResult>();
                foreach(var anchor in config.anchors)
                {
                    var p=Position(anchor);var q=all[anchor.name][0].position;
                    checks.Add(new AnchorResult{name=anchor.name,source=p,imported=q,errorMeters=Vector3.Distance(transform.MultiplyPoint3x4(p),q)});
                }
                float error=checks.Max(x=>x.errorMeters);
                if(error>1e-5f || Mathf.Abs(Mathf.Abs(transform.determinant)-1)>1e-4f)throw new Exception("Character axes/scale mismatch, max anchor error="+error+", det="+transform.determinant);
                for(int i=0;i<3;i++)for(int j=0;j<3;j++)if(Mathf.Abs(Vector3.Dot(transform.GetColumn(i),transform.GetColumn(j))-(i==j?1:0))>1e-4f)throw new Exception("Character transform contains non-rigid shear/scale");
                var meshes=character.GetComponentsInChildren<SkinnedMeshRenderer>();
                int triangles=meshes.Sum(x=>x.sharedMesh.triangles.Length/3);
                var allMeshes=character.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                var topology=new TopologyInspection{expectedTriangles=config.expectedTriangles,activeTriangles=triangles,allTriangles=allMeshes.Sum(x=>x.sharedMesh.triangles.Length/3),sourceToUnity=transform,anchors=checks.ToArray(),meshes=allMeshes.Select(x=>new MeshInspection{name=x.name,active=x.gameObject.activeInHierarchy,enabled=x.enabled,vertices=x.sharedMesh.vertexCount,triangles=x.sharedMesh.triangles.Length/3,submeshes=x.sharedMesh.subMeshCount,localToWorld=x.localToWorldMatrix}).ToArray()};
                File.WriteAllText(Path.Combine(output,"topology.json"),JsonUtility.ToJson(topology,true));
                // Preserve actual imported topology for independent source matching
                // if Unity removes/splits anything during FBX ingestion.
                for(int n=0;n<allMeshes.Length;n++)
                {
                    var renderer=allMeshes[n];var mesh=renderer.sharedMesh;
                    using(var stream=new BinaryWriter(File.OpenWrite(Path.Combine(output,"mesh-"+n+"-source-positions.bin"))))foreach(var local in mesh.vertices)
                    {var p=transform.inverse.MultiplyPoint3x4(renderer.localToWorldMatrix.MultiplyPoint3x4(local));stream.Write(p.x);stream.Write(p.y);stream.Write(p.z);}
                    using(var stream=new BinaryWriter(File.OpenWrite(Path.Combine(output,"mesh-"+n+"-indices.bin"))))foreach(int i in mesh.triangles)stream.Write(i);
                }
                int removedZeroArea=0;string proofHash=null;
                if(triangles!=config.expectedTriangles)
                {
                    string proofPath="Assets/NativeGroom/Character/topology-attribution.json";
                    var proof=JsonUtility.FromJson<TopologyAttribution>(File.ReadAllText(proofPath));
                    // The allowance is tied to independently audited exact source
                    // and imported buffers, never only a lower triangle count.
                    if(allMeshes.Length!=1 || !proof.matchedNondegenerateTriangleMultiset || proof.sourceSha256!=Hash(config.fbx) ||
                        proof.sourceTriangles!=config.expectedTriangles || proof.importedTriangles!=triangles ||
                        proof.addedTriangleMultiplicity!=0 || proof.removedNonzeroAreaCandidateCount!=0 ||
                        proof.removedTriangleMultiplicity!=config.expectedTriangles-triangles ||
                        proof.importPositionsSha256!=Hash(Path.Combine(output,"mesh-0-source-positions.bin")) ||
                        proof.importIndicesSha256!=Hash(Path.Combine(output,"mesh-0-indices.bin")))
                        throw new Exception("Imported topology differs from the independently verified zero-area-only removal");
                    removedZeroArea=proof.removedTriangleMultiplicity;proofHash=Hash(proofPath);
                }
                var clipNames=AssetDatabase.LoadAllAssetsAtPath(config.fbx).OfType<AnimationClip>().Where(x=>!x.name.StartsWith("__preview__")).Select(x=>x.name).ToArray();
                foreach(string expected in new[]{"Idle","Walk","Run","Melee","Shoot","Hit","FacePerformance"})
                    if(clipNames.Count(x=>x.Equals(expected,StringComparison.OrdinalIgnoreCase)||x.EndsWith("|"+expected,StringComparison.OrdinalIgnoreCase)||x.EndsWith("_"+expected,StringComparison.OrdinalIgnoreCase))!=1)throw new Exception("Missing/ambiguous embedded clip "+expected);
                var colors=meshes.SelectMany(x=>x.sharedMesh.colors).ToArray();
                string folder="Assets/CharacterProbeOutput";if(!AssetDatabase.IsValidFolder(folder))AssetDatabase.CreateFolder("Assets","CharacterProbeOutput");
                var regionResults=new List<RegionResult>();
                foreach(var region in config.regions)
                {
                    var provider=ScriptableObject.CreateInstance<NativeBinaryCurveProvider>();provider.expectedCurves=region.curves;provider.expectedPoints=region.points;provider.sourceToUnity=transform;
                    provider.positions=AssetDatabase.LoadAssetAtPath<TextAsset>(region.prefix+".positions.bytes");provider.radii=AssetDatabase.LoadAssetAtPath<TextAsset>(region.prefix+".radii.bytes");provider.counts=AssetDatabase.LoadAssetAtPath<TextAsset>(region.prefix+".curveCounts.bytes");provider.rootUV=AssetDatabase.LoadAssetAtPath<TextAsset>(region.prefix+".rootUv.bytes");
                    AssetDatabase.CreateAsset(provider,folder+"/"+region.name+"-provider.asset");
                    var asset=ScriptableObject.CreateInstance<HairAsset>();asset.settingsBasic.type=HairAsset.Type.Custom;asset.settingsBasic.kLODClusters=false;asset.settingsBasic.memoryLayout=HairAsset.MemoryLayout.Sequential;
                    asset.settingsCustom.dataProvider=provider;asset.settingsCustom.settingsResolve.resampleCurves=false;asset.settingsCustom.settingsResolve.rootUV=HairAsset.SettingsResolve.RootUV.ResolveFromCurves;asset.settingsCustom.settingsResolve.additionalData=true;asset.settingsCustom.settingsResolve.additionalDataMask=HairAsset.SettingsResolve.AdditionalData.PerVertexWidth;
                    AssetDatabase.CreateAsset(asset,folder+"/"+region.name+"-hair.asset");HairAssetBuilder.BuildHairAsset(asset,HairAssetBuilder.BuildFlags.DisableProgress);
                    if(asset.strandGroups==null||asset.strandGroups.Length!=1)throw new Exception("Unexpected groom group partition");
                    var group=asset.strandGroups[0];var points=NativeBinaryCurveProvider.Floats(provider.positions);var radii=NativeBinaryCurveProvider.Floats(provider.radii);
                    if(group.strandCount!=region.curves||group.particlePosition.Length!=region.points||group.particleDiameter==null||group.particleDiameter.Length!=region.points)throw new Exception("Native groom build lost authored points/diameters");
                    var result=new RegionResult{name=region.name,curves=region.curves,points=region.points};
                    for(int i=0;i<region.points;i++)
                    {
                        var expected=transform.MultiplyPoint3x4(new Vector3(points[3*i],points[3*i+1],points[3*i+2]));
                        result.maxPointErrorMeters=Mathf.Max(result.maxPointErrorMeters,Vector3.Distance(expected,group.particlePosition[i]));
                        result.maxDiameterErrorMeters=Mathf.Max(result.maxDiameterErrorMeters,Mathf.Abs(2*radii[i]-group.particleDiameter[i]));
                    }
                    if(result.maxPointErrorMeters>1e-7f||result.maxDiameterErrorMeters>1e-8f)throw new Exception("Native authored stream transfer failed");regionResults.Add(result);
                }
                var receipt=new Receipt{status="Actual cleaned character import and coordinate/curve-asset transfer only; rendering and deforming attachment unverified",engine=Application.unityVersion,sourceSha256=config.sourceSha256,sourceToUnity=transform,maxAnchorErrorMeters=error,determinant=transform.determinant,anchors=checks.ToArray(),regions=regionResults.ToArray(),canonicalBones=config.bones.Length,triangles=triangles,vertices=meshes.Sum(x=>x.sharedMesh.vertexCount),morphs=meshes.Sum(x=>x.sharedMesh.blendShapeCount),colorAlphaZero=colors.Count(x=>x.a==0),colorAlphaOne=colors.Count(x=>x.a==1),colorAlphaOther=colors.Count(x=>x.a!=0&&x.a!=1),clips=clipNames};
                receipt.independentlyVerifiedZeroAreaTrianglesRemoved=removedZeroArea;receipt.topologyAttributionSha256=proofHash;
                File.WriteAllText(Path.Combine(output,"import.json"),JsonUtility.ToJson(receipt,true));AssetDatabase.SaveAssets();
                UnityEngine.Object.DestroyImmediate(character);Debug.Log("KK_NATIVE_CHARACTER_IMPORT_COMPLETE");EditorApplication.Exit(0);
            }
            catch(Exception e){if(Directory.Exists(output))File.WriteAllText(Path.Combine(output,"failure.txt"),e.ToString());if(character)UnityEngine.Object.DestroyImmediate(character);Debug.LogException(e);EditorApplication.Exit(1);}
        }
    }
}
