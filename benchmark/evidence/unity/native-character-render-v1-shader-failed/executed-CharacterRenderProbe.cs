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
    // First full-character GPU diagnostic. Rest pose only; no claim about
    // attachment, animation quality, standalone frame time or artistic approval.
    public static class CharacterRenderProbe
    {
        const string Data="Assets/NativeGroom/Character/Strands/";
        const string Assets="Assets/CharacterRenderOutput";
        static Camera camera;static RenderTexture target;static GameObject character;
        static readonly List<HairInstance> hair=new List<HairInstance>();
        static readonly List<string> errors=new List<string>();
        static readonly List<Region> regions=new List<Region>();
        static string output;static int frame,phase,completed;static double start;
        static Color32[] visible;static Matrix4x4 sourceToUnity;
        [Serializable] class Region {public string name;public int curves,points,width,height;public float minDiameterM,maxDiameterM;public bool validNativeRenderer;}
        [Serializable] class Receipt
        {
            public string status,engine,gpu,api,shader,pose,diameterMode,colorMode;
            public int width,height,curves,points,visibleChangedPixels,completedCameraFrames;
            public bool simulation,attachmentVerified,performanceMeasured;
            public float exposureEV;public Region[] regions;public string[] materialNames,errors;
        }
        public static void Run()
        {
            try
            {
                output=Path.GetFullPath("../character-render-v1");
                if(Directory.Exists(output))throw new Exception("Preserve prior character render");
                Directory.CreateDirectory(output);Application.logMessageReceived+=OnLog;
                Unity.Collections.NativeLeakDetection.Mode=Unity.Collections.NativeLeakDetectionMode.EnabledWithStackTrace;
                ShaderUtil.allowAsyncCompilation=false;
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var pipeline=AssetDatabase.LoadAssetAtPath<HDRenderPipelineAsset>("Assets/Settings/HDRP High Fidelity.asset");
                if(!pipeline)throw new Exception("Missing isolated HDRP settings");
                var serialized=new SerializedObject(pipeline);serialized.FindProperty("m_RenderPipelineSettings.supportHighQualityLineRendering").boolValue=true;
                serialized.ApplyModifiedPropertiesWithoutUndo();GraphicsSettings.defaultRenderPipeline=pipeline;QualitySettings.renderPipeline=pipeline;
                QualitySettings.vSyncCount=0;QualitySettings.skinWeights=SkinWeights.Unlimited;
                if(!AssetDatabase.IsValidFolder(Assets))AssetDatabase.CreateFolder("Assets","CharacterRenderOutput");
                var profile=ScriptableObject.CreateInstance<VolumeProfile>();
                var volume=new GameObject("Character diagnostic volume").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;
                var exposure=profile.Add<Exposure>(true);exposure.mode.Override(ExposureMode.Fixed);exposure.fixedExposure.Override(11.5f);
                profile.Add<Tonemapping>(true).mode.Override(TonemappingMode.ACES);
                var lines=profile.Add<HighQualityLineRenderingVolumeComponent>(true);lines.enable.Override(true);lines.tileOpacityThreshold.Override(.995f);
                var diffusion=AssetDatabase.LoadAssetAtPath<DiffusionProfileSettings>("Assets/Benchmark/Generated/NibSkinProfile.asset");
                if(!diffusion)throw new Exception("Missing authored skin profile");
                profile.Add<DiffusionProfileList>(true).diffusionProfiles.Override(new[]{diffusion});
                profile.Add<VisualEnvironment>(true).skyType.Override((int)SkyType.PhysicallyBased);
                profile.Add<PhysicallyBasedSky>(true).groundTint.Override(new Color(.35f,.28f,.2f));
                Light key=Light("Key",Quaternion.Euler(35,145,0),Color.white,30000);
                Light("Fill",Quaternion.Euler(30,-35,0),new Color(.8f,.87f,1),8000);RenderSettings.sun=key;
                var prefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/NativeGroom/Character/Nib_Natural.fbx");
                if(!prefab)throw new Exception("Missing cleaned character");
                character=(GameObject)PrefabUtility.InstantiatePrefab(prefab);character.name="Nib native groom diagnostic";
                var importedSkin=character.GetComponentsInChildren<SkinnedMeshRenderer>();
                if(importedSkin.Length!=1)throw new Exception("Expected exact audited single skinned mesh");
                using(var stream=new BinaryWriter(File.Create(Path.Combine(output,"imported-color-alpha.bin"))))
                    foreach(var color in importedSkin[0].sharedMesh.colors)stream.Write(color.a);
                foreach(var animation in character.GetComponentsInChildren<Animation>())animation.enabled=false;
                foreach(var renderer in character.GetComponentsInChildren<Renderer>())
                {
                    var slots=renderer.sharedMaterials;
                    for(int i=0;i<slots.Length;i++)
                    {
                        string name=slots[i]?slots[i].name:"missing";
                        var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/Benchmark/Generated/"+name+".mat");
                        if(!material || !material.shader || ShaderUtil.ShaderHasError(material.shader))throw new Exception("Missing/invalid authored material "+name);
                        slots[i]=material;
                    }
                    renderer.sharedMaterials=slots;renderer.shadowCastingMode=ShadowCastingMode.On;
                    if(renderer is SkinnedMeshRenderer skin)skin.updateWhenOffscreen=true;
                }
                var shader=AssetDatabase.LoadAssetAtPath<Shader>("Assets/NativeGroom/NativeFurAuthored.shadergraph");
                if(!shader || ShaderUtil.ShaderHasError(shader))throw new Exception("Authored strand shader failed import");
                foreach(string name in new[]{"HeadCream","EarInnerCream_L","EarOuterTawny_L","EarInnerCream_R","EarOuterTawny_R"})
                {
                    var asset=AssetDatabase.LoadAssetAtPath<HairAsset>("Assets/CharacterProbeOutput/"+name+"-hair.asset");
                    var provider=AssetDatabase.LoadAssetAtPath<NativeBinaryCurveProvider>("Assets/CharacterProbeOutput/"+name+"-provider.asset");
                    if(!asset || !provider || asset.strandGroups.Length!=1)throw new Exception("Missing actual curve asset "+name);
                    sourceToUnity=provider.sourceToUnity;var group=asset.strandGroups[0];
                    int count=group.strandCount,points=group.particlePosition.Length,width=points/count;
                    if(width!=9 || points!=provider.expectedPoints || count!=provider.expectedCurves || count>SystemInfo.maxTextureSize)throw new Exception("Unexpected strand texture layout");
                    var colors=NativeBinaryCurveProvider.Floats(AssetDatabase.LoadAssetAtPath<TextAsset>(Data+name+".colorLinearRgb.bytes"));
                    var radii=NativeBinaryCurveProvider.Floats(provider.radii);
                    if(colors.Length!=3*points || radii.Length!=points)throw new Exception("Missing authored RGB/diameter");
                    var tex=new Texture2D(width,count,TextureFormat.RGBAFloat,false,true){name=name+" authored linear RGB diameter",filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp};
                    var rgba=new Color[points];for(int i=0;i<points;i++)rgba[i]=new Color(colors[3*i],colors[3*i+1],colors[3*i+2],2*radii[i]);
                    tex.SetPixels(rgba);tex.Apply(false,false);AssetDatabase.CreateAsset(tex,Assets+"/"+name+"-data.asset");
                    var material=new Material(shader);material.SetTexture("_AuthoredStrandData",tex);HDMaterial.ValidateMaterial(material);material.EnableKeyword("HAIR_VERTEX_LIVE");
                    AssetDatabase.CreateAsset(material,Assets+"/"+name+".mat");
                    var instance=new GameObject(name).AddComponent<HairInstance>();
                    instance.settingsExecutive.updateMode=HairInstance.SettingsExecutive.UpdateMode.ExternalCall;
                    instance.settingsExecutive.updateSimulation=false;instance.settingsExecutive.updateSimulationInEditor=false;
                    instance.settingsVolumetrics.gridResolution=8;instance.settingsVolumetrics.scatteringProbe=false;
                    instance.strandGroupDefaults.settingsRendering.material=true;instance.strandGroupDefaults.settingsRendering.materialAsset=material;
                    instance.strandGroupDefaults.settingsRendering.renderer=HairSim.SettingsRendering.Renderer.HDRPHighQualityLines;
                    instance.strandGroupDefaults.settingsRendering.rendererShadows=ShadowCastingMode.Off;
                    instance.strandGroupDefaults.settingsRendering.allowIndirect=false;
                    instance.strandGroupDefaults.settingsRendering.kLODSelection=HairSim.RenderLODSelection.Manual;
                    instance.strandGroupDefaults.settingsRendering.kLODSelectionValue=1;
                    instance.strandGroupProviders=new[]{new HairInstance.GroupProvider{hairAsset=asset}};
                    HairInstanceBuilder.BuildHairInstance(instance,instance.strandGroupProviders,HideFlags.None);hair.Add(instance);
                    regions.Add(new Region{name=name,curves=count,points=points,width=width,height=count,minDiameterM=2*radii.Min(),maxDiameterM=2*radii.Max()});
                }
                camera=new GameObject("Character probe camera").AddComponent<Camera>();camera.nearClipPlane=.01f;camera.farClipPlane=20;
                camera.orthographic=true;camera.orthographicSize=.34f;SetCamera(false);
                var hd=camera.gameObject.AddComponent<HDAdditionalCameraData>();hd.clearColorMode=HDAdditionalCameraData.ClearColorMode.Color;hd.backgroundColorHDR=new Color(.04f,.045f,.05f);
                hd.customRenderingSettings=true;hd.renderingPathCustomFrameSettings.SetEnabled(FrameSettingsField.HighQualityLineRendering,true);
                hd.renderingPathCustomFrameSettingsOverrideMask.mask[(uint)FrameSettingsField.HighQualityLineRendering]=true;
                hd.antialiasing=HDAdditionalCameraData.AntialiasingMode.None;
                target=new RenderTexture(1400,1100,24,RenderTextureFormat.ARGB32,RenderTextureReadWrite.sRGB);target.Create();camera.targetTexture=target;
                RenderPipeline.SubmitRenderRequest(camera,new RenderPipeline.StandardRequest{destination=target});
                if(!(RenderPipelineManager.currentPipeline is HDRenderPipeline))throw new Exception("HDRP failed to initialize");
                foreach(var instance in hair)
                {
                    var material=instance.strandGroupDefaults.settingsRendering.materialAsset;HairMaterialUtility.TryCompileCountPassesPending(material);
                    if(HairMaterialUtility.AnyPassPendingCompilation(material)||ShaderUtil.ShaderHasError(shader))throw new Exception("Authored hair shader prewarm failed");
                }
                AssetDatabase.SaveAssets();start=EditorApplication.timeSinceStartup;
                RenderPipelineManager.endCameraRendering+=OnRendered;EditorApplication.update+=Step;
            }
            catch(Exception e){Fail(e);}
        }
        static Light Light(string name,Quaternion rotation,Color color,float lux)
        {
            var light=new GameObject(name).AddComponent<Light>();light.type=LightType.Directional;light.color=color;light.transform.rotation=rotation;
            light.shadows=LightShadows.Soft;var hd=light.gameObject.AddComponent<HDAdditionalLightData>();hd.SetIntensity(lux,LightUnit.Lux);hd.EnableShadows(true);return light;
        }
        static void SetCamera(bool side)
        {
            Vector3 focus=sourceToUnity.MultiplyPoint3x4(new Vector3(0,-.005f,1.17f));
            camera.transform.position=sourceToUnity.MultiplyPoint3x4(side?new Vector3(3,-.005f,1.185f):new Vector3(.35f,-3,1.33f));
            camera.transform.rotation=Quaternion.LookRotation(focus-camera.transform.position,sourceToUnity.MultiplyVector(Vector3.forward));
        }
        static void Step()
        {
            try
            {
                if(EditorApplication.timeSinceStartup-start>300)throw new Exception("Character render exceeded 300 seconds");
                EditorApplication.QueuePlayerLoopUpdate();if(frame++<8)return;
                foreach(var h in hair)if(h.isActiveAndEnabled)h.DispatchUpdate();
                RenderPipeline.SubmitRenderRequest(camera,new RenderPipeline.StandardRequest{destination=target});
                if(frame<64)return;
                if(phase==0)
                {
                    for(int i=0;i<hair.Count;i++)
                    {
                        var lines=hair[i].GetComponentsInChildren<HDAdditionalMeshRendererSettings>();
                        regions[i].validNativeRenderer=lines.Length>0 && lines.All(x=>x.isActiveAndEnabled && x.LineRendererIsValid());
                    }
                    if(regions.Any(x=>!x.validNativeRenderer))throw new Exception("Missing native line renderer");
                    visible=Save("Neutral.png");foreach(var h in hair)h.gameObject.SetActive(false);phase=1;frame=8;return;
                }
                if(phase==1)
                {
                    var control=Save("Neutral-without-native-groom.png");int changed=0;
                    for(int i=0;i<control.Length;i++){var a=visible[i];var b=control[i];if(Math.Abs(a.r-b.r)+Math.Abs(a.g-b.g)+Math.Abs(a.b-b.b)>12)changed++;}
                    var receipt=new Receipt{status="Actual rest-pose full character GPU diagnostic; appearance requires review",engine=Application.unityVersion,gpu=SystemInfo.graphicsDeviceName,api=SystemInfo.graphicsDeviceType.ToString(),shader="HDRP Physical Hair with native High Quality Lines",pose="Imported rest pose; authored roots are rest coordinates",diameterMode="Authored per-point diameter texture; no LOD width compensation",colorMode="Authored per-point linear RGB texture",width=target.width,height=target.height,curves=regions.Sum(x=>x.curves),points=regions.Sum(x=>x.points),visibleChangedPixels=changed,completedCameraFrames=completed,simulation=false,attachmentVerified=false,performanceMeasured=false,exposureEV=11.5f,regions=regions.ToArray(),materialNames=character.GetComponentsInChildren<Renderer>().SelectMany(x=>x.sharedMaterials).Select(x=>x.name).Distinct().ToArray(),errors=errors.ToArray()};
                    File.WriteAllText(Path.Combine(output,"render.json"),JsonUtility.ToJson(receipt,true));
                    if(changed<1000)throw new Exception("Full groom lacks visible image contribution");
                    foreach(var h in hair)h.gameObject.SetActive(true);SetCamera(true);phase=2;frame=0;return;
                }
                Save("Profile.png");if(errors.Count>0)throw new Exception("Native render errors: "+string.Join(" | ",errors));
                Debug.Log("KK_NATIVE_CHARACTER_RENDER_COMPLETE");Finish(0);
            }
            catch(Exception e){Fail(e);}
        }
        static void OnRendered(ScriptableRenderContext c,Camera cam){if(cam==camera)completed++;}
        static Color32[] Save(string name)
        {
            var old=RenderTexture.active;RenderTexture.active=target;var t=new Texture2D(target.width,target.height,TextureFormat.RGB24,false,false);
            t.ReadPixels(new Rect(0,0,target.width,target.height),0,0);t.Apply();File.WriteAllBytes(Path.Combine(output,name),t.EncodeToPNG());
            var result=t.GetPixels32();UnityEngine.Object.DestroyImmediate(t);RenderTexture.active=old;return result;
        }
        static void OnLog(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)errors.Add(message);}
        static void Fail(Exception e){if(output!=null&&Directory.Exists(output))File.WriteAllText(Path.Combine(output,"failure.txt"),e+"\n"+string.Join("\n",errors));Debug.LogException(e);Finish(1);}
        static void Finish(int code)
        {
            EditorApplication.update-=Step;RenderPipelineManager.endCameraRendering-=OnRendered;Application.logMessageReceived-=OnLog;
            foreach(var h in hair)if(h){h.ResetSimulationState();HairInstanceBuilder.ClearHairInstance(h);UnityEngine.Object.DestroyImmediate(h.gameObject);}hair.Clear();
            AsyncGPUReadback.WaitAllRequests();if(camera)camera.targetTexture=null;if(target){target.Release();UnityEngine.Object.DestroyImmediate(target);}EditorApplication.Exit(code);
        }
    }
}
