using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace KragKings.Benchmark
{
    public sealed class DemoContacts : MonoBehaviour
    {
        public Material dustMaterial;
        public AudioClip[] kragSteps,nibSteps;
        ParticleSystem kragDust,nibDust;
        readonly Dictionary<DemoUnit,AudioSource> sources=new();
        readonly Dictionary<DemoUnit,int> previousSample=new();
        readonly System.Random variation=new(2741);
        void Awake()
        {
            kragDust=MakeDust("Heavy sand contact",true);
            nibDust=MakeDust("Light sand contact",false);
        }
        ParticleSystem MakeDust(string name,bool heavy)
        {
            var go=new GameObject(name);go.transform.SetParent(transform,false);
            var particles=go.AddComponent<ParticleSystem>();particles.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);
            var main=particles.main;main.loop=true;main.duration=1;main.playOnAwake=false;
            main.simulationSpace=ParticleSystemSimulationSpace.World;
            main.startLifetime=new ParticleSystem.MinMaxCurve(.25f,heavy?.55f:.35f);
            main.startSize=new ParticleSystem.MinMaxCurve(heavy?.055f:.025f,heavy?.16f:.07f);
            main.startRotation=new ParticleSystem.MinMaxCurve(0,Mathf.PI*2);
            main.maxParticles=heavy?100:45;main.gravityModifier=.04f;
            var emission=particles.emission;emission.enabled=false;
            var shape=particles.shape;shape.enabled=false;
            var size=particles.sizeOverLifetime;size.enabled=true;
            size.size=new ParticleSystem.MinMaxCurve(1,new AnimationCurve(new Keyframe(0,.45f),new Keyframe(.3f,1),new Keyframe(1,1.5f)));
            var color=particles.colorOverLifetime;color.enabled=true;
            var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(heavy?.23f:.12f,.12f),new GradientAlphaKey(0,1)});
            color.color=gradient;
            var renderer=particles.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=dustMaterial;
            renderer.renderMode=ParticleSystemRenderMode.Billboard;renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=true;
            particles.useAutoRandomSeed=false;particles.randomSeed=heavy?137u:257u;
            particles.Play();return particles;
        }
        public void Attach(DemoUnit unit)
        {
            var source=unit.gameObject.AddComponent<AudioSource>();source.playOnAwake=false;
            source.spatialBlend=.75f;source.minDistance=3;source.maxDistance=22;source.rolloffMode=AudioRolloffMode.Linear;
            source.dopplerLevel=0;source.volume=.7f;
            sources.Add(unit,source);previousSample[unit]=-1;
            unit.FootContact+=Contact;
        }
        void Contact(DemoUnit unit,Vector3 point,Vector3 normal)
        {
            bool heavy=unit.species=="Krag";
            var particles=heavy?kragDust:nibDust;
            int count=heavy?(unit.IsWalking?7:11):(unit.IsWalking?2:4);
            for(int i=0;i<count;i++)
            {
                float a=(float)variation.NextDouble()*Mathf.PI*2;
                float strength=(heavy?.12f:.055f)*(float)variation.NextDouble();
                Vector3 tangent=Vector3.ProjectOnPlane(new Vector3(Mathf.Cos(a),0,Mathf.Sin(a)),normal).normalized;
                var emit=new ParticleSystem.EmitParams {
                    position=point+normal*.025f+tangent*.035f,
                    velocity=tangent*strength+normal*(heavy?.11f:.07f),
                    startColor=new Color(.63f,.49f,.31f,1)
                };
                particles.Emit(emit,1);
            }
            AudioClip[] clips=heavy?kragSteps:nibSteps;
            if(clips==null || clips.Length==0)return;
            int index=variation.Next(clips.Length);
            if(index==previousSample[unit])index=(index+1)%clips.Length;
            previousSample[unit]=index;
            var source=sources[unit];source.pitch=.97f+(float)variation.NextDouble()*.06f;
            source.PlayOneShot(clips[index],unit.IsWalking?.8f:1);
        }
        void OnDestroy()
        {
            foreach(var unit in sources.Keys)if(unit)unit.FootContact-=Contact;
        }
    }
}
