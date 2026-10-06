using System;
using System.Collections.Generic;
using UnityEngine;

namespace KragKings.Benchmark
{
    // Animation and the unit's terrain IK evaluate first; corrective skin follows
    // the final pose. No Blender-only driver is assumed to survive the FBX export.
    [DefaultExecutionOrder(100)]
    public sealed class DemoDeformation : MonoBehaviour
    {
        [Serializable] public class Contract
        {
            public int schemaVersion;
            public string faceRoot;
            public Driver[] drivers;
        }
        [Serializable] public class Driver
        {
            public string morph,bone,channel,kind;
            public float start,end,maxWeight=1;
        }
        public Contract contract;
        sealed class Binding
        {
            public Driver driver;
            public Transform bone;
            public Quaternion restRotation;
            public Vector3 restPosition;
            public readonly List<(SkinnedMeshRenderer renderer,int index)> targets=new();
        }
        readonly List<Binding> bindings=new();

        public float MaximumAppliedWeight(string kind)
        {
            float maximum=0;
            foreach(var binding in bindings)
                if(binding.driver.kind==kind)
                    foreach(var target in binding.targets)
                        maximum=Mathf.Max(maximum,target.renderer.GetBlendShapeWeight(target.index));
            return maximum;
        }

        void Awake()
        {
            if(contract==null || contract.schemaVersion!=1 || contract.drivers==null)
                throw new InvalidOperationException(name+": missing portable deformation contract");
            var bones=new Dictionary<string,Transform>(StringComparer.Ordinal);
            foreach(var bone in GetComponentsInChildren<Transform>())
                if(!bones.ContainsKey(bone.name))bones.Add(bone.name,bone);
            var renderers=GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach(var driver in contract.drivers)
            {
                if(!bones.TryGetValue(driver.bone,out var bone))throw new InvalidOperationException(name+": missing driver bone "+driver.bone);
                if(driver.channel!="rotationMagnitudeDegrees"&&driver.channel!="translationDistanceMeters")throw new InvalidOperationException(name+": unsupported driver channel "+driver.channel);
                if(driver.end<=driver.start)throw new InvalidOperationException(name+": invalid driver range for "+driver.morph);
                var binding=new Binding{driver=driver,bone=bone,restRotation=bone.localRotation,restPosition=bone.localPosition};
                foreach(var renderer in renderers)
                {
                    var mesh=renderer.sharedMesh;
                    for(int index=0;index<mesh.blendShapeCount;index++)
                    {
                        string morph=mesh.GetBlendShapeName(index);
                        // Unity's FBX importer may prefix the source mesh name.
                        if(morph==driver.morph || morph.EndsWith("."+driver.morph,StringComparison.Ordinal))
                            binding.targets.Add((renderer,index));
                    }
                }
                if(binding.targets.Count==0)throw new InvalidOperationException(name+": missing exported morph "+driver.morph);
                bindings.Add(binding);
            }
        }
        void LateUpdate()
        {
            foreach(var binding in bindings)
            {
                var driver=binding.driver;
                float value;
                if(driver.channel=="rotationMagnitudeDegrees")
                    value=Quaternion.Angle(binding.restRotation,binding.bone.localRotation);
                else
                {
                    // Imported local bone positions can retain an FBX scale parent.
                    // Convert the delta through that parent's transform to meters.
                    Vector3 localDelta=binding.bone.localPosition-binding.restPosition;
                    value=binding.bone.parent ? binding.bone.parent.TransformVector(localDelta).magnitude : localDelta.magnitude;
                }
                float weight=Mathf.Clamp01((value-driver.start)/(driver.end-driver.start))*Mathf.Clamp01(driver.maxWeight)*100;
                foreach(var target in binding.targets)target.renderer.SetBlendShapeWeight(target.index,weight);
            }
        }
    }
}
