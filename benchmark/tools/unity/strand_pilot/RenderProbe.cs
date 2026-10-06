using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using Unity.DemoTeam.Hair;

namespace KragKings.StrandPilot
{
    public static class RenderProbe
    {
        static Camera camera;
        static RenderTexture target;
        static List<HairInstance> hair=new List<HairInstance>();
        static int frame;
        static double began;
        static string output;
        static bool captured;
        static readonly List<string> errors=new List<string>();
        [Serializable] class Receipt
        {
            public string status,engine,gpu,api,shader;
            public int width,height,regions,strands,points;
            public bool simulation,highQualityLines;
            public string[] errors;
        }
        public static void Run()
        {
            try
            {
                output=Path.GetFullPath("../fixture-render-v1");
                if(Directory.Exists(output))throw new Exception("Preserve previous render output");
                Directory.CreateDirectory(output);
                Application.logMessageReceived+=OnLog;
                ShaderUtil.allowAsyncCompilation=false;
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var pipeline=AssetDatabase.LoadAssetAtPath<HDRenderPipelineAsset>("Assets/Settings/HDRP High Fidelity.asset");
                if(!pipeline)throw new Exception("Missing isolated HDRP settings");
                var serialized=new SerializedObject(pipeline);
                serialized.FindProperty("m_RenderPipelineSettings.supportHighQualityLineRendering").boolValue=true;
                serialized.ApplyModifiedPropertiesWithoutUndo();
                GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;
                QualitySettings.vSyncCount=0;
                var volume=new GameObject("Probe Volume").AddComponent<Volume>();volume.isGlobal=true;
                var profile=ScriptableObject.CreateInstance<VolumeProfile>();volume.sharedProfile=profile;
                var exposure=profile.Add<Exposure>(true);exposure.mode.Override(ExposureMode.Fixed);exposure.fixedExposure.Override(9);
                var lines=profile.Add<HighQualityLineRenderingVolumeComponent>(true);lines.enable.Override(true);lines.tileOpacityThreshold.Override(.995f);
                var tone=profile.Add<Tonemapping>(true);tone.mode.Override(TonemappingMode.ACES);
                var sun=new GameObject("Probe Key").AddComponent<Light>();sun.type=LightType.Directional;sun.color=Color.white;
                sun.transform.rotation=Quaternion.Euler(35,-35,0);sun.gameObject.AddComponent<HDAdditionalLightData>().SetIntensity(30000,LightUnit.Lux);
                var fill=new GameObject("Probe Fill").AddComponent<Light>();fill.type=LightType.Directional;fill.color=new Color(.8f,.87f,1);
                fill.transform.rotation=Quaternion.Euler(25,145,0);fill.gameObject.AddComponent<HDAdditionalLightData>().SetIntensity(8000,LightUnit.Lux);
                var shader=AssetDatabase.LoadAssetAtPath<Shader>("Assets/NativeGroom/NativeFurPhysical.shadergraph");
                if(!shader || ShaderUtil.ShaderHasError(shader))throw new Exception("Native physical hair shader did not import cleanly");
                if(!AssetDatabase.IsValidFolder("Assets/RenderProbeOutput"))AssetDatabase.CreateFolder("Assets","RenderProbeOutput");
                Bounds bounds=new Bounds();bool hasBounds=false;
                foreach(string dataPath in Directory.GetFiles("Assets/NativeGroom/Fixture","*.json").OrderBy(x=>x))
                {
                    if(Path.GetFileName(dataPath)=="conversion.json")continue;
                    var provider=ScriptableObject.CreateInstance<NativeCurveProvider>();provider.curveData=AssetDatabase.LoadAssetAtPath<TextAsset>(dataPath.Replace('\\','/'));
                    var data=provider.Read();
                    string path="Assets/RenderProbeOutput/"+data.region;
                    AssetDatabase.CreateAsset(provider,path+"-provider.asset");
                    var asset=ScriptableObject.CreateInstance<HairAsset>();asset.settingsBasic.type=HairAsset.Type.Custom;asset.settingsBasic.kLODClusters=false;
                    asset.settingsCustom.dataProvider=provider;asset.settingsCustom.settingsResolve.resampleCurves=false;
                    asset.settingsCustom.settingsResolve.rootUV=HairAsset.SettingsResolve.RootUV.ResolveFromCurves;
                    asset.settingsCustom.settingsResolve.additionalData=true;
                    asset.settingsCustom.settingsResolve.additionalDataMask=HairAsset.SettingsResolve.AdditionalData.PerVertexWidth;
                    AssetDatabase.CreateAsset(asset,path+"-hair.asset");HairAssetBuilder.BuildHairAsset(asset,HairAssetBuilder.BuildFlags.DisableProgress);
                    if(asset.strandGroups==null || asset.strandGroups[0].strandCount!=data.counts.Length)throw new Exception("Curve ingestion failed for "+data.region);
                    var material=new Material(shader);
                    material.SetColor("_FurColor",data.region.Contains("Cream")?new Color(.72f,.6f,.43f):data.region.Contains("Pink")?new Color(.52f,.24f,.18f):new Color(.25f,.12f,.055f));
                    HDMaterial.ValidateMaterial(material);AssetDatabase.CreateAsset(material,path+".mat");
                    var instance=new GameObject(data.region).AddComponent<HairInstance>();
                    instance.settingsExecutive.updateMode=HairInstance.SettingsExecutive.UpdateMode.ExternalCall;
                    instance.settingsExecutive.updateSimulation=false;instance.settingsExecutive.updateSimulationInEditor=false;
                    instance.settingsVolumetrics.gridResolution=8;instance.settingsVolumetrics.scatteringProbe=false;
                    instance.strandGroupDefaults.settingsRendering.material=true;instance.strandGroupDefaults.settingsRendering.materialAsset=material;
                    instance.strandGroupDefaults.settingsRendering.renderer=HairSim.SettingsRendering.Renderer.HDRPHighQualityLines;
                    instance.strandGroupDefaults.settingsRendering.rendererShadows=ShadowCastingMode.Off;
                    instance.strandGroupDefaults.settingsRendering.allowIndirect=false;
                    instance.strandGroupProviders=new[]{new HairInstance.GroupProvider{hairAsset=asset}};
                    HairInstanceBuilder.BuildHairInstance(instance,instance.strandGroupProviders,HideFlags.None);
                    hair.Add(instance);
                    for(int i=0;i<data.radii.Length;i++)
                    {
                        var p=new Vector3(data.positions[3*i],data.positions[3*i+1],data.positions[3*i+2]);
                        if(!hasBounds){bounds=new Bounds(p,Vector3.zero);hasBounds=true;}else bounds.Encapsulate(p);
                    }
                }
                if(hair.Count!=3)throw new Exception("Expected three actual Blender fixture regions");
                camera=new GameObject("Probe Camera").AddComponent<Camera>();camera.nearClipPlane=.001f;camera.farClipPlane=10;camera.fieldOfView=30;
                camera.transform.position=bounds.center+new Vector3(0,bounds.size.y*.2f,-Mathf.Max(.08f,bounds.size.x*1.7f));camera.transform.LookAt(bounds.center);
                var hd=camera.gameObject.AddComponent<HDAdditionalCameraData>();hd.clearColorMode=HDAdditionalCameraData.ClearColorMode.Color;hd.backgroundColorHDR=new Color(.015f,.02f,.025f,1);
                hd.customRenderingSettings=true;hd.renderingPathCustomFrameSettings.SetEnabled(FrameSettingsField.HighQualityLineRendering,true);
                hd.renderingPathCustomFrameSettingsOverrideMask.mask[(uint)FrameSettingsField.HighQualityLineRendering]=true;
                hd.antialiasing=HDAdditionalCameraData.AntialiasingMode.None;
                target=new RenderTexture(1280,720,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);target.Create();camera.targetTexture=target;
                AssetDatabase.SaveAssets();EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),"Assets/RenderProbeOutput/Fixture.unity");
                began=EditorApplication.timeSinceStartup;frame=0;EditorApplication.update+=Step;
            }
            catch(Exception e){Fail(e);}
        }
        static void Step()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-began>240)throw new Exception("Native fur probe exceeded240seconds");
                EditorApplication.QueuePlayerLoopUpdate();
                // Let ExecuteAlways setup run before dispatching the explicit
                // GPU update. Camera rendering remains the actual HDRP path.
                if(frame++<8)return;
                foreach(var instance in hair)if(instance.enabled)instance.DispatchUpdate();
                RenderPipeline.SubmitRenderRequest(camera,new RenderPipeline.StandardRequest{destination=target});
                if(frame<32)return;
                if(!captured)
                {
                    Save("strands.png");captured=true;
                    foreach(var instance in hair)instance.gameObject.SetActive(false);
                    return;
                }
                if(frame<36)return;
                Save("without-strands.png");
                var receipt=new Receipt{status="Actual static fixture render only; inspect images before acceptance. Character attachment and performance untested",engine=Application.unityVersion,gpu=SystemInfo.graphicsDeviceName,api=SystemInfo.graphicsDeviceType.ToString(),shader="Physical Hair / native HDRP High Quality Lines",width=target.width,height=target.height,regions=3,strands=12,points=108,simulation=false,highQualityLines=true,errors=errors.ToArray()};
                File.WriteAllText(Path.Combine(output,"render.json"),JsonUtility.ToJson(receipt,true));
                if(errors.Count!=0)throw new Exception("Native renderer logged errors: "+string.Join(" | ",errors));
                Debug.Log("KK_NATIVE_STRAND_RENDER_COMPLETE");Finish(0);
            }
            catch(Exception e){Fail(e);}
        }
        static void Save(string name)
        {
            var old=RenderTexture.active;RenderTexture.active=target;
            var pixels=new Texture2D(target.width,target.height,TextureFormat.RGB24,false,false);
            pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();
            File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());UnityEngine.Object.DestroyImmediate(pixels);RenderTexture.active=old;
        }
        static void OnLog(string message,string stack,LogType type)
        {if(type==LogType.Error || type==LogType.Exception || type==LogType.Assert)errors.Add(message);}
        static void Fail(Exception e)
        {
            if(output!=null && Directory.Exists(output))File.WriteAllText(Path.Combine(output,"failure.txt"),e.ToString()+"\n"+string.Join("\n",errors));
            Debug.LogException(e);Finish(1);
        }
        static void Finish(int code)
        {
            EditorApplication.update-=Step;Application.logMessageReceived-=OnLog;
            if(target){target.Release();UnityEngine.Object.DestroyImmediate(target);}
            EditorApplication.Exit(code);
        }
    }
}
