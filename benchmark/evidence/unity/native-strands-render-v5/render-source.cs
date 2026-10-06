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
        static int renderedFrames;
        static Color32[] visiblePixels;
        static readonly List<Bounds> regionBounds=new List<Bounds>();
        static readonly List<string> regionNames=new List<string>();
        static readonly List<RendererState> rendererStates=new List<RendererState>();
        static float maxPositionError,maxDiameterError;
        static readonly List<string> errors=new List<string>();
        [Serializable] class Receipt
        {
            public string status,engine,gpu,api,shader,radiusRepresentation,colorRepresentation;
            public int width,height,regions,strands,points;
            public bool simulation,highQualityLines;
            public float maxImportedPositionErrorM,maxImportedDiameterErrorM;
            public int submittedFrames,completedCameraFrames,hiddenColorRange;
            public RegionCoverage[] visibleCoverage;
            public RendererState[] rendererStates;
            public string[] errors;
        }
        [Serializable] class RendererState
        {
            public string stage,region;
            public int callback,unityFrame,completedCameraFrames,renderers,activeRenderers,lineRenderers,validLineRenderers;
            public string[] shaderNames,vertexSetupNames;
            public bool instanceActive;
        }
        [Serializable] class RegionCoverage { public string region; public int changedPixels; }
        public static void Run()
        {
            try
            {
                output=Path.GetFullPath("../fixture-render-v5");
                if(Directory.Exists(output))throw new Exception("Preserve previous render output");
                Directory.CreateDirectory(output);
                Application.logMessageReceived+=OnLog;
                Unity.Collections.NativeLeakDetection.Mode=Unity.Collections.NativeLeakDetectionMode.EnabledWithStackTrace;
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
                    string path="Assets/RenderProbeOutput/V5-"+data.region;
                    AssetDatabase.CreateAsset(provider,path+"-provider.asset");
                    var asset=ScriptableObject.CreateInstance<HairAsset>();asset.settingsBasic.type=HairAsset.Type.Custom;asset.settingsBasic.kLODClusters=false;asset.settingsBasic.memoryLayout=HairAsset.MemoryLayout.Sequential;
                    asset.settingsCustom.dataProvider=provider;asset.settingsCustom.settingsResolve.resampleCurves=false;
                    asset.settingsCustom.settingsResolve.rootUV=HairAsset.SettingsResolve.RootUV.ResolveFromCurves;
                    asset.settingsCustom.settingsResolve.additionalData=true;
                    asset.settingsCustom.settingsResolve.additionalDataMask=HairAsset.SettingsResolve.AdditionalData.PerVertexWidth;
                    AssetDatabase.CreateAsset(asset,path+"-hair.asset");HairAssetBuilder.BuildHairAsset(asset,HairAssetBuilder.BuildFlags.DisableProgress);
                    if(asset.strandGroups==null || asset.strandGroups[0].strandCount!=data.counts.Length)throw new Exception("Curve ingestion failed for "+data.region);
                    var group=asset.strandGroups[0];
                    if(group.particlePosition.Length!=data.radii.Length || group.particleDiameter==null || group.particleDiameter.Length!=data.radii.Length)
                        throw new Exception("Point positions/widths lost during native asset construction");
                    for(int i=0;i<data.radii.Length;i++)
                    {
                        var expected=new Vector3(data.positions[3*i],data.positions[3*i+1],data.positions[3*i+2]);
                        maxPositionError=Mathf.Max(maxPositionError,Vector3.Distance(expected,group.particlePosition[i]));
                        maxDiameterError=Mathf.Max(maxDiameterError,Mathf.Abs(2*data.radii[i]-group.particleDiameter[i]));
                    }
                    if(maxPositionError>1e-7f || maxDiameterError>1e-8f)throw new Exception("Authored curve transfer exceeded fixture tolerance");
                    var material=new Material(shader);
                    material.SetColor("_FurColor",data.region.Contains("Cream")?new Color(.72f,.6f,.43f):data.region.Contains("Pink")?new Color(.52f,.24f,.18f):new Color(.25f,.12f,.055f));
                    HDMaterial.ValidateMaterial(material);AssetDatabase.CreateAsset(material,path+".mat");
                    // The package counts passes pending before CompilePass, then
                    // substitutes its async shader even after synchronous compile.
                    // HDRP caches the material reference, so a later shader swap on
                    // that same instance can leave its vertex-setup compute null.
                    // Prepare the actual live-vertex variant before registration.
                    material.EnableKeyword("HAIR_VERTEX_LIVE");
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
                    Bounds region=new Bounds(new Vector3(data.positions[0],data.positions[1],data.positions[2]),Vector3.zero);
                    for(int i=0;i<data.radii.Length;i++)
                    {
                        var p=new Vector3(data.positions[3*i],data.positions[3*i+1],data.positions[3*i+2]);
                        region.Encapsulate(p);
                        if(!hasBounds){bounds=new Bounds(p,Vector3.zero);hasBounds=true;}else bounds.Encapsulate(p);
                    }
                    regionBounds.Add(region);regionNames.Add(data.region);
                }
                if(hair.Count!=3)throw new Exception("Expected three actual Blender fixture regions");
                camera=new GameObject("Probe Camera").AddComponent<Camera>();camera.nearClipPlane=.001f;camera.farClipPlane=10;camera.fieldOfView=30;
                camera.transform.position=bounds.center+new Vector3(0,bounds.size.y*.2f,-Mathf.Max(.08f,bounds.size.x*1.7f));camera.transform.LookAt(bounds.center);
                var hd=camera.gameObject.AddComponent<HDAdditionalCameraData>();hd.clearColorMode=HDAdditionalCameraData.ClearColorMode.Color;hd.backgroundColorHDR=new Color(.015f,.02f,.025f,1);
                hd.customRenderingSettings=true;hd.renderingPathCustomFrameSettings.SetEnabled(FrameSettingsField.HighQualityLineRendering,true);
                hd.renderingPathCustomFrameSettingsOverrideMask.mask[(uint)FrameSettingsField.HighQualityLineRendering]=true;
                hd.antialiasing=HDAdditionalCameraData.AntialiasingMode.None;
                target=new RenderTexture(1280,720,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);target.Create();camera.targetTexture=target;
                // Shader subshader/pass selection depends on the active pipeline.
                // A prewarm before the first HDRP camera sees only the fallback.
                RenderPipeline.SubmitRenderRequest(camera,new RenderPipeline.StandardRequest{destination=target});
                if(!(RenderPipelineManager.currentPipeline is HDRenderPipeline))throw new Exception("HDRP camera did not initialize its pipeline");
                foreach(var instance in hair)
                {
                    var material=instance.strandGroupDefaults.settingsRendering.materialAsset;
                    int compiled=HairMaterialUtility.TryCompileCountPassesPending(material);
                    if(HairMaterialUtility.AnyPassPendingCompilation(material) || ShaderUtil.ShaderHasError(shader))throw new Exception("Native HDRP material prewarm failed");
                    Debug.Log("KK_NATIVE_HAIR_PREWARM "+instance.name+" compiled="+compiled+" passCount="+material.passCount);
                }
                AssetDatabase.SaveAssets();EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),"Assets/RenderProbeOutput/Fixture.unity");
                began=EditorApplication.timeSinceStartup;frame=0;
                RenderPipelineManager.endCameraRendering+=OnCameraRendered;
                EditorApplication.update+=Step;
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
                // DispatchUpdate does not guard inactive objects. Calling it after
                // OnDisable recreates buffers and re-registers HDRP line renderers.
                foreach(var instance in hair)if(instance.isActiveAndEnabled)instance.DispatchUpdate();
                if(frame==16)
                {
                    RecordRenderers("initial");
                    // Narrow editor compatibility repair: HDRP only refreshes its
                    // vertex setup when the material reference changes. Rebind a
                    // ready material if the package's temporary shader left that
                    // cache invalid. No engine/package source is altered.
                    foreach(var instance in hair)foreach(var lines in instance.GetComponentsInChildren<HDAdditionalMeshRendererSettings>())
                    {
                        if(lines.LineRendererIsValid())continue;
                        var renderer=lines.GetComponent<MeshRenderer>();var material=renderer.sharedMaterial;
                        if(!material || HairMaterialUtility.AnyPassPendingCompilation(material))throw new Exception("Line material still compiling before rebind");
                        renderer.sharedMaterial=null;lines.enableHighQualityLineRendering=true;
                        renderer.sharedMaterial=material;lines.enableHighQualityLineRendering=true;
                        Debug.Log("KK_NATIVE_LINE_REBIND "+instance.name+" valid="+lines.LineRendererIsValid());
                    }
                    RecordRenderers("initialized");
                }
                RenderPipeline.SubmitRenderRequest(camera,new RenderPipeline.StandardRequest{destination=target});
                if(frame<72)return;
                if(!captured)
                {
                    RecordRenderers("visible");
                    visiblePixels=Save("strands.png");captured=true;
                    foreach(var instance in hair)instance.gameObject.SetActive(false);
                    RecordRenderers("disabled");
                    return;
                }
                if(frame<96)return;
                RecordRenderers("hidden");
                var hiddenPixels=Save("without-strands.png");
                int hiddenRange=BackgroundRange(hiddenPixels);
                var coverage=MeasureCoverage(visiblePixels,hiddenPixels);
                var receipt=new Receipt{status="Actual static fixture render only; inspect images before acceptance. Character attachment and performance untested",engine=Application.unityVersion,gpu=SystemInfo.graphicsDeviceName,api=SystemInfo.graphicsDeviceType.ToString(),shader="Physical Hair / native HDRP High Quality Lines",radiusRepresentation="Per-point diameters retained in HairAsset; current official HairVertex shader renders a fitted linear root-to-tip taper",colorRepresentation="Regional constant colors for the fixture; authored per-point character colors not yet transferred",width=target.width,height=target.height,regions=3,strands=12,points=108,simulation=false,highQualityLines=true,maxImportedPositionErrorM=maxPositionError,maxImportedDiameterErrorM=maxDiameterError,submittedFrames=frame-8,completedCameraFrames=renderedFrames,hiddenColorRange=hiddenRange,visibleCoverage=coverage,rendererStates=rendererStates.ToArray(),errors=errors.ToArray()};
                File.WriteAllText(Path.Combine(output,"render.json"),JsonUtility.ToJson(receipt,true));
                if(hiddenRange>2)throw new Exception("Hidden fixture is not an empty uniform background");
                if(coverage.Any(x=>x.changedPixels<100))throw new Exception("A fixture region is missing from the visible capture");
                if(renderedFrames<80)throw new Exception("Insufficient completed camera frames");
                if(errors.Count!=0)throw new Exception("Native renderer logged errors: "+string.Join(" | ",errors));
                Debug.Log("KK_NATIVE_STRAND_RENDER_COMPLETE");Finish(0);
            }
            catch(Exception e){Fail(e);}
        }
        static void OnCameraRendered(ScriptableRenderContext context,Camera renderedCamera)
        {if(renderedCamera==camera)renderedFrames++;}
        static void RecordRenderers(string stage)
        {
            foreach(var instance in hair)
            {
                var renderers=instance.GetComponentsInChildren<MeshRenderer>(true);
                var lines=instance.GetComponentsInChildren<HDAdditionalMeshRendererSettings>(true);
                rendererStates.Add(new RendererState{stage=stage,region=instance.name,callback=frame,unityFrame=Time.frameCount,completedCameraFrames=renderedFrames,renderers=renderers.Length,activeRenderers=renderers.Count(x=>x.enabled && x.gameObject.activeInHierarchy),lineRenderers=lines.Count(x=>x.isActiveAndEnabled && x.enableHighQualityLineRendering),validLineRenderers=lines.Count(x=>x.isActiveAndEnabled && x.LineRendererIsValid()),shaderNames=renderers.Select(x=>x.sharedMaterial && x.sharedMaterial.shader?x.sharedMaterial.shader.name:"missing").ToArray(),vertexSetupNames=lines.Select(x=>{var value=new SerializedObject(x).FindProperty("m_VertexSetupCompute").objectReferenceValue;return value?value.name:"missing";}).ToArray(),instanceActive=instance.isActiveAndEnabled});
            }
        }
        static int BackgroundRange(Color32[] pixels)
        {
            int minR=255,minG=255,minB=255,maxR=0,maxG=0,maxB=0;
            foreach(var p in pixels){minR=Math.Min(minR,p.r);minG=Math.Min(minG,p.g);minB=Math.Min(minB,p.b);maxR=Math.Max(maxR,p.r);maxG=Math.Max(maxG,p.g);maxB=Math.Max(maxB,p.b);}
            return Math.Max(maxR-minR,Math.Max(maxG-minG,maxB-minB));
        }
        static RegionCoverage[] MeasureCoverage(Color32[] visible,Color32[] hidden)
        {
            var result=new List<RegionCoverage>();
            for(int n=0;n<regionBounds.Count;n++)
            {
                var b=regionBounds[n];var lo=new Vector2(float.PositiveInfinity,float.PositiveInfinity);var hi=new Vector2(float.NegativeInfinity,float.NegativeInfinity);
                for(int corner=0;corner<8;corner++)
                {
                    var p=camera.WorldToScreenPoint(new Vector3((corner&1)==0?b.min.x:b.max.x,(corner&2)==0?b.min.y:b.max.y,(corner&4)==0?b.min.z:b.max.z));
                    lo=Vector2.Min(lo,p);hi=Vector2.Max(hi,p);
                }
                int count=0;
                for(int y=Math.Max(0,Mathf.FloorToInt(lo.y)-4);y<Math.Min(target.height,Mathf.CeilToInt(hi.y)+4);y++)
                    for(int x=Math.Max(0,Mathf.FloorToInt(lo.x)-4);x<Math.Min(target.width,Mathf.CeilToInt(hi.x)+4);x++)
                    {int i=y*target.width+x;var a=visible[i];var c=hidden[i];if(Math.Abs(a.r-c.r)+Math.Abs(a.g-c.g)+Math.Abs(a.b-c.b)>12)count++;}
                result.Add(new RegionCoverage{region=regionNames[n],changedPixels=count});
            }
            return result.ToArray();
        }
        static Color32[] Save(string name)
        {
            var old=RenderTexture.active;RenderTexture.active=target;
            var pixels=new Texture2D(target.width,target.height,TextureFormat.RGB24,false,false);
            pixels.ReadPixels(new Rect(0,0,target.width,target.height),0,0);pixels.Apply();
            File.WriteAllBytes(Path.Combine(output,name),pixels.EncodeToPNG());var colors=pixels.GetPixels32();UnityEngine.Object.DestroyImmediate(pixels);RenderTexture.active=old;return colors;
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
            RenderPipelineManager.endCameraRendering-=OnCameraRendered;
            foreach(var instance in hair)if(instance)
            {
                instance.ResetSimulationState();
                HairInstanceBuilder.ClearHairInstance(instance);
                UnityEngine.Object.DestroyImmediate(instance.gameObject);
            }
            hair.Clear();AsyncGPUReadback.WaitAllRequests();
            if(camera)camera.targetTexture=null;
            if(target){target.Release();UnityEngine.Object.DestroyImmediate(target);}
            EditorApplication.Exit(code);
        }
    }
}
