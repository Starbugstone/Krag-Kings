using System.Collections;
using UnityEngine;

namespace KragKings.Benchmark
{
    public sealed class DemoCombatAudio : MonoBehaviour
    {
        public AudioClip kragShot,nibShot,kragHit,nibHit;
        readonly AudioSource[] voices=new AudioSource[8];
        int nextVoice;
        void Awake()
        {
            for(int i=0;i<voices.Length;i++)
            {
                var go=new GameObject("Action audio "+i);go.transform.SetParent(transform,false);
                var source=go.AddComponent<AudioSource>();source.playOnAwake=false;
                source.spatialBlend=1;source.minDistance=4;source.maxDistance=60;
                source.rolloffMode=AudioRolloffMode.Linear;source.dopplerLevel=0;
                voices[i]=source;
            }
        }
        public void Shot(DemoUnit unit)=>Play(unit.species=="Krag"?kragShot:nibShot,unit.ShotOrigin,.55f);
        public void Action(DemoUnit unit,string action)
        {
            if(action=="Hit")StartCoroutine(Hit(unit));
        }
        IEnumerator Hit(DemoUnit unit)
        {
            int version=unit.ActionVersion;
            yield return new WaitForSeconds(unit.ActionDuration("Hit")*.22f);
            if(unit.ActionVersion==version)
                Play(unit.species=="Krag"?kragHit:nibHit,unit.transform.position+Vector3.up*unit.bodyHeight*.6f,.6f);
        }
        void Play(AudioClip clip,Vector3 position,float gain)
        {
            if(!clip)return;
            var source=voices[nextVoice++%voices.Length];source.Stop();
            source.transform.position=position;source.pitch=1;source.volume=gain;source.clip=clip;source.Play();
        }
    }
}
