using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.HighDefinition;
using Unity.DemoTeam.Hair;
using Unity.DemoTeam.DigitalHuman;

namespace KragKings.StrandPilot
{
    public static class CompatibilityProbe
    {
        [Serializable] class Receipt
        {
            public string status,unityVersion,hairAssembly,skinAssembly,hdrpAssembly;
            public int groups,strands,pointsPerStrand;
            public bool supportsNativeLines;
        }
        public static void Run()
        {
            // A small genuine asset build exercises Burst/Collections and the
            // package builder. It does not establish rendering or skinning.
            if(!AssetDatabase.IsValidFolder("Assets/ProbeOutput"))AssetDatabase.CreateFolder("Assets","ProbeOutput");
            const string path="Assets/ProbeOutput/CompatibilityHair.asset";
            if(AssetDatabase.LoadAssetAtPath<HairAsset>(path))throw new Exception("Preserve the previous probe before running again");
            var asset=ScriptableObject.CreateInstance<HairAsset>();
            asset.settingsBasic.type=HairAsset.Type.Procedural;
            asset.settingsBasic.kLODClusters=false;
            asset.settingsProcedural.strandCount=128;
            asset.settingsProcedural.strandParticleCount=8;
            asset.settingsProcedural.strandLength=.035f;
            asset.settingsProcedural.strandDiameter=.08f;
            AssetDatabase.CreateAsset(asset,path);
            HairAssetBuilder.BuildHairAsset(asset,HairAssetBuilder.BuildFlags.DisableProgress);
            if(asset.strandGroups==null || asset.strandGroups.Length!=1 || asset.strandGroups[0].strandCount!=128)
                throw new Exception("Tiny hair asset build failed");
            EditorUtility.SetDirty(asset);AssetDatabase.SaveAssets();
            var result=new Receipt {
                status="Actual package compilation and 128-strand asset build; rendering, animation and performance not tested",
                unityVersion=Application.unityVersion,
                hairAssembly=typeof(HairInstance).Assembly.FullName,
                skinAssembly=typeof(SkinAttachmentTarget).Assembly.FullName,
                hdrpAssembly=typeof(HDAdditionalMeshRendererSettings).Assembly.FullName,
                groups=asset.strandGroups.Length,strands=asset.strandGroups[0].strandCount,
                pointsPerStrand=asset.strandGroups[0].strandParticleCount,
                supportsNativeLines=Enum.IsDefined(typeof(HairSim.SettingsRendering.Renderer),"HDRPHighQualityLines")
            };
            File.WriteAllText(Path.GetFullPath("../compatibility.json"),JsonUtility.ToJson(result,true));
            Debug.Log("KK_STRAND_COMPATIBILITY_COMPLETE");
        }
    }
}
