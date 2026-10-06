using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
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
        [Serializable] public class MaterialEntry
        {
            public string name,baseColor,normal,roughness,metallic;
            public string alphaMode,alphaSource,doubleSidedNormalMode,normalConvention;
            public float alphaClipThreshold;
            public bool doubleSided;
            public bool hasCoatParameters;
            public float coatWeight,coatRoughness,coatIor;
        }
        [Serializable] public class VariantEntry { public string name,fbx,label;public DemoDeformation.Contract deformation; }
        [Serializable] class ImportReport {public string engine,species;public ImportedMeshReport[] variants;}
        [Serializable] class ImportedMeshReport {public string name,fbxSha256;public int renderers,vertices,triangles,materialSlots,bones,morphTargets,correctiveDrivers;public string[] clips;public ClipReport[] clipDetails;}
        [Serializable] class ClipReport
        {
            public string name;public float seconds;
            public int varyingTransformCurves,varyingFaceCurves,varyingTorsoCurves,varyingEarCurves;
            public string[] varyingBoneNames;
        }

        [MenuItem("Krag Kings/Prepare scene and build Windows")]
        public static void PrepareAndBuild()
        {
            Prepare();
            BuildWindows();
        }

        // Reuse the already validated scene/imports for runtime-code and material
        // fixes. Refuse stale shared content; changed FBXs require PrepareAndBuild.
        [MenuItem("Krag Kings/Rebuild prepared Windows demo")]
        public static void BuildPrepared()
        {
            string scenePath=AssetRoot+"/Scenes/Dunes.unity";
            if(!File.Exists(scenePath))throw new Exception("Prepare the comparison scene first");
            EditorSceneManager.OpenScene(scenePath,OpenSceneMode.Single);
            var director=UnityEngine.Object.FindAnyObjectByType<DemoScene>();
            if(!director||director.contentFingerprint!=ContentFingerprint(Path.Combine(Repo,"benchmark/shared")))
                throw new Exception("Shared content changed since scene preparation; run PrepareAndBuild");
            SetProjectSettings();
            foreach(string path in Directory.GetFiles(Generated,"*.mat"))
            {
                var material=AssetDatabase.LoadAssetAtPath<Material>(path.Replace('\\','/'));
                if(material&&IsSkin(material.name))ApplySkinProfile(material,material.name);
            }
            if(RenderSettings.sun)
            {
                var sun=RenderSettings.sun.GetComponent<HDAdditionalLightData>();
                if(sun)sun.angularDiameter=1.5f;
                RenderSettings.sun.color=Color.white;
            }
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),scenePath);
            AssetDatabase.SaveAssets();
            BuildWindows();
        }
        static void BuildWindows()
        {
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
            if(ContentFingerprint(Imported)!=ContentFingerprint(Path.Combine(Repo,"benchmark/shared")))
                throw new Exception("Imported file snapshot differs from shared content; inspect stale or changed files before building");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            SetProjectSettings();
            var krag=ImportSpecies("krag");var nib=ImportSpecies("nib");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var dunesAsset=AssetDatabase.LoadAssetAtPath<GameObject>(Imported+"/environment/Dunes.fbx");
            if(!dunesAsset) throw new Exception("Shared Dunes.fbx missing");
            var dunes=(GameObject)PrefabUtility.InstantiatePrefab(dunesAsset);dunes.name="Shared dune terrain";
            // Measured FBX import maps source (x,y,z) to Unity (-x,z,-y).
            // Our common scene uses Unity (x,z,y), Unreal (100x,-100y,100z).
            // Correct only the terrain adapter; preserve the shared source mesh.
            dunes.transform.rotation=Quaternion.AngleAxis(180,Vector3.up)*dunes.transform.rotation;
            var sand=MakeSand();
            foreach(var filter in dunes.GetComponentsInChildren<MeshFilter>())
            {
                filter.gameObject.layer=8;
                var collider=filter.gameObject.AddComponent<MeshCollider>();collider.sharedMesh=filter.sharedMesh;
                var renderer=filter.GetComponent<MeshRenderer>();renderer.sharedMaterial=sand;
            }
            Physics.SyncTransforms();
            var terrainSamples=DemoTerrainReference.Sample();
            foreach(var sample in terrainSamples)Debug.Log("KRAG_TERRAIN_REFERENCE "+JsonUtility.ToJson(sample));
            if(terrainSamples.Any(s=>!s.passed))throw new Exception("Imported dune coordinate/collision mismatch; inspect all KRAG_TERRAIN_REFERENCE samples");
            var director=new GameObject("Demo controller").AddComponent<DemoScene>();
            director.contentFingerprint=ContentFingerprint(Imported);
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
            var combat=director.gameObject.AddComponent<DemoCombatAudio>();
            combat.kragShot=AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Krag_Shot.wav");
            combat.nibShot=AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Nib_Shot.wav");
            combat.kragHit=AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Krag_Hit.wav");
            combat.nibHit=AssetDatabase.LoadAssetAtPath<AudioClip>(Imported+"/audio/Nib_Hit.wav");
            if(!combat.kragShot||!combat.nibShot||!combat.kragHit||!combat.nibHit)throw new Exception("Shared action audio missing");
            var camera=new GameObject("Camera").AddComponent<Camera>();camera.tag="MainCamera";camera.fieldOfView=38;camera.nearClipPlane=.08f;camera.farClipPlane=1800;
            camera.gameObject.AddComponent<DemoAudioRecorder>();camera.gameObject.AddComponent<AudioListener>();
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
                string previousSettings=EditorJsonUtility.ToJson(importer);
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
                if(EditorJsonUtility.ToJson(importer)!=previousSettings)importer.SaveAndReimport();
                else Debug.Log("KRAG_IMPORT_SETTINGS_CACHED "+path);
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
                var clipDetails=new List<ClipReport>();
                foreach(var clip in clips)
                {
                    string canonical=DemoUnit.CanonicalClip(clip.name);if(canonical==null)continue;
                    if(!names.Add(canonical))throw new Exception(path+": ambiguous duplicate canonical take "+canonical);
                    var detail=new ClipReport{name=canonical,seconds=clip.length};
                    var varyingBones=new HashSet<string>(StringComparer.Ordinal);
                    foreach(var binding in AnimationUtility.GetCurveBindings(clip))
                    {
                        if(binding.type!=typeof(Transform))continue;
                        var curve=AnimationUtility.GetEditorCurve(clip,binding);
                        if(curve==null||curve.length<2)continue;
                        var keys=curve.keys;
                        if(keys.Max(k=>k.value)-keys.Min(k=>k.value)<.000001f)continue;
                        detail.varyingTransformCurves++;
                        if(binding.path.Contains("/FaceRoot"))detail.varyingFaceCurves++;
                        string bone=binding.path.Substring(binding.path.LastIndexOf('/')+1);
                        varyingBones.Add(bone);
                        if(bone=="Pelvis"||bone=="Spine"||bone=="Chest")detail.varyingTorsoCurves++;
                        if(bone.StartsWith("Ear",StringComparison.Ordinal))detail.varyingEarCurves++;
                    }
                    // Curve retention is evidence for the actual imported clip,
                    // not a substitute for inspecting whole-body motion in game.
                    detail.varyingBoneNames=varyingBones.OrderBy(n=>n,StringComparer.Ordinal).ToArray();
                    if(detail.varyingTransformCurves==0||detail.varyingFaceCurves==0)throw new Exception(path+": "+canonical+" lost animated body/facial transform curves");
                    clipDetails.Add(detail);player.AddClip(clip,canonical);
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
                reportEntries.Add(new ImportedMeshReport{name=variant.name,fbxSha256=HashFile(path),renderers=meshes.Length,
                    vertices=meshes.Sum(r=>r.sharedMesh.vertexCount),triangles=meshes.Sum(r=>Enumerable.Range(0,r.sharedMesh.subMeshCount).Sum(s=>(int)r.sharedMesh.GetIndexCount(s)/3)),
                    materialSlots=meshes.Sum(r=>r.sharedMaterials.Length),bones=meshes.SelectMany(r=>r.bones).Distinct().Count(),
                    morphTargets=meshes.Sum(r=>r.sharedMesh.blendShapeCount),correctiveDrivers=deformation.contract.drivers.Length,clips=names.OrderBy(n=>n).ToArray(),clipDetails=clipDetails.ToArray()});
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
            bool masked=entry.alphaMode=="MASK";
            if(!string.IsNullOrEmpty(entry.alphaMode) && !masked && entry.alphaMode!="OPAQUE")
                throw new Exception(entry.name+": unsupported alphaMode "+entry.alphaMode);
            if(!string.IsNullOrEmpty(entry.normalConvention) && entry.normalConvention!="OpenGL +Y")
                throw new Exception(entry.name+": expected shared OpenGL +Y tangent normals");
            if(masked && (entry.alphaSource!="baseColor.a" || entry.alphaClipThreshold<=0 || entry.alphaClipThreshold>=1 || entry.doubleSidedNormalMode!="Flip"))
                throw new Exception(entry.name+": incomplete masked-card alpha/normal contract");
            string safe=entry.name.Replace('/','_');
            var material=LoadOrCreateMaterial(Generated+"/"+safe+".mat","HDRP/Lit");
            var color=Texture(folder+"/"+entry.baseColor,true,false,false);
            if(masked)
            {
                string colorPath=folder+"/"+entry.baseColor;
                var importer=(TextureImporter)AssetImporter.GetAtPath(colorPath);
                if(!importer.DoesSourceTextureHaveAlpha())throw new Exception(entry.name+": card base color has no source alpha");
                bool changed=importer.alphaSource!=TextureImporterAlphaSource.FromInput || !importer.alphaIsTransparency
                    || !importer.mipMapsPreserveCoverage || !Mathf.Approximately(importer.alphaTestReferenceValue,entry.alphaClipThreshold);
                importer.alphaSource=TextureImporterAlphaSource.FromInput;importer.alphaIsTransparency=true;
                importer.mipMapsPreserveCoverage=true;importer.alphaTestReferenceValue=entry.alphaClipThreshold;
                if(changed)importer.SaveAndReimport();
                color=AssetDatabase.LoadAssetAtPath<Texture2D>(colorPath);
            }
            var normal=Texture(folder+"/"+entry.normal,false,true,false);
            var rough=Texture(folder+"/"+entry.roughness,false,false,true);
            var metal=Texture(folder+"/"+entry.metallic,false,false,true);
            int width=rough.width,height=rough.height;
            Color[] r=rough.GetPixels(),m=metal.GetPixels();
            var metallic=new LinearScalarMap(m.Select(c=>c.r).ToArray(),metal.width,metal.height);
            var packed=new Texture2D(width,height,TextureFormat.RGBA32,false,true);
            var pixels=new Color[r.Length];for(int i=0;i<r.Length;i++)pixels[i]=new Color(metallic.AtOutputTexel(i%width,i/width,width,height),1,1,1-r[i].r);
            Debug.Log("KRAG_MASK_PACK "+entry.name+" roughness="+width+"x"+height+" metallic="+metal.width+"x"+metal.height+" output="+width+"x"+height+" scalarLinear=true constantMetallic="+metallic.IsConstant);
            packed.SetPixels(pixels);packed.Apply();string maskPath=Generated+"/"+safe+"_Mask.png";File.WriteAllBytes(maskPath,packed.EncodeToPNG());UnityEngine.Object.DestroyImmediate(packed);
            AssetDatabase.ImportAsset(maskPath,ImportAssetOptions.ForceSynchronousImport);
            material.SetTexture("_BaseColorMap",color);material.SetColor("_BaseColor",Color.white);material.SetTexture("_NormalMap",normal);material.SetFloat("_NormalScale",1);
            material.SetTexture("_MaskMap",Texture(maskPath,false,false,false));material.SetFloat("_Metallic",1);material.SetFloat("_Smoothness",1);
            material.SetFloat("_SmoothnessRemapMin",0);material.SetFloat("_SmoothnessRemapMax",1);material.SetFloat("_AORemapMin",0);material.SetFloat("_AORemapMax",1);
            if(IsSkin(entry.name))ApplySkinProfile(material,entry.name);
            material.SetFloat("_SurfaceType",0); // Masked PBR remains in the opaque depth-writing path.
            material.SetFloat("_AlphaCutoffEnable",masked?1:0);
            if(masked)
            {
                material.SetFloat("_AlphaCutoff",entry.alphaClipThreshold);
                material.SetFloat("_AlphaCutoffShadow",entry.alphaClipThreshold);
                material.SetFloat("_DoubleSidedEnable",entry.doubleSided?1:0);
                material.SetFloat("_DoubleSidedNormalMode",0); // Pinned HDRP Lit: Flip=0.
            }
            else material.SetFloat("_DoubleSidedEnable",1); // Preserve the existing opaque baseline.
            ApplyCoat(material,entry);
            HDMaterial.ValidateMaterial(material);EditorUtility.SetDirty(material);
            return material;
        }
        static void ApplyCoat(Material material,MaterialEntry entry)
        {
            // HDRP 17.4 Lit exposes coat weight, but fixes the top-layer IOR at
            // 1.5 and physical roughness at .01 (perceptual roughness .1).
            // Preserve the authored values in the manifest and report this
            // approximation rather than silently dropping the ocular coat.
            if(!material.HasProperty("_CoatMask"))throw new Exception(entry.name+": shader has no coat mask");
            if(entry.hasCoatParameters &&
                (!(entry.coatWeight>=0 && entry.coatWeight<=1) ||
                 !(entry.coatRoughness>=0 && entry.coatRoughness<=1) ||
                 !(entry.coatIor>=1 && entry.coatIor<=4)))
                throw new Exception(entry.name+": invalid authored coat parameters");
            material.SetTexture("_CoatMaskMap",null);
            material.SetFloat("_CoatMask",entry.hasCoatParameters?entry.coatWeight:0);
            if(entry.hasCoatParameters)
                Debug.Log("KRAG_COAT_MAPPING "+entry.name+" weight="+entry.coatWeight+
                    " sourcePerceptualRoughness="+entry.coatRoughness+" sourceIOR="+entry.coatIor+
                    " shader=HDRP/Lit runtimePerceptualRoughness=0.1 runtimeIOR=1.5 visualAcceptancePending=true");
        }
        static bool IsSkin(string name)=>name.Contains("Skin")||name.Contains("Muzzle")||name.Contains("EarInner")||name=="Nib_v5_DustyPinkEar";
        static void ApplySkinProfile(Material material,string name)
        {
            bool krag=name.StartsWith("Krag_");
            material.SetFloat("_MaterialID",0);
            material.SetFloat("_SubsurfaceMask",krag?.25f:.6f);
            material.SetFloat("_Thickness",name.Contains("Ear")?.15f:.65f);
            HDMaterial.SetDiffusionProfile(material,SkinProfile(krag));
            HDMaterial.ValidateMaterial(material);EditorUtility.SetDirty(material);
        }
        static string ContentFingerprint(string directory)=>HashText(string.Join("\n",Directory.GetFiles(directory,"*",SearchOption.AllDirectories)
            .Where(p=>new[]{".png",".fbx",".json",".wav"}.Contains(Path.GetExtension(p).ToLowerInvariant()))
            .OrderBy(p=>p,StringComparer.Ordinal).Select(p=>Path.GetRelativePath(directory,p).Replace('\\','/')+":"+HashFile(p))));
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
            // HDRP's asset menu performs this step after CreateAsset because the
            // shader hash is derived from the persistent GUID. CreateInstance's
            // earlier OnEnable sees no asset path and leaves hash zero.
            var serialized=new SerializedObject(profile);
            if(serialized.FindProperty("profile.hash").uintValue==0)
            {
                var hashTable=typeof(DiffusionProfileSettings).Assembly.GetType("UnityEditor.Rendering.HighDefinition.DiffusionProfileHashTable");
                var update=hashTable?.GetMethod("UpdateDiffusionProfileHashNow",System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static);
                if(update==null)throw new Exception("Pinned HDRP diffusion-profile hash initializer is unavailable");
                update.Invoke(null,new object[]{profile});
                serialized.Update();
                if(serialized.FindProperty("profile.hash").uintValue==0)throw new Exception("Diffusion profile has no persistent shader hash: "+path);
            }
            // OnEnable can compute a hash while an existing asset is loading,
            // before Unity retains its dirty state. Persist even that path.
            EditorUtility.SetDirty(profile);
            AssetDatabase.SaveAssetIfDirty(profile);
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
            var light=new GameObject("Late afternoon sun").AddComponent<Light>();light.type=LightType.Directional;light.transform.rotation=Quaternion.Euler(42,-140,0);light.color=Color.white;light.lightUnit=LightUnit.Lux;light.intensity=55000;light.shadows=LightShadows.Soft;
            var hd=light.gameObject.AddComponent<HDAdditionalLightData>();hd.EnableShadows(true);hd.SetShadowResolution(2048);hd.angularDiameter=1.5f;
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
            PlayerSettings.defaultScreenWidth=1920;PlayerSettings.defaultScreenHeight=1080;PlayerSettings.fullScreenMode=FullScreenMode.FullScreenWindow;PlayerSettings.runInBackground=true;
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
            var files=Directory.GetFiles(source,"*",SearchOption.AllDirectories);
            foreach(var sourcePath in files.Where(p=>!p.EndsWith(".fbx",StringComparison.OrdinalIgnoreCase)))
            {
                string ext=Path.GetExtension(sourcePath).ToLowerInvariant();if(ext!=".fbx"&&ext!=".png"&&ext!=".json"&&ext!=".wav")continue;
                string relative=Path.GetRelativePath(source,sourcePath);string path=Path.Combine(destination,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));
                CopyIfChanged(sourcePath,path);
            }
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            // Process high-resolution FBXs separately, releasing temporary model
            // allocations between imports instead of retaining the entire batch.
            foreach(var sourcePath in files.Where(p=>p.EndsWith(".fbx",StringComparison.OrdinalIgnoreCase)).OrderBy(p=>new FileInfo(p).Length))
            {
                string relative=Path.GetRelativePath(source,sourcePath);string path=Path.Combine(destination,relative).Replace('\\','/');Directory.CreateDirectory(Path.GetDirectoryName(path));
                bool changed=CopyIfChanged(sourcePath,path);
                if(changed || !AssetImporter.GetAtPath(path))AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
                EditorUtility.UnloadUnusedAssetsImmediate();GC.Collect();GC.WaitForPendingFinalizers();
                Debug.Log((changed?"KRAG_MODEL_IMPORTED ":"KRAG_MODEL_SOURCE_UNCHANGED ")+relative);
            }
        }
        static bool CopyIfChanged(string source,string destination)
        {
            // Restored candidates can be older than the local import. Content,
            // not modification time, defines the cross-engine comparison.
            if(!File.Exists(destination)||new FileInfo(source).Length!=new FileInfo(destination).Length||HashFile(source)!=HashFile(destination))
            {File.Copy(source,destination,true);return true;}
            return false;
        }
        static string HashFile(string path){using var hash=SHA256.Create();using var input=File.OpenRead(path);return BitConverter.ToString(hash.ComputeHash(input)).Replace("-","").ToLowerInvariant();}
        static string HashText(string value){using var hash=SHA256.Create();return BitConverter.ToString(hash.ComputeHash(System.Text.Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
    }
}
