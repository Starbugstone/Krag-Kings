using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace KragKings.Benchmark
{
    // This directs the real playable actors and camera. It does not alter time,
    // render offline frames, or substitute cinematic models for game assets.
    public sealed class DemoShowcase : MonoBehaviour
    {
        DemoScene scene;
        string evidence;
        bool playing;
        float started;
        Vector3[] origins;
        DemoAudioRecorder audioRecorder;
        public void Begin(DemoScene controller,string path,bool wait)
        {scene=controller;evidence=path;StartCoroutine(Show(wait));}
        IEnumerator Until(float seconds)
        {while(Time.unscaledTime-started<seconds)yield return null;}
        void Variant(DemoUnit unit,int index)
        {unit.SetVariant(index%unit.variants.Length);scene.Select(unit);}
        IEnumerator Show(bool wait)
        {
            scene.AutomatedView=true;
            origins=new[]{scene.units[0].transform.position,scene.units[1].transform.position};
            foreach(var unit in scene.units)unit.SetVariant(0);
            scene.ResetCamera();
            yield return new WaitForSecondsRealtime(15);
            File.WriteAllText(Path.Combine(evidence,"showcase-ready.json"),JsonUtility.ToJson(new CaptureState{state="ready",durationSeconds=72,width=Screen.width,height=Screen.height,utc=DateTime.UtcNow.ToString("o")},true));
            Debug.Log("UNITY_SHOWCASE_READY");
            if(wait)while(!File.Exists(Path.Combine(evidence,"showcase-start.flag")))yield return null;
            audioRecorder=scene.demoCamera.GetComponent<DemoAudioRecorder>();
            if(audioRecorder)audioRecorder.BeginRecording(75);
            started=Time.unscaledTime;playing=true;
            File.WriteAllText(Path.Combine(evidence,"showcase-started.json"),JsonUtility.ToJson(new CaptureState{state="started",durationSeconds=72,width=Screen.width,height=Screen.height,utc=DateTime.UtcNow.ToString("o")},true));
            Debug.Log("UNITY_SHOWCASE_STARTED");
            var krag=scene.units[0];var nib=scene.units[1];
            yield return Until(6);
            krag.MoveTo(origins[0]+new Vector3(-.7f,0,4),true);
            nib.MoveTo(origins[1]+new Vector3(.9f,0,4));
            yield return Until(10);nib.MoveTo(origins[1]);
            yield return Until(14);scene.Select(krag);krag.Trigger("Melee");nib.Trigger("Shoot");
            yield return Until(16);Variant(krag,1);Variant(nib,1);krag.Trigger("Melee");nib.Trigger("Shoot");
            yield return Until(18);krag.Trigger("Hit");nib.Trigger("Hit");
            yield return Until(20);Variant(krag,2);Variant(nib,2);krag.MoveTo(origins[0]);nib.MoveTo(origins[1]);
            yield return Until(24);Variant(krag,3);krag.Trigger("Shoot");nib.Trigger("Melee");
            yield return Until(28);Variant(nib,0);nib.TriggerFace();
            yield return Until(36.5f);nib.Trigger("Shoot");
            yield return Until(38);Variant(krag,0);krag.TriggerFace();
            yield return Until(45.5f);krag.Trigger("Melee");
            yield return Until(47);krag.Trigger("Shoot");
            for(int cycle=0;cycle<4;cycle++)
            {
                yield return Until(48+cycle*4);
                Variant(krag,1+cycle%Mathf.Max(1,krag.variants.Length-1));
                Variant(nib,1+cycle%Mathf.Max(1,nib.variants.Length-1));
                float side=cycle%2==0?1:-1;
                krag.MoveTo(origins[0]+new Vector3(-.7f,0,side*2),cycle%2==0);
                nib.MoveTo(origins[1]+new Vector3(.7f,0,side*2));
            }
            yield return Until(62);Variant(krag,0);Variant(nib,0);
            krag.MoveTo(origins[0]-Vector3.forward);nib.MoveTo(origins[1]-Vector3.forward);
            yield return Until(65);krag.MoveTo(origins[0]);nib.MoveTo(origins[1]);
            yield return Until(68);scene.Select(krag);krag.Trigger("Melee");nib.Trigger("Shoot");
            yield return Until(72);
            playing=false;scene.AutomatedView=false;scene.ResetCamera();
            if(audioRecorder)audioRecorder.EndRecording(Path.Combine(evidence,"showcase-engine-audio.wav"));
            File.WriteAllText(Path.Combine(evidence,"showcase-complete.json"),JsonUtility.ToJson(new CaptureState{state="complete",durationSeconds=72,width=Screen.width,height=Screen.height,utc=DateTime.UtcNow.ToString("o")},true));
            Debug.Log("UNITY_SHOWCASE_COMPLETE");
        }
        void Update()
        {
            if(!playing)return;
            float t=Time.unscaledTime-started;
            if(t>=28&&t<48){scene.PortraitCamera();return;}
            Vector3 focus=(scene.units[0].transform.position+scene.units[1].transform.position)*.5f+Vector3.up*.95f;
            float yaw=165+Mathf.Sin(t*.15f)*30;
            float distance=8.5f+Mathf.Sin(t*.21f)*.6f;
            if(t>=62){float settle=Mathf.Clamp01((t-62)/7);yaw=Mathf.Lerp(yaw,165,settle);distance=Mathf.Lerp(distance,8.5f,settle);}
            scene.SetView(focus,yaw,22,distance);
        }
        [Serializable] class CaptureState {public string state,utc;public int durationSeconds,width,height;}
    }
}
