using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;
using KragKings.Benchmark;

namespace KragKings.Editor
{
    public static class BenchmarkBuild
    {
        const string AssetRoot="Assets/Benchmark";
        const string Imported=AssetRoot+"/Imported";
        const string Generated=AssetRoot+"/Generated";
        static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"../../.."));
        [Serializable] public class Manifest { public MaterialEntry[] materials;public VariantEntry[] variants;public DemoDeformation.Contract deformation;public DemoUnit.LocomotionSet locomotion;public DemoUnit.WeaponContract weapon; }
        [Serializable] public class MaterialEntry { public string name,baseColor,normal,roughness,metallic; }
        [Serializable] public class VariantEntry { public string name,fbx,label;public DemoDeformation.Contract deformation; }
        [Serializable] class ImportReport {public string engine,species;public ImportedMeshReport[] variants;}
        [Serializable] class ImportedMeshReport {public string name;public int renderers,vertices,triangles,materialSlots,bones,morphTargets,correctiveDrivers;public string[] clips;}

        [MenuItem("Krag Kings/Prepare scene and build Windows")]
        public static void PrepareAndBuild()
        {
            Prepare();
            string output=Path.Combine(Repo,"benchmark/builds/Unity/KragKings-Unity.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions { scenes=new[]{AssetRoot+"/Scenes/Dunes.unity"},locationPathName=output,target=BuildTarget.StandaloneWindows64,options=BuildOptions.None });
            Debug.Log("KRAG_BUILD_RESULT "+report.summary.result+" "+report.summary.totalSize+" bytes");
            if(report.summary.result!=BuildResult.Succeeded) throw new Exception("Windows build failed: "+report.summary.result);
        }

        [MenuItem("Krag Kings/Prepare comparison scene")]
        public static void Prepare()
        {
            AssetDatabase.DesiredWorkerCount=1;
            AssetDatabase.ForceToDesiredWorkerCount();
            Directory.CreateDirectory(Imported);Directory.CreateDirectory(Generated);Directory.CreateDirectory(AssetRoot+"/Scenes");
            CopyTree(Path.Combine(Repo,"benchmark/shared"),Imported);
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            SetProjectSettings();
            var krag=ImportSpecies("krag");var nib=ImportSpecies("nib");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var dunesAsset=AssetDatabase.LoadAssetAtPath<GameObject>(Imported+"/environment/Dunes.fbx");
            if(!dunesAsset) throw new Exception("Shared Dunes.fbx missing");
            var dunes=(GameObject)PrefabUtility.InstantiatePrefab(dunesAsset);dunes.name="Shared dune terrain";
            var sand=MakeSand();
            foreach(var filter in dunes.GetComponentsInChildren<MeshFilter>())
            {
                filter.gameObject.layer=8;
                var collider=filter.gameObject.AddComponent<MeshCollider>();collider.sharedMesh=filter.sharedMesh;
                var renderer=filter.GetComponent<MeshRenderer>();renderer.sharedMaterial=sand;
            }
            Physics.SyncTransforms();
            var director=new GameObject("Demo controller").AddComponent<DemoScene>();
            var contacts=director.gameObject.AddComponent<DemoContacts>();
            var particleShader=AssetDatabase.LoadAssetAtPath<Shader>(AssetRoot+"/Shaders/ParticleLitSoft.shadergraph");
            if(!particleShader)throw new Exception("Lit soft-particle shader missing");
            var dust=AssetDatabase.LoadAssetAtPath<Material>(Generated+"/SandDust.mat");
            if(!dust){dust=new Material(particleShader);AssetDatabase.CreateAsset(dust,Generated+"/SandDust.mat");}
            dust.SetTexture("Texture2D_23DD87FD",Texture(Imported+"/effects/SandDustMask.png",true,false,false));
            dust.SetVector("Vector2_3782A8B8",new Vector4(.025f,.20f,0,0));
            contacts.dustMaterial=dust;EditorUtility.SetDirty(dust);
            contacts.kragSteps=Enumerable.Range(1,6).Select(i=>AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Krag_Sand_"+i.ToString("00")+".wav")).ToArray();
            contacts.nibSteps=Enumerable.Range(1,6).Select(i=>AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Nib_Sand_"+i.ToString("00")+".wav")).ToArray();
            if(contacts.kragSteps.Any(c=>!c)||contacts.nibSteps.Any(c=>!c))throw new Exception("Shared sand contact audio missing");
            var camera=new GameObject("Camera").AddComponent<Camera>();camera.tag="MainCamera";camera.fieldOfView=38;camera.nearClipPlane=.08f;camera.farClipPlane=1800;
            camera.gameObject.AddComponent<AudioListener>();
            var hdCamera=camera.gameObject.AddComponent<HDAdditionalCameraData>();hdCamera.antialiasing=HDAdditionalCameraData.AntialiasingMode.TemporalAntialiasing;hdCamera.allowDynamicResolution=false;
            director.demoCamera=camera;
            director.units=new[]{CreateUnit("Krag",krag,new Vector3(-1.35f,0,0),2.1f,3.2f),CreateUnit("Nib",nib,new Vector3(1.2f,0,.1f),1.45f,3.9f)};
            var indicator=LoadOrCreateMaterial(Generated+"/Indicator.mat","HDRP/Unlit");
            indicator.SetColor("_UnlitColor",new Color(.2f,.8f,.74f));indicator.SetColor("_EmissiveColor",new Color(.15f,.6f,.55f));HDMaterial.ValidateMaterial(indicator);director.indicatorMaterial=indicator;
            MakeLighting();
            EditorSceneManager.SaveScene(scene,AssetRoot+"/Scenes/Dunes.unity");
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(AssetRoot+"/Scenes/Dunes.unity",true)};
            AssetDatabase.SaveAssets();
            Debug.Log("KRAG_SCENE_PREPARED: "+krag.Count+" Krag variants, "+nib.Count+" Nib variants.");
        }
        struct ImportedVariant {public GameObject prefab;public string label;}
        static DemoUnit CreateUnit(string species,List<ImportedVariant> entries,Vector3 position,float height,float speed)
        {
            var go=new GameObject(species);go.transform.position=position;go.transform.rotation=Quaternion.identity;
            var unit=go.AddComponent<DemoUnit>();unit.species=species;unit.bodyHeight=height;
            var manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText(Imported+"/characters/"+species.ToLowerInvariant()+"/manifest.json"));
            unit.locomotion=manifest.locomotion;
            unit.weapon=manifest.weapon;
            if(unit.locomotion?.Walk==null || unit.locomotion.Run==null)throw new Exception(species+": missing authored locomotion contact/speed data");
            foreach(var cycle in new[]{unit.locomotion.Walk,unit.locomotion.Run})
                if(cycle.speedMetersPerSecond<=0||cycle.cycleSeconds<=0||cycle.stanceFraction<=0||cycle.stanceFraction>=1||cycle.leftContacts==null||cycle.leftContacts.Length==0||cycle.rightContacts==null||cycle.rightContacts.Length==0)
                    throw new Exception(species+": incomplete locomotion contact/speed/stance data");
            unit.runSpeed=unit.locomotion.Run.speedMetersPerSecond;unit.walkSpeed=unit.locomotion.Walk.speedMetersPerSecond;
            unit.variants=entries.Select(e=>e.prefab).ToArray();unit.variantLabels=entries.Select(e=>e.label).ToArray();return unit;
        }
        static List<ImportedVariant> ImportSpecies(string species)
        {
            string folder=Imported+"/characters/"+species;
            string manifestPath=folder+"/manifest.json";
            if(!File.Exists(manifestPath)) throw new Exception("Missing character manifest "+manifestPath);
            Manifest manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText(manifestPath));
            if(manifest.materials==null || manifest.variants==null || manifest.variants.Length<2) throw new Exception("Incomplete material/variant manifest "+manifestPath);
            if(manifest.deformation==null || manifest.deformation.schemaVersion!=1 || manifest.deformation.drivers==null || manifest.deformation.drivers.Length==0) throw new Exception("Missing facial/muscle driver contract "+manifestPath);
            if(manifest.weapon==null||string.IsNullOrEmpty(manifest.weapon.muzzleBone)||string.IsNullOrEmpty(manifest.weapon.aimBone)||manifest.weapon.fireTimesNormalized==null||manifest.weapon.fireTimesNormalized.Length==0)
                throw new Exception("Missing animated weapon marker/timing contract "+manifestPath);
            float lastFire=-1;
            foreach(float fire in manifest.weapon.fireTimesNormalized){if(fire<0||fire>=1||fire<=lastFire)throw new Exception("Invalid normalized shot timing "+manifestPath);lastFire=fire;}
            var materials=new Dictionary<string,Material>(StringComparer.OrdinalIgnoreCase);
            foreach(var item in manifest.materials) materials.Add(item.name,MakeCharacterMaterial(folder,item));
            var result=new List<ImportedVariant>();
            var reportEntries=new List<ImportedMeshReport>();
            foreach(var variant in manifest.variants)
            {
                string path=folder+"/"+variant.fbx;
                var importer=AssetImporter.GetAtPath(path) as ModelImporter;
                if(!importer) throw new Exception("Missing FBX "+path);
                importer.animationType=ModelImporterAnimationType.Legacy;
                importer.importAnimation=true;importer.importCameras=false;importer.importLights=false;importer.isReadable=false;
                importer.importBlendShapes=true;
                importer.skinWeights=ModelImporterSkinWeights.Custom;importer.maxBonesPerVertex=8;importer.minBoneWeight=.001f;
                importer.importNormals=ModelImporterNormals.Import;importer.importTangents=ModelImporterTangents.CalculateMikk;
                importer.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
                var clipSettings=importer.defaultClipAnimations;
                foreach(var settings in clipSettings)
                {
                    string canonical=DemoUnit.CanonicalClip(settings.name);
                    if(canonical==null) canonical=DemoUnit.CanonicalClip(settings.takeName);
                    if(canonical!=null) {settings.name=canonical;settings.loopTime=canonical=="Idle"||canonical=="Walk"||canonical=="Run";settings.wrapMode=settings.loopTime?WrapMode.Loop:WrapMode.Once;}
                }
                importer.clipAnimations=clipSettings;
                importer.SaveAndReimport();
                var model=AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var instance=(GameObject)PrefabUtility.InstantiatePrefab(model);instance.name=variant.name;
                foreach(var renderer in instance.GetComponentsInChildren<Renderer>())
                {
                    Material[] slots=renderer.sharedMaterials;
                    for(int i=0;i<slots.Length;i++)
                    {
                        string materialName=slots[i]?slots[i].name:"";
                        if(!materials.TryGetValue(materialName,out var material)) throw new Exception(path+": unknown material slot "+materialName);
                        slots[i]=material;
                    }
                    renderer.sharedMaterials=slots;
                    renderer.shadowCastingMode=ShadowCastingMode.On;renderer.receiveShadows=true;
                    if(renderer is SkinnedMeshRenderer skinned) {skinned.updateWhenOffscreen=true;skinned.quality=SkinQuality.Auto;}
                }
                foreach(var animator in instance.GetComponentsInChildren<Animator>()) UnityEngine.Object.DestroyImmediate(animator);
                var player=instance.GetComponent<Animation>()??instance.AddComponent<Animation>();
                var deformation=instance.GetComponent<DemoDeformation>()??instance.AddComponent<DemoDeformation>();
                deformation.contract=variant.deformation??manifest.deformation;
                var clips=AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__")).ToArray();
                var names=new HashSet<string>();
                foreach(var clip in clips)
                {
                    string canonical=DemoUnit.CanonicalClip(clip.name);if(canonical==null)continue;
                    player.AddClip(clip,canonical);names.Add(canonical);
                    if(canonical=="Idle") player.clip=clip;
                }
                foreach(string clip in new[]{"Idle","Walk","Run","Melee","Shoot","Hit","FacePerformance"}) if(!names.Contains(clip)) throw new Exception(path+": missing animation "+clip+"; imported "+string.Join(",",clips.Select(c=>c.name)));
                var meshes=instance.GetComponentsInChildren<SkinnedMeshRenderer>();
                var boneNames=new HashSet<string>(instance.GetComponentsInChildren<Transform>().Select(t=>t.name));
                if(!boneNames.Contains(manifest.weapon.muzzleBone)||!boneNames.Contains(manifest.weapon.aimBone))throw new Exception(path+": missing exported weapon markers");
                foreach(var driver in deformation.contract.drivers)
                {
                    if(!boneNames.Contains(driver.bone))throw new Exception(path+": missing corrective bone "+driver.bone);
                    bool found=false;
                    foreach(var mesh in meshes)for(int i=0;i<mesh.sharedMesh.blendShapeCount;i++)
                    {
                        string name=mesh.sharedMesh.GetBlendShapeName(i);
                        if(name==driver.morph||name.EndsWith("."+driver.morph,StringComparison.Ordinal))found=true;
                    }
                    if(!found)throw new Exception(path+": missing corrective morph "+driver.morph);
                }
                reportEntries.Add(new ImportedMeshReport{name=variant.name,renderers=meshes.Length,
                    vertices=meshes.Sum(r=>r.sharedMesh.vertexCount),triangles=meshes.Sum(r=>Enumerable.Range(0,r.sharedMesh.subMeshCount).Sum(s=>(int)r.sharedMesh.GetIndexCount(s)/3)),
                    materialSlots=meshes.Sum(r=>r.sharedMaterials.Length),bones=meshes.SelectMany(r=>r.bones).Distinct().Count(),
                    morphTargets=meshes.Sum(r=>r.sharedMesh.blendShapeCount),correctiveDrivers=deformation.contract.drivers.Length,clips=names.OrderBy(n=>n).ToArray()});
                player.playAutomatically=true;
                Directory.CreateDirectory(Generated+"/Prefabs");
                string prefabPath=Generated+"/Prefabs/"+variant.name+".prefab";
                var prefab=PrefabUtility.SaveAsPrefabAsset(instance,prefabPath);
                UnityEngine.Object.DestroyImmediate(instance);
                result.Add(new ImportedVariant{prefab=prefab,label=variant.label});
            }
            string evidence=Path.Combine(Repo,"benchmark/local/evidence/unity");Directory.CreateDirectory(evidence);
            File.WriteAllText(Path.Combine(evidence,species+"-import.json"),JsonUtility.ToJson(new ImportReport{engine=Application.unityVersion,species=species,variants=reportEntries.ToArray()},true));
            return result;
        }
        static Material MakeCharacterMaterial(string folder,MaterialEntry entry)
        {
            string safe=entry.name.Replace('/','_');
            var material=LoadOrCreateMaterial(Generated+"/"+safe+".mat","HDRP/Lit");
            var color=Texture(folder+"/"+entry.baseColor,true,false,false);
            var normal=Texture(folder+"/"+entry.normal,false,true,false);
            var rough=Texture(folder+"/"+entry.roughness,false,false,true);
            var metal=Texture(folder+"/"+entry.metallic,false,false,true);
            int width=rough.width,height=rough.height;
            Color[] r=rough.GetPixels(),m=metal.GetPixels();
            if(m.Length!=r.Length) throw new Exception("Metal/roughness map sizes differ for "+entry.name);
            var packed=new Texture2D(width,height,TextureFormat.RGBA32,false,true);
            var pixels=new Color[r.Length];for(int i=0;i<r.Length;i++)pixels[i]=new Color(m[i].r,1,1,1-r[i].r);
            packed.SetPixels(pixels);packed.Apply();string maskPath=Generated+"/"+safe+"_Mask.png";File.WriteAllBytes(maskPath,packed.EncodeToPNG());UnityEngine.Object.DestroyImmediate(packed);
            AssetDatabase.ImportAsset(maskPath,ImportAssetOptions.ForceSynchronousImport);
            material.SetTexture("_BaseColorMap",color);material.SetColor("_BaseColor",Color.white);material.SetTexture("_NormalMap",normal);material.SetFloat("_NormalScale",1);
            material.SetTexture("_MaskMap",Texture(maskPath,false,false,false));material.SetFloat("_Metallic",1);material.SetFloat("_Smoothness",1);
            material.SetFloat("_SmoothnessRemapMin",0);material.SetFloat("_SmoothnessRemapMax",1);material.SetFloat("_AORemapMin",0);material.SetFloat("_AORemapMax",1);
            if(entry.name.Contains("Skin")||entry.name.Contains("Muzzle")||entry.name.Contains("EarInner"))
            {
                bool krag=entry.name.StartsWith("Krag_");
                material.SetFloat("_MaterialID",0); // HDRP subsurface scattering material.
                material.SetFloat("_SubsurfaceMask",krag?.25f:.6f);
                material.SetFloat("_Thickness",entry.name.Contains("Ear")?.15f:.65f);
                HDMaterial.SetDiffusionProfile(material,SkinProfile(krag));
            }
            material.SetFloat("_DoubleSidedEnable",1);HDMaterial.ValidateMaterial(material);EditorUtility.SetDirty(material);
            return material;
        }
        static DiffusionProfileSettings SkinProfile(bool krag)
        {
            string path=Generated+(krag?"/KragSkinProfile.asset":"/NibSkinProfile.asset");
            var profile=AssetDatabase.LoadAssetAtPath<DiffusionProfileSettings>(path);
            if(!profile)
            {
                profile=ScriptableObject.CreateInstance<DiffusionProfileSettings>();
                AssetDatabase.CreateAsset(profile,path);
                profile.scatteringDistance=krag?new Color(.45f,.25f,.13f):new Color(1.2f,.55f,.29f);
                profile.transmissionTint=new Color(.82f,.43f,.20f);
                profile.worldScale=1;
                EditorUtility.SetDirty(profile);
            }
            return profile;
        }
        static Material MakeSand()
        {
            var material=LoadOrCreateMaterial(Generated+"/Sand.mat","HDRP/Lit");
            material.SetColor("_BaseColor",Color.white);material.SetTexture("_BaseColorMap",Texture(Imported+"/environment/Sand_BaseColor.png",true,false,false));
            material.SetTexture("_NormalMap",Texture(Imported+"/environment/Sand_Normal.png",false,true,false));
            material.SetTexture("_MaskMap",Texture(Imported+"/environment/Sand_MaskHDRP.png",false,false,false));material.SetFloat("_NormalScale",1);
            material.SetFloat("_SmoothnessRemapMin",0);material.SetFloat("_SmoothnessRemapMax",1);HDMaterial.ValidateMaterial(material);EditorUtility.SetDirty(material);return material;
        }
        static Texture2D Texture(string path,bool srgb,bool normal,bool readable)
        {
            var importer=AssetImporter.GetAtPath(path) as TextureImporter;
            if(!importer) throw new Exception("Missing texture "+path);
            bool changed=importer.sRGBTexture!=srgb||importer.isReadable!=readable||importer.textureType!=(normal?TextureImporterType.NormalMap:TextureImporterType.Default)
                ||importer.maxTextureSize!=4096||importer.anisoLevel!=16||!importer.mipmapEnabled||importer.wrapMode!=TextureWrapMode.Repeat||importer.textureCompression!=TextureImporterCompression.CompressedHQ;
            importer.sRGBTexture=srgb;importer.isReadable=readable;importer.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;
            // Preserve hero-map resolution. Source maps remain their authored size;
            // this cap allows 4K detail without forcing every small mask to 4K.
            importer.maxTextureSize=4096;importer.anisoLevel=16;importer.mipmapEnabled=true;importer.wrapMode=TextureWrapMode.Repeat;importer.textureCompression=TextureImporterCompression.CompressedHQ;
            if(changed)importer.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
        static Material LoadOrCreateMaterial(string path,string shader)
        {
            var material=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!material){material=new Material(Shader.Find(shader));AssetDatabase.CreateAsset(material,path);}return material;
        }
        static void MakeLighting()
        {
            var light=new GameObject("Late afternoon sun").AddComponent<Light>();light.type=LightType.Directional;light.transform.rotation=Quaternion.Euler(42,-140,0);light.color=new Color(1,.89f,.73f);light.lightUnit=LightUnit.Lux;light.intensity=55000;light.shadows=LightShadows.Soft;
            var hd=light.gameObject.AddComponent<HDAdditionalLightData>();hd.EnableShadows(true);hd.SetShadowResolution(2048);
            var volume=new GameObject("Desert lighting and grade").AddComponent<Volume>();volume.isGlobal=true;
            var profile=ScriptableObject.CreateInstance<VolumeProfile>();
            var visual=profile.Add<VisualEnvironment>(true);visual.skyType.Override((int)SkyType.PhysicallyBased);
            var sky=profile.Add<PhysicallyBasedSky>(true);sky.groundTint.Override(new Color(.37f,.27f,.15f));sky.exposure.Override(0);
            var exposure=profile.Add<Exposure>(true);exposure.mode.Override(ExposureMode.Fixed);exposure.fixedExposure.Override(12.7f);
            var tone=profile.Add<Tonemapping>(true);tone.mode.Override(TonemappingMode.ACES);
            var ao=profile.Add<ScreenSpaceAmbientOcclusion>(true);ao.intensity.Override(.75f);ao.radius.Override(.45f);
            var gi=profile.Add<GlobalIllumination>(true);gi.enable.Override(true);gi.tracing.Override(RayCastingMode.RayMarching);gi.fullResolutionSS.Override(true);
            var reflections=profile.Add<ScreenSpaceReflection>(true);reflections.enabled.Override(true);reflections.tracing.Override(RayCastingMode.RayMarching);reflections.minSmoothness=.6f;reflections.smoothnessFadeStart=.75f;
            var shadows=profile.Add<ContactShadows>(true);shadows.enable.Override(true);shadows.length.Override(.2f);shadows.maxDistance.Override(40);
            var diffusion=profile.Add<DiffusionProfileList>(true);diffusion.diffusionProfiles.Override(new[]{SkinProfile(true),SkinProfile(false)});
            var fog=profile.Add<Fog>(true);fog.enabled.Override(true);fog.meanFreePath.Override(180);fog.baseHeight.Override(-2);fog.maximumHeight.Override(16);
            string path=Generated+"/DesertVolume.asset";AssetDatabase.CreateAsset(profile,path);foreach(var component in profile.components)AssetDatabase.AddObjectToAsset(component,profile);volume.sharedProfile=profile;
            RenderSettings.sun=light;
            // Static scene capture is generated from this same scene, not concept artwork.
        }
        static void SetProjectSettings()
        {
            PlayerSettings.companyName="Krag Kings";PlayerSettings.productName="Krag Kings — Engine Comparison";PlayerSettings.colorSpace=ColorSpace.Linear;
            PlayerSettings.defaultScreenWidth=1920;PlayerSettings.defaultScreenHeight=1080;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.runInBackground=true;
            PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{GraphicsDeviceType.Direct3D12,GraphicsDeviceType.Direct3D11});
            QualitySettings.SetQualityLevel(0,true);QualitySettings.vSyncCount=0;QualitySettings.skinWeights=SkinWeights.Unlimited;
            var high=AssetDatabase.LoadAssetAtPath<HDRenderPipelineAsset>("Assets/Settings/HDRP High Fidelity.asset");
            if(!high) throw new Exception("HDRP High Fidelity template asset missing");
            var pipelineSettings=new SerializedObject(high);
            pipelineSettings.FindProperty("m_RenderPipelineSettings.supportSSR").boolValue=true;
            pipelineSettings.ApplyModifiedPropertiesWithoutUndo();
            GraphicsSettings.defaultRenderPipeline=high;QualitySettings.renderPipeline=high;
            var tags=new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers=tags.FindProperty("layers");layers.GetArrayElementAtIndex(8).stringValue="Ground";layers.GetArrayElementAtIndex(9).stringValue="Unit";tags.ApplyModifiedPropertiesWithoutUndo();
        }
        static void CopyTree(string source,string destination)
        {
            foreach(var sourcePath in Directory.GetFiles(source,"*",SearchOption.AllDirectories))
            {
                string ext=Path.GetExtension(sourcePath).ToLowerInvariant();if(ext!=".fbx"&&ext!=".png"&&ext!=".json"&&ext!=".wav")continue;
                string relative=Path.GetRelativePath(source,sourcePath);string path=Path.Combine(destination,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
                if(!File.Exists(path)||File.GetLastWriteTimeUtc(sourcePath)>File.GetLastWriteTimeUtc(path)) File.Copy(sourcePath,path,true);
            }
        }
    }
}
