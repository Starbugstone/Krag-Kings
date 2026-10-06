using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using KragKings.Benchmark;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

namespace KragKings.Editor
{
    // A bounded check through the real installed Input System with temporary
    // devices. It neither injects Windows input nor drives a scene/character.
    public static class DemoPressContextCheck
    {
        [Serializable] sealed class Observation
        {
            public string name;
            public bool passed,finalShift,finalPressedThisFrame;
            public DemoMovePressQueue.Press[] retained;
        }
        [Serializable] sealed class Report
        {
            public bool completed,nativeWindowsInputSent,artisticAcceptance;
            public string startedUtc,finishedUtc,error,inputSystemVersion;
            public Observation[] checks;
        }
        public static void RunAndBuildPrepared(){Run();BenchmarkBuild.BuildPrepared();}
        public static void Run()
        {
            var report=new Report {startedUtc=DateTime.UtcNow.ToString("o"),inputSystemVersion=InputSystem.version.ToString()};
            var checks=new List<Observation>();
            Keyboard keyboard=null;Mouse mouse=null;DemoMovePressQueue presses=null;
            var previousKeyboard=Keyboard.current;var previousMouse=Mouse.current;
            bool accept=true;
            string[] args=Environment.GetCommandLineArgs();
            string path=Path.GetFullPath(Path.Combine(Application.dataPath,"../../local/evidence/unity-queued-press-context.json"));
            for(int i=0;i<args.Length-1;i++)if(args[i]=="-pressContextReport")path=args[i+1];
            if(File.Exists(path))throw new InvalidOperationException("Preserve the previous queued-event report before running again: "+path);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            try
            {
                keyboard=InputSystem.AddDevice<Keyboard>("KragKings-PressContext-Keyboard");
                mouse=InputSystem.AddDevice<Mouse>("KragKings-PressContext-Mouse");
                presses=new DemoMovePressQueue(()=>accept);
                void QueueKeys(params Key[] down)=>InputSystem.QueueStateEvent(keyboard,new KeyboardState(down));
                void Button(bool down,Vector2 point)=>InputSystem.QueueStateEvent(mouse,new MouseState {position=point}.WithButton(MouseButton.Right,down));
                DemoMovePressQueue.Press[] Drain()
                {
                    var result=new List<DemoMovePressQueue.Press>();
                    while(presses.TryDequeue(out var p))if(p.mouseDeviceId==mouse.deviceId)result.Add(p);
                    return result.ToArray();
                }
                void Neutral()
                {
                    QueueKeys();Button(false,Vector2.zero);InputSystem.Update();presses.Clear();
                    _=mouse.rightButton.wasPressedThisFrame; // Warm the same frame-tracking path used by the demo.
                }
                void Check(string name,bool[] expected,Vector2[] positions,bool expectOldPollingFailure=false)
                {
                    var retained=Drain();bool shift=keyboard.leftShiftKey.isPressed||keyboard.rightShiftKey.isPressed;
                    bool ok=retained.Length==expected.Length;
                    for(int i=0;i<retained.Length&&i<expected.Length;i++)
                        ok&=retained[i].walk==expected[i]&&Vector2.Distance(retained[i].position,positions[i])<.001f;
                    if(expectOldPollingFailure)ok&=mouse.rightButton.wasPressedThisFrame&&!shift;
                    checks.Add(new Observation{name=name,passed=ok,finalShift=shift,finalPressedThisFrame=mouse.rightButton.wasPressedThisFrame,retained=retained});
                    if(!ok)throw new InvalidOperationException("Queued input regression failed: "+name);
                }
                foreach(var shift in new[]{Key.LeftShift,Key.RightShift})
                {
                    Neutral();QueueKeys(shift);Button(true,new Vector2(100,200));Button(false,new Vector2(900,950));QueueKeys();InputSystem.Update();
                    Check(shift+" released in the same update retains Walk and press cursor",new[]{true},new[]{new Vector2(100,200)},true);
                }
                Neutral();
                QueueKeys(Key.LeftShift);Button(true,new Vector2(100,200));Button(false,new Vector2(100,200));QueueKeys();
                Button(true,new Vector2(300,400));Button(false,new Vector2(300,400));
                QueueKeys(Key.RightShift);Button(true,new Vector2(500,600));Button(false,new Vector2(500,600));QueueKeys();InputSystem.Update();
                Check("Multiple presses preserve ordered Walk/Run/Walk",new[]{true,false,true},new[]{new Vector2(100,200),new Vector2(300,400),new Vector2(500,600)},true);

                Neutral();QueueKeys(Key.LeftShift);Button(true,new Vector2(100,200));InputSystem.Update();
                InputSystem.ResetDevice(mouse);
                Check("Device reset clears pending commands",Array.Empty<bool>(),Array.Empty<Vector2>());

                Neutral();QueueKeys(Key.RightShift);Button(true,new Vector2(100,200));InputSystem.Update();
                accept=false;presses.Clear();Button(false,Vector2.zero);QueueKeys();Button(true,new Vector2(900,950));Button(false,Vector2.zero);InputSystem.Update();
                Check("Inactive/focus-cleared capture retains no commands",Array.Empty<bool>(),Array.Empty<Vector2>());
                accept=true;Neutral();Button(true,new Vector2(350,450));Button(false,Vector2.zero);InputSystem.Update();
                Check("Re-enabled ordinary press does not inherit Shift",new[]{false},new[]{new Vector2(350,450)});

                Neutral();Button(true,new Vector2(100,200));InputSystem.Update();InputSystem.RemoveDevice(mouse);
                Check("Device removal clears pending commands",Array.Empty<bool>(),Array.Empty<Vector2>());
                report.completed=true;
            }
            catch(Exception e){report.error=e.ToString();throw;}
            finally
            {
                presses?.Dispose();
                if(mouse!=null&&mouse.added)InputSystem.RemoveDevice(mouse);
                if(keyboard!=null&&keyboard.added)InputSystem.RemoveDevice(keyboard);
                if(previousKeyboard!=null&&previousKeyboard.added)previousKeyboard.MakeCurrent();
                if(previousMouse!=null&&previousMouse.added)previousMouse.MakeCurrent();
                report.checks=checks.ToArray();report.finishedUtc=DateTime.UtcNow.ToString("o");
                File.WriteAllText(path,JsonUtility.ToJson(report,true));
            }
            Debug.Log("KRAG_PRESS_CONTEXT_EVENTS_PASS "+checks.Count);
        }
    }
}
