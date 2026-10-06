using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;

namespace KragKings.Benchmark
{
    public sealed class DemoScene : MonoBehaviour
    {
        public Camera demoCamera;
        public DemoUnit[] units;
        public Material indicatorMaterial;
        public string contentFingerprint;
        public DemoUnit Selected { get; private set; }
        public bool AutomatedView {get;set;}
        LineRenderer selectionRing, destinationRing;
        Vector3 cameraFocus;
        float yaw=165, pitch=22, distance=6.4f;
        float markerLife;
        bool showStats;
        float smoothedFrame;
        string message="Select a crew member and explore the dunes.";
        GUIStyle titleStyle, labelStyle, smallStyle, valueStyle;
        readonly Color teal=new(.30f,.82f,.79f);
        readonly Color sand=new(.94f,.85f,.68f);
        readonly List<float> frameTimes=new();
        readonly List<string> runtimeErrors=new();
        readonly List<ShotEvidence> verificationShots=new();
        bool verification;
        bool performanceOnly,performanceSampling,performanceMoving;
        long previousFrameTick;
        bool inputProbe;
        string lastProbeKey;
        float nextProbe;
        string evidencePath;
        string renderQuality;
        DemoCombatAudio combatAudio;
        DemoMovePressQueue movePresses;
        WindowsMovePressSource windowsPresses;
        bool sceneReady;
        DemoMovePressQueue.Press lastMovePress;
        int movePressDispatchCount,lastMoveDispatchFrame;
        bool lastMoveAccepted;
        IDisposable inputProfileLease;
        bool profileInteractiveInput;
        string reportedInputProfile;
        bool applicationPaused,inputSetupFailed;
        string nativeInputRestoreStatus="not attached";
        long nativeOriginalProcedure,nativeHookProcedure,nativeProcedureAfterDispose;
        string MovementBackend=>WindowsMovePressSource.Supported?"Win32 message context":"InputSystem event queue";

        void OnEnable()=>SynchronizeInputCapture();
        void OnDisable(){ReleaseInputCapture();inputProfileLease?.Dispose();inputProfileLease=null;RecordInputProfile("disabled");}
        void OnApplicationFocus(bool focused){movePresses?.Clear();windowsPresses?.Clear();windowsPresses?.SetEnabled(focused&&!applicationPaused);}
        void OnApplicationPause(bool paused){applicationPaused=paused;movePresses?.Clear();windowsPresses?.Clear();windowsPresses?.SetEnabled(!paused&&Application.isFocused);}
        void ReleaseInputCapture()
        {
            movePresses?.Dispose();movePresses=null;
            if(windowsPresses!=null)
            {
                try {windowsPresses.Dispose();nativeProcedureAfterDispose=windowsPresses.ProcedureAfterDispose;nativeInputRestoreStatus=windowsPresses.Restored?"restored":windowsPresses.RestorationDeferred?"deferred behind another subclass until window destruction":"not restored";}
                catch(Exception error){nativeInputRestoreStatus="restoration error: "+error.Message;Debug.LogError(nativeInputRestoreStatus);}
                windowsPresses=null;
            }
        }
        void SynchronizeInputCapture()
        {
            if(!sceneReady||inputSetupFailed)return;
            bool interactive=!performanceOnly&&!AutomatedView&&!verification;
            if(interactive&&windowsPresses==null&&movePresses==null)
            {
                try
                {
                    if(WindowsMovePressSource.Supported)
                    {
                        windowsPresses=new WindowsMovePressSource(inputProbe);nativeInputRestoreStatus="attached";
                        nativeOriginalProcedure=windowsPresses.OriginalProcedure;nativeHookProcedure=windowsPresses.HookProcedure;nativeProcedureAfterDispose=0;
                        if(inputProbe)movePresses=new DemoMovePressQueue(()=>isActiveAndEnabled&&Application.isFocused&&!applicationPaused,recordDiagnostics:true,captureMovement:false);
                    }
                    else movePresses=new DemoMovePressQueue(()=>isActiveAndEnabled&&Application.isFocused&&!applicationPaused&&!performanceOnly&&!AutomatedView&&!verification,inputProbe);
                }
                catch(Exception error){inputSetupFailed=true;ReleaseInputCapture();Debug.LogError("Movement input setup failed: "+error);Application.Quit(1);return;}
            }
            if(!interactive&&(movePresses!=null||windowsPresses!=null))ReleaseInputCapture();
            windowsPresses?.SetEnabled(Application.isFocused&&!applicationPaused);
            if(profileInteractiveInput&&!WindowsMovePressSource.Supported&&inputProfileLease==null)inputProfileLease=DemoMovePressQueue.AcquirePressPositionLease();
            RecordInputProfile("active");
        }
        [Serializable] sealed class InputProfileRecord {public string utc,reason,buildGuid,inputSystemVersion,movementBackend,nativeRestoreStatus;public long nativeOriginalProcedure,nativeHookProcedure,nativeProcedureAfterDispose;public bool disableRedundantEventsMerging,interactiveCapture,nativeAttached,performanceRun,interactiveProfileRequested;}
        void RecordInputProfile(string reason)
        {
            if(!sceneReady||string.IsNullOrEmpty(evidencePath))return;
            bool disabled=InputSystem.settings.disableRedundantEventsMerging;
            string profileKey=disabled+":"+(windowsPresses!=null)+":"+(movePresses!=null);
            if(reason=="active"&&reportedInputProfile==profileKey)return;
            reportedInputProfile=profileKey;
            var profile=new InputProfileRecord {utc=DateTime.UtcNow.ToString("o"),reason=reason,buildGuid=Application.buildGUID,inputSystemVersion=InputSystem.version.ToString(),
                disableRedundantEventsMerging=disabled,interactiveCapture=windowsPresses!=null||movePresses!=null,movementBackend=MovementBackend,nativeAttached=windowsPresses!=null,nativeRestoreStatus=nativeInputRestoreStatus,
                nativeOriginalProcedure=nativeOriginalProcedure,nativeHookProcedure=nativeHookProcedure,nativeProcedureAfterDispose=nativeProcedureAfterDispose,performanceRun=performanceOnly,interactiveProfileRequested=profileInteractiveInput};
            File.AppendAllText(Path.Combine(evidencePath,"input-profile.jsonl"),JsonUtility.ToJson(profile)+Environment.NewLine);
            Debug.Log("KRAG_INPUT_PROFILE "+JsonUtility.ToJson(profile));
        }

        public static bool TryGround(Vector3 point,out RaycastHit hit) => Physics.Raycast(new Vector3(point.x,60,point.z),Vector3.down,out hit,120,1<<8,QueryTriggerInteraction.Ignore);

        void Start()
        {
            Application.logMessageReceived+=RecordError;
            QualitySettings.vSyncCount=0;
            Application.targetFrameRate=-1;
            var contacts=GetComponent<DemoContacts>();
            combatAudio=GetComponent<DemoCombatAudio>();
            foreach(var unit in units) {unit.Initialize();unit.ActionStarted+=Effect;if(contacts)contacts.Attach(unit);}
            selectionRing=Ring("Selection",teal,.023f);
            destinationRing=Ring("Destination",new Color(1,.60f,.22f),.017f);
            destinationRing.enabled=false;
            Select(units[0]);
            ResetCamera();
            string[] args=Environment.GetCommandLineArgs();
            renderQuality=DemoRenderTuning.Apply(args);
            verification=args.Contains("-benchmarkVerify");
            performanceMoving=args.Contains("-benchmarkPerformanceMoving");
            performanceOnly=args.Contains("-benchmarkPerformance")||performanceMoving;
            profileInteractiveInput=args.Contains("-benchmarkInteractiveInputProfile");
            if(verification && performanceOnly)throw new InvalidOperationException("Run functional verification and performance sampling separately.");
            inputProbe=args.Contains("-inputProbe") && !performanceOnly;
            evidencePath=Path.Combine(Application.persistentDataPath,"Evidence");
            for(int i=0;i<args.Length-1;i++) if(args[i]=="-evidencePath") evidencePath=args[i+1];
            Directory.CreateDirectory(evidencePath);
            if(args.Contains("-benchmarkReview"))
            {
                if(verification||performanceOnly||args.Contains("-benchmarkShowcase"))throw new InvalidOperationException("Run visual review separately");
                AutomatedView=true;StartCoroutine(Review());
            }
            if(verification) StartCoroutine(Verify());
            if(performanceOnly) StartCoroutine(MeasurePerformance());
            if(args.Contains("-benchmarkShowcase"))
            {
                if(verification||performanceOnly)throw new InvalidOperationException("Record showcase separately from verification/performance.");
                gameObject.AddComponent<DemoShowcase>().Begin(this,evidencePath,args.Contains("-showcaseWait"));
            }
            previousFrameTick=System.Diagnostics.Stopwatch.GetTimestamp();
            sceneReady=true;
            SynchronizeInputCapture();
            if(inputSetupFailed)return;
            Debug.Log("KRAG_KINGS_DEMO_READY "+SystemInfo.graphicsDeviceName+" "+Screen.width+"x"+Screen.height);
        }
        LineRenderer Ring(string name,Color color,float width)
        {
            var go=new GameObject(name);
            var line=go.AddComponent<LineRenderer>();
            line.sharedMaterial=StrokeMaterial(color);
            line.startColor=line.endColor=color;
            line.widthMultiplier=width;
            line.loop=true;
            line.positionCount=80;
            line.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
            return line;
        }
        Material StrokeMaterial(Color color)
        {
            // HDRP/Unlit does not consume the LineRenderer's vertex tint by default.
            var material=new Material(indicatorMaterial);
            material.SetColor("_UnlitColor",Color.black);
            material.SetColor("_EmissiveColor",color);
            material.SetFloat("_EmissiveExposureWeight",0);
            return material;
        }
        void PositionRing(LineRenderer line,Vector3 center,float radius)
        {
            for(int i=0;i<line.positionCount;i++)
            {
                float angle=i*Mathf.PI*2/line.positionCount;
                Vector3 p=center+new Vector3(Mathf.Cos(angle),0,Mathf.Sin(angle))*radius;
                if(TryGround(p,out var hit)) p=hit.point+hit.normal*.025f;
                line.SetPosition(i,p);
            }
        }
        public void Select(DemoUnit unit)
        {
            Selected=unit;
            message=unit.species=="Nib" ? "Restores ordinary function. No upgrades." : "Heavy armor and industrial bionics.";
        }
        public bool Click(Vector2 screenPosition,bool move,bool walk=false)
        {
            Ray ray=demoCamera.ScreenPointToRay(screenPosition);
            if(!move)
            {
                if(Physics.Raycast(ray,out var unitHit,300,1<<9))
                {
                    var unit=unitHit.collider.GetComponentInParent<DemoUnit>();
                    if(unit) { Select(unit); return true; }
                }
                return false;
            }
            if(Selected && Physics.Raycast(ray,out var terrainHit,300,1<<8) && Selected.MoveTo(terrainHit.point,walk))
            {
                PositionRing(destinationRing,terrainHit.point,.28f);
                destinationRing.enabled=true;markerLife=2;
                return true;
            }
            message="Choose an open spot on walkable sand.";
            return false;
        }
        public void ResetCamera()
        {
            cameraFocus=(units[0].transform.position+units[1].transform.position)*.5f+Vector3.up*.95f;
            yaw=165;pitch=22;distance=6.4f;
        }
        public void PortraitCamera(bool actionBust=false)
        {
            if(!Selected)return;
            cameraFocus=Selected.PortraitFocus;
            yaw=Selected.transform.eulerAngles.y+165;pitch=7;
            distance=Selected.species=="Krag"?1.35f:1.45f;
            if(actionBust && Selected.species=="Krag")
            {
                // Face-only framing cropped the actual raised arm and weapon.
                // Preserve the close facial view, then widen for acting poses.
                cameraFocus-=Vector3.up*.18f;
                yaw-=15;distance=2.4f;
            }
        }
        public void SetView(Vector3 focus,float viewYaw,float viewPitch,float viewDistance)
        {cameraFocus=focus;yaw=viewYaw;pitch=viewPitch;distance=viewDistance;}
        // Actions follow the printed Latin letters on the active keyboard layout
        // (for example A on AZERTY), matching the controls displayed in the demo.
        static bool LetterPressed(Keyboard keyboard,string letter) =>
            keyboard.FindKeyOnCurrentKeyboardLayout(letter)?.wasPressedThisFrame==true;
        void Update()
        {
            long tick=System.Diagnostics.Stopwatch.GetTimestamp();
            float frameSeconds=previousFrameTick>0?(float)((tick-previousFrameTick)/(double)System.Diagnostics.Stopwatch.Frequency):Time.unscaledDeltaTime;
            previousFrameTick=tick;
            smoothedFrame=Mathf.Lerp(smoothedFrame,frameSeconds,.06f);
            if(performanceSampling)frameTimes.Add(frameSeconds*1000);
            SynchronizeInputCapture();
            if(inputSetupFailed)return;
            if(performanceOnly||AutomatedView){movePresses?.Clear();if(Keyboard.current?.escapeKey.wasPressedThisFrame==true)Application.Quit();return;}
            var keyboard=Keyboard.current;var mouse=Mouse.current;
            if(keyboard!=null)
            {
                if(inputProbe)foreach(var key in keyboard.allKeys)
                    if(key.wasPressedThisFrame)lastProbeKey=key.name+" / "+key.displayName;
                if(keyboard.escapeKey.wasPressedThisFrame) Application.Quit();
                if(keyboard.tabKey.wasPressedThisFrame) Select(units[(Array.IndexOf(units,Selected)+1)%units.Length]);
                if(LetterPressed(keyboard,"v") && Selected) Selected.SetVariant(Selected.VariantIndex+1);
                if(LetterPressed(keyboard,"a") && Selected) Selected.Trigger("Melee");
                if(LetterPressed(keyboard,"f") && Selected) Selected.Trigger("Shoot");
                if(LetterPressed(keyboard,"h") && Selected) Selected.Trigger("Hit");
                if(LetterPressed(keyboard,"e") && Selected) Selected.TriggerFace();
                if(LetterPressed(keyboard,"c")) PortraitCamera();
                if(keyboard.homeKey.wasPressedThisFrame) ResetCamera();
                if(keyboard.f3Key.wasPressedThisFrame) showStats=!showStats;
                if(keyboard.f12Key.wasPressedThisFrame) ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,"capture-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+".png"));
                Vector3 pan=new((keyboard.rightArrowKey.isPressed?1:0)-(keyboard.leftArrowKey.isPressed?1:0),0,(keyboard.upArrowKey.isPressed?1:0)-(keyboard.downArrowKey.isPressed?1:0));
                if(pan.sqrMagnitude>0)
                {
                    float aboveGround=TryGround(cameraFocus,out var beforePan)?cameraFocus.y-beforePan.point.y:.95f;
                    cameraFocus+=Quaternion.Euler(0,yaw,0)*pan*(distance*.4f*Time.unscaledDeltaTime);
                    cameraFocus.x=Mathf.Clamp(cameraFocus.x,-700,700);cameraFocus.z=Mathf.Clamp(cameraFocus.z,-700,700);
                    if(TryGround(cameraFocus,out var afterPan))cameraFocus.y=afterPan.point.y+aboveGround;
                }
            }
            if(mouse!=null)
            {
                Vector2 p=mouse.position.ReadValue();
                bool inWorld=p.y>92*Screen.height/1080f && p.y<Screen.height-100*Screen.height/1080f;
                if(inWorld && mouse.leftButton.wasPressedThisFrame) Click(p,false);
                while(movePresses!=null&&movePresses.TryDequeue(out var press))
                {
                    if(!Application.isFocused){movePresses.Clear();break;}
                    DispatchMovePress(press);
                }
                if(mouse.middleButton.isPressed)
                {
                    Vector2 delta=mouse.delta.ReadValue();yaw+=delta.x*.17f;pitch=Mathf.Clamp(pitch-delta.y*.13f,8,72);
                }
                // The pinned Input System normalizes one Windows wheel notch to 1.
                distance=Mathf.Clamp(distance-mouse.scroll.ReadValue().y*.6f,.65f,28);
            }
            while(windowsPresses!=null&&windowsPresses.TryDequeue(out var native))
            {
                if(!Application.isFocused||applicationPaused){windowsPresses.Clear();break;}
                var position=new Vector2((native.clientX+.5f)*Screen.width/native.clientWidth-.5f,Screen.height-.5f-(native.clientY+.5f)*Screen.height/native.clientHeight);
                DispatchMovePress(new DemoMovePressQueue.Press {position=position,walk=native.walk,eventId=native.sequence,eventTime=native.messageTimeMilliseconds/1000.0});
            }
            markerLife-=Time.unscaledDeltaTime;
            if(markerLife<=0) destinationRing.enabled=false;
        }
        void DispatchMovePress(DemoMovePressQueue.Press press)
        {
            bool inWorld=press.position.y>92*Screen.height/1080f&&press.position.y<Screen.height-100*Screen.height/1080f;
            lastMovePress=press;lastMoveDispatchFrame=Time.frameCount;++movePressDispatchCount;
            lastMoveAccepted=inWorld&&Click(press.position,true,press.walk);
        }
        void LateUpdate()
        {
            Quaternion rotation=Quaternion.Euler(pitch,yaw,0);
            Vector3 target=cameraFocus-rotation*Vector3.forward*distance;
            if(TryGround(target,out var hit)) target.y=Mathf.Max(target.y,hit.point.y+.4f);
            demoCamera.transform.SetPositionAndRotation(target,Quaternion.LookRotation(cameraFocus-target));
            if(Selected) PositionRing(selectionRing,Selected.transform.position,Selected.species=="Krag"?.72f:.48f);
            if(inputProbe && Time.unscaledTime>=nextProbe)
            {
                nextProbe=Time.unscaledTime+.1f;
                WriteInputProbe();
            }
        }
        void WriteInputProbe()
        {
            // Native Windows interaction checks use actual camera projections instead
            // of hard-coded monitor coordinates. Ordinary play creates no probe file.
            Vector3 destination=Selected.transform.position+new Vector3(2,0,2);
            if(TryGround(destination,out var hit)) destination=hit.point;
            var report=new InputProbe {frame=Time.frameCount,width=Screen.width,height=Screen.height,
                keyboardLayout=Keyboard.current?.keyboardLayout,physicalAKeyLabel=Keyboard.current?.aKey.displayName,lastKey=lastProbeKey,
                buildGuid=Application.buildGUID,contentFingerprint=contentFingerprint,
                selected=Selected.species,variant=Selected.VariantIndex,action=Selected.CurrentAction,facePlaying=Selected.FacePlaying,
                moving=Selected.IsMoving,walking=Selected.IsWalking,cameraDistance=distance,cameraYaw=yaw,cameraFocus=cameraFocus,moveScreen=demoCamera.WorldToScreenPoint(destination),
                movePressCount=movePressDispatchCount,movePressFrame=lastMoveDispatchFrame,movePress=lastMovePress,movePressAccepted=lastMoveAccepted,
                movementInputEdges=movePresses?.SnapshotDiagnosticEdges(),inputMergingDisabled=InputSystem.settings.disableRedundantEventsMerging,
                movementBackend=MovementBackend,nativePressHistory=windowsPresses?.SnapshotHistory(),nativeWindowHandle=windowsPresses?.WindowHandle??0,nativeInputError=windowsPresses?.CallbackError,
                currentMousePosition=Mouse.current?.position.ReadValue()??Vector2.zero,
                units=units.Select(u=>new InputUnit {species=u.species,position=u.transform.position,
                    action=u.CurrentAction,facePlaying=u.FacePlaying,
                    screen=demoCamera.WorldToScreenPoint(u.transform.position+Vector3.up*u.bodyHeight*.5f)}).ToArray()};
            string path=Path.Combine(evidencePath,"input-probe.json");
            string temp=path+".tmp";
            File.WriteAllText(temp,JsonUtility.ToJson(report));
            if(File.Exists(path)) File.Replace(temp,path,null);else File.Move(temp,path);
        }
        [Serializable] class InputUnit {public string species,action;public bool facePlaying;public Vector3 position,screen;}
        [Serializable] class InputProbe {public int frame,width,height,variant,movePressCount,movePressFrame;public long nativeWindowHandle;public string selected,action,keyboardLayout,physicalAKeyLabel,lastKey,buildGuid,contentFingerprint,movementBackend,nativeInputError;public bool moving,walking,facePlaying,movePressAccepted,inputMergingDisabled;public DemoMovePressQueue.Press movePress;public DemoMovePressQueue.DiagnosticEdge[] movementInputEdges;public WindowsMovePressSource.Press[] nativePressHistory;public Vector2 currentMousePosition;public float cameraDistance,cameraYaw;public Vector3 cameraFocus,moveScreen;public InputUnit[] units;}
        void Effect(DemoUnit unit,string action) { if(combatAudio)combatAudio.Action(unit,action);if(action=="Shoot")StartCoroutine(Tracer(unit)); }
        IEnumerator Tracer(DemoUnit unit)
        {
            int version=unit.ActionVersion;float began=Time.time;
            foreach(float normalized in unit.weapon.fireTimesNormalized)
            {
                float due=began+normalized*unit.ActionDuration("Shoot");
                while(Time.time<due){if(unit.ActionVersion!=version)yield break;yield return null;}
                yield return new WaitForEndOfFrame();
                if(unit.ActionVersion!=version)yield break;
                if(combatAudio)combatAudio.Shot(unit);
                Vector3 start=unit.ShotOrigin,direction=unit.ShotDirection,end=start+direction*7;
                if(verification)
                    verificationShots.Add(new ShotEvidence{species=unit.species,variant=unit.Model.name,
                        requestedNormalizedTime=normalized,observedNormalizedTime=(Time.time-began)/unit.ActionDuration("Shoot"),
                        origin=start,direction=direction,unitForward=unit.transform.forward,
                        forwardDeviationDegrees=direction.sqrMagnitude>.5f?Vector3.Angle(direction,unit.transform.forward):180});
                if(Physics.Raycast(start,direction,out var ground,7,1<<8))end=ground.point;
                var go=new GameObject("Shot tracer");var line=go.AddComponent<LineRenderer>();
                var material=StrokeMaterial(new Color(1,.73f,.25f));line.sharedMaterial=material;
                material.SetFloat("_EmissiveExposureWeight",1);material.SetColor("_EmissiveColor",new Color(1,.73f,.25f)*100000);
                line.startColor=new Color(1,.85f,.35f);line.endColor=new Color(1,.6f,.15f,0);line.startWidth=.022f;line.endWidth=.008f;line.positionCount=2;
                line.SetPosition(0,start);line.SetPosition(1,end);
                var flash=GameObject.CreatePrimitive(PrimitiveType.Sphere);flash.name="Muzzle flash";
                Destroy(flash.GetComponent<Collider>());flash.transform.SetPositionAndRotation(start+direction*.035f,Quaternion.LookRotation(direction));
                flash.transform.localScale=unit.species=="Krag"?new Vector3(.035f,.035f,.10f):new Vector3(.023f,.023f,.07f);
                var flashRenderer=flash.GetComponent<MeshRenderer>();flashRenderer.sharedMaterial=material;flashRenderer.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
                Destroy(flash,.035f);
                Destroy(go,.055f);Destroy(material,.06f);
            }
        }
        void OnDestroy()
        {
            Application.logMessageReceived-=RecordError;
            if(selectionRing) Destroy(selectionRing.sharedMaterial);
            if(destinationRing) Destroy(destinationRing.sharedMaterial);
        }
        void RecordError(string condition,string stack,LogType type)
        {
            if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert)runtimeErrors.Add(condition);
        }
        void OnGUI()
        {
            if(titleStyle==null)
            {
                titleStyle=new GUIStyle(GUI.skin.label){fontSize=27,fontStyle=FontStyle.Bold};titleStyle.normal.textColor=sand;
                labelStyle=new GUIStyle(GUI.skin.label){fontSize=19};labelStyle.normal.textColor=Color.white;
                smallStyle=new GUIStyle(GUI.skin.label){fontSize=15};smallStyle.normal.textColor=new Color(.75f,.76f,.73f);
                valueStyle=new GUIStyle(labelStyle){fontSize=23,fontStyle=FontStyle.Bold};valueStyle.normal.textColor=teal;
            }
            GUI.matrix=Matrix4x4.TRS(Vector3.zero,Quaternion.identity,new Vector3(Screen.width/1920f,Screen.height/1080f,1));
            Panel(new Rect(0,0,1920,93));Panel(new Rect(0,984,1920,96));
            GUI.Label(new Rect(35,17,390,45),"KRAG KINGS",titleStyle);
            GUI.Label(new Rect(36,56,650,28),"DUNES  /  CHARACTER & MOVEMENT STUDY",smallStyle);
            GUI.Label(new Rect(1610,23,280,30),"UNITY  ·  HDRP",labelStyle);
            if(Selected)
            {
                GUI.Label(new Rect(700,16,560,40),Selected.species.ToUpper()+"  /  "+Selected.VariantLabel.ToUpper(),valueStyle);
                GUI.Label(new Rect(700,54,700,28),message,smallStyle);
            }
            GUI.Label(new Rect(35,1001,1530,30),"SELECT  Left click     RUN  Right click     WALK  Shift + Right click     MELEE  A     SHOOT  F     HIT  H     BIONICS  V     NEXT  Tab",labelStyle);
            GUI.Label(new Rect(35,1038,1540,28),"FACE  E     PORTRAIT  C     CAMERA  Arrows · Middle drag · Scroll     RESET  Home     CAPTURE  F12     PERFORMANCE  F3     EXIT  Esc",smallStyle);
            if(Selected) GUI.Label(new Rect(1580,1010,315,40),Selected.FacePlaying && Selected.CurrentAction=="Idle" ? "EXPRESSION" : Selected.CurrentAction.ToUpper(),valueStyle);
            if(showStats) { Panel(new Rect(25,110,445,91));GUI.Label(new Rect(40,120,420,30),$"{1/Mathf.Max(.0001f,smoothedFrame):F0} FPS  ·  {smoothedFrame*1000:F1} ms",labelStyle);GUI.Label(new Rect(40,158,420,25),SystemInfo.graphicsDeviceName,smallStyle); }
        }
        static void Panel(Rect rect) { Color old=GUI.color;GUI.color=new Color(.026f,.047f,.049f,.92f);GUI.DrawTexture(rect,Texture2D.whiteTexture);GUI.color=old; }

        IEnumerator Review()
        {
            yield return new WaitForSecondsRealtime(12);
            foreach(var unit in units)unit.SetVariant(0);
            Select(units[0]);ResetCamera();yield return new WaitForSecondsRealtime(.6f);
            ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,"Unity-Natural-Pair.png"));
            yield return new WaitForSecondsRealtime(.5f);
            foreach(var unit in units)
            {
                Select(unit);PortraitCamera();yield return new WaitForSecondsRealtime(.6f);
                ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.species+"-Portrait.png"));
                yield return new WaitForSecondsRealtime(.5f);
                unit.TriggerFace();yield return new WaitForSeconds(unit.ActionDuration("FacePerformance")*.35f);
                ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.species+"-Expression.png"));
                yield return new WaitForSecondsRealtime(.5f);
                while(unit.FacePlaying)yield return null;
                foreach(string action in new[]{"Melee","Shoot","Hit"})
                {
                    unit.Trigger(action);PortraitCamera(true);
                    float normalized=action=="Shoot"?unit.weapon.fireTimesNormalized[0]:.45f;
                    yield return new WaitForSeconds(unit.ActionDuration(action)*normalized);
                    ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.species+"-"+action+"-Expression.png"));
                    yield return new WaitForSeconds(unit.ActionDuration(action)*(1-normalized)+.25f);
                }
            }
            Debug.Log("BENCHMARK_VISUAL_REVIEW_CAPTURED "+contentFingerprint);
            Application.Quit(runtimeErrors.Count==0?0:1);
        }
        IEnumerator Verify()
        {
            yield return new WaitForSeconds(12);
            var checks=new List<string>();var failures=new List<string>();
            var deformationChecks=new List<DeformationEvidence>();
            var terrain=DemoTerrainReference.Sample();
            if(terrain.All(s=>s.passed))checks.Add("Imported dune coordinates and upward collision normals match the shared source");
            else failures.Add("Imported dune coordinates/collision normals differ from the shared source");
            // These are separate actors. Selection and camera inspection must not
            // serialize their actions or reset a previously selected performance.
            Select(units[0]);units[0].Trigger("Melee");
            yield return null;
            Vector3 otherScreen=demoCamera.WorldToScreenPoint(units[1].transform.position+Vector3.up*units[1].bodyHeight*.5f);
            if(!Click(otherScreen,false))failures.Add("Concurrent action: second unit could not be selected");
            units[1].Trigger("Shoot");
            yaw+=25;distance-=.5f;cameraFocus+=Vector3.right*.25f;
            yield return new WaitForEndOfFrame();
            if(units[0].CurrentAction!="Melee"||units[1].CurrentAction!="Shoot")failures.Add("Concurrent actions interrupted one another");
            else checks.Add("Independent overlapping Krag melee and Nib shooting while changing camera");
            yield return new WaitForSeconds(Mathf.Max(units[0].ActionDuration("Melee"),units[1].ActionDuration("Shoot"))+.2f);
            ResetCamera();
            foreach(var unit in units)
            {
                Vector3 screen=demoCamera.WorldToScreenPoint(unit.transform.position+Vector3.up*unit.bodyHeight*.5f);
                if(Click(screen,false) && Selected==unit) checks.Add(unit.species+": ray selection");else failures.Add(unit.species+": ray selection failed");
                for(int v=0;v<unit.variants.Length;v++)
                {
                    unit.SetVariant(v);yield return new WaitForSeconds(.5f);
                    foreach(string action in new[]{"Idle","Walk","Run","Melee","Shoot","Hit","FacePerformance"}) if(!unit.HasAction(action)) failures.Add(unit.Model.name+": missing "+action);
                    ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.Model.name+".png"));
                    yield return new WaitForEndOfFrame();
                    var observed=new DeformationEvidence{variant=unit.Model.name};
                    var idleFace=new ActionExpressionEvidence{action="Idle"};
                    float idleEnd=Time.time+Mathf.Max(.5f,unit.ActionDuration("Idle"));
                    while(Time.time<idleEnd)
                    {
                        yield return null;
                        idleFace.maximumFacialMorphWeight=Mathf.Max(idleFace.maximumFacialMorphWeight,unit.MaximumMorphWeight("facial"));
                    }
                    if(idleFace.maximumFacialMorphWeight<1)failures.Add(unit.Model.name+": no facial corrective activation during Idle");
                    observed.actionExpressions.Add(idleFace);
                    foreach(string action in new[]{"Melee","Shoot","Hit"})
                    {
                        unit.Trigger(action);
                        float actionStarted=Time.time;
                        float end=actionStarted+unit.ActionDuration(action)+.2f;
                        float captureDue=actionStarted+unit.ActionDuration(action)*(action=="Shoot"?unit.weapon.fireTimesNormalized[0]:.45f);
                        bool actionCaptured=false;
                        var actionFace=new ActionExpressionEvidence{action=action};
                        while(Time.time<end)
                        {
                            yield return null;
                            if(!actionCaptured && Time.time>=captureDue)
                            {
                                ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.Model.name+"-"+action+"-pose.png"));
                                actionCaptured=true;
                            }
                            observed.maximumBodyMorphWeight=Mathf.Max(observed.maximumBodyMorphWeight,unit.MaximumMorphWeight("body"));
                            actionFace.maximumFacialMorphWeight=Mathf.Max(actionFace.maximumFacialMorphWeight,unit.MaximumMorphWeight("facial"));
                        }
                        if(actionFace.maximumFacialMorphWeight<1)failures.Add(unit.Model.name+": no facial corrective activation during "+action);
                        observed.actionExpressions.Add(actionFace);
                    }
                    unit.TriggerFace();PortraitCamera();
                    float faceStart=Time.time;bool portraitCaptured=false;
                    while(unit.FacePlaying)
                    {
                        yield return null;
                        observed.maximumFacialMorphWeight=Mathf.Max(observed.maximumFacialMorphWeight,unit.MaximumMorphWeight("facial"));
                        if(!portraitCaptured && Time.time-faceStart>unit.ActionDuration("FacePerformance")*.35f)
                        {ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,unit.Model.name+"-face.png"));portraitCaptured=true;}
                    }
                    ResetCamera();
                    if(observed.maximumBodyMorphWeight<1)failures.Add(unit.Model.name+": body corrective morphs did not activate during actions");
                    if(observed.maximumFacialMorphWeight<1)failures.Add(unit.Model.name+": facial morphs did not activate during FacePerformance");
                    deformationChecks.Add(observed);
                    checks.Add(unit.Model.name+": variants/actions exercised");
                }
                unit.SetVariant(0);
                Vector3 start=unit.transform.position;
                int route=0,contacts=0;
                void CountContact(DemoUnit ignored,Vector3 point,Vector3 normal){contacts++;}
                unit.FootContact+=CountContact;
                foreach(Vector3 offset in new[]{new Vector3(2,0,3),new Vector3(-3,0,-4),Vector3.zero})
                {
                    Vector3 destination=start+offset;
                    if(!TryGround(destination,out var hit)) {failures.Add("Missing dune collision");continue;}
                    bool walking=route++==0;
                    if(!unit.MoveTo(hit.point,walking)) failures.Add("Move rejected");
                    float timeout=Time.time+Vector3.Distance(unit.transform.position,hit.point)/(walking?unit.walkSpeed:unit.runSpeed)+6;
                    bool sawGait=false;
                    float gaitFaceMaximum=0;
                    while(Vector3.Distance(unit.transform.position,hit.point)>.16f && Time.time<timeout)
                    {
                        sawGait|=unit.CurrentAction==(walking?"Walk":"Run");
                        gaitFaceMaximum=Mathf.Max(gaitFaceMaximum,unit.MaximumMorphWeight("facial"));
                        if(TryGround(unit.transform.position,out var ground) && Mathf.Abs(unit.transform.position.y-ground.point.y)>.025f) failures.Add(unit.species+": terrain separation");
                        yield return null;
                    }
                    if(Vector3.Distance(unit.transform.position,hit.point)>.16f) failures.Add(unit.species+": movement timeout");
                    if(!sawGait)failures.Add(unit.species+": expected locomotion clip did not play");
                    if(gaitFaceMaximum<1)failures.Add(unit.species+": no facial corrective activation during "+(walking?"Walk":"Run"));
                }
                unit.FootContact-=CountContact;
                if(contacts<4)failures.Add(unit.species+": too few authored foot contacts during traversal");
                checks.Add(unit.species+": dune traversal completed");
            }
            Select(units[0]);ResetCamera();yield return new WaitForSeconds(1);
            ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,"Unity-Dunes-Final.png"));
            yield return new WaitForSeconds(1);
            // Regression for the measured firing-arm fault: sample the actual
            // animated muzzle markers at discharge, not just an active clip.
            // Ten degrees is a diagnostic tolerance for this forward-fire demo,
            // not a weapon accuracy or tactical combat rule.
            foreach(var unit in units.Where(u=>u.species=="Krag"))
                foreach(var model in unit.variants)
                {
                    var shots=verificationShots.Where(s=>s.species==unit.species && s.variant==model.name).ToArray();
                    if(shots.Length<unit.weapon.fireTimesNormalized.Length)failures.Add(model.name+": missing actual discharge-marker samples");
                    else if(shots.Any(s=>s.forwardDeviationDegrees>10))failures.Add(model.name+": firing muzzle deviates more than 10 degrees from unit forward");
                    else checks.Add(model.name+": actual firing markers aim within diagnostic forward tolerance");
                }
            failures.AddRange(runtimeErrors);
            var report=new VerificationReport{engine=Application.unityVersion,gpu=SystemInfo.graphicsDeviceName,resolution=$"{Screen.width}x{Screen.height}",contentFingerprint=contentFingerprint,buildGuid=Application.buildGUID,checks=checks.ToArray(),failures=failures.Distinct().ToArray(),deformation=deformationChecks.ToArray(),shots=verificationShots.ToArray(),terrain=terrain};
            File.WriteAllText(Path.Combine(evidencePath,"verification.json"),JsonUtility.ToJson(report,true));
            Debug.Log("BENCHMARK_VERIFICATION "+(report.failures.Length==0?"PASS":"FAIL"));
            Application.Quit(report.failures.Length==0?0:1);
        }
        IEnumerator MeasurePerformance()
        {
            foreach(var unit in units)unit.SetVariant(0);
            Select(units[0]);ResetCamera();
            Coroutine movement=performanceMoving?StartCoroutine(PerformanceMotion()):null;
            yield return new WaitForSecondsRealtime(15);
            frameTimes.Clear();performanceSampling=true;
            string sampleStartedUtc=DateTime.UtcNow.ToString("o");
            long sampleStartedTick=System.Diagnostics.Stopwatch.GetTimestamp();
            yield return new WaitForSecondsRealtime(30);
            performanceSampling=false;
            string sampleEndedUtc=DateTime.UtcNow.ToString("o");
            double sampleElapsedSeconds=(System.Diagnostics.Stopwatch.GetTimestamp()-sampleStartedTick)/(double)System.Diagnostics.Stopwatch.Frequency;
            if(movement!=null)StopCoroutine(movement);
            var times=frameTimes.OrderBy(x=>x).ToArray();
            var report=new PerformanceReport{engine=Application.unityVersion,gpu=SystemInfo.graphicsDeviceName,
                contentFingerprint=contentFingerprint,buildGuid=Application.buildGUID,
                graphicsAPI=SystemInfo.graphicsDeviceType.ToString(),cpu=SystemInfo.processorType,vramMB=SystemInfo.graphicsMemorySize,
                resolution=$"{Screen.width}x{Screen.height}",warmupSeconds=15,sampleSeconds=30,frames=times.Length,
                sampleStartedUtc=sampleStartedUtc,sampleEndedUtc=sampleEndedUtc,sampleElapsedSeconds=sampleElapsedSeconds,
                meanMs=times.Length>0?times.Average():0,p95Ms=Percentile(times,.95f),p99Ms=Percentile(times,.99f),
                workload=performanceMoving?"Natural Krag and Nib, repeated 12-second run/melee/shoot/hit sequence, fixed default camera; no captures or input probes during sample":"Natural Krag and Nib, Idle, default camera, same dune surface; no captures or input probes during sample",
                quality=renderQuality,internalResolution=$"{demoCamera.scaledPixelWidth}x{demoCamera.scaledPixelHeight}",
                inputSystemVersion=InputSystem.version.ToString(),movementBackend=MovementBackend,disableRedundantEventsMerging=InputSystem.settings.disableRedundantEventsMerging,interactiveInputProfileRequested=profileInteractiveInput,
                cameraDistance=Vector3.Distance(demoCamera.transform.position,cameraFocus),
                failures=runtimeErrors.Distinct().ToArray()};
            File.WriteAllText(Path.Combine(evidencePath,"performance.json"),JsonUtility.ToJson(report,true));
            ScreenCapture.CaptureScreenshot(Path.Combine(evidencePath,"performance-view.png"));
            yield return new WaitForSecondsRealtime(1);
            Application.Quit(report.failures.Length==0&&times.Length>0?0:1);
        }
        IEnumerator PerformanceMotion()
        {
            Vector3 kragOrigin=units[0].transform.position,nibOrigin=units[1].transform.position;
            var offsets=new[]{new Vector3(.6f,0,2),new Vector3(-.4f,0,1.8f)};
            float[] times={0,3,4.3f,6,9};
            double cycleStart=Time.realtimeSinceStartupAsDouble;
            while(true)
            {
                for(int stage=0;stage<times.Length;stage++)
                {
                    while(Time.realtimeSinceStartupAsDouble-cycleStart<times[stage])yield return null;
                    switch(stage)
                    {
                        case 0: units[0].MoveTo(kragOrigin+offsets[0]);units[1].MoveTo(nibOrigin+offsets[1]);break;
                        case 1: units[0].Trigger("Melee");units[1].Trigger("Shoot");break;
                        case 2: units[0].Trigger("Hit");units[1].Trigger("Melee");break;
                        case 3: units[0].MoveTo(kragOrigin);units[1].MoveTo(nibOrigin);break;
                        case 4: units[0].Trigger("Shoot");units[1].Trigger("Hit");break;
                    }
                }
                while(Time.realtimeSinceStartupAsDouble-cycleStart<12)yield return null;
                cycleStart+=12;
            }
        }
        static float Percentile(float[] sorted,float p)=>sorted.Length>0?sorted[Mathf.Clamp(Mathf.CeilToInt(sorted.Length*p)-1,0,sorted.Length-1)]:0;
        [Serializable] class ActionExpressionEvidence {public string action;public float maximumFacialMorphWeight;}
        [Serializable] class ShotEvidence {public string species,variant;public float requestedNormalizedTime,observedNormalizedTime,forwardDeviationDegrees;public Vector3 origin,direction,unitForward;}
        [Serializable] class DeformationEvidence {public string variant;public float maximumBodyMorphWeight,maximumFacialMorphWeight;public List<ActionExpressionEvidence> actionExpressions=new();}
        [Serializable] class VerificationReport { public string engine,gpu,resolution,contentFingerprint,buildGuid;public string[] checks,failures;public DeformationEvidence[] deformation;public ShotEvidence[] shots;public DemoTerrainReference.Evidence[] terrain; }
        [Serializable] class PerformanceReport {public string engine,gpu,graphicsAPI,cpu,resolution,internalResolution,workload,quality,contentFingerprint,buildGuid,sampleStartedUtc,sampleEndedUtc,inputSystemVersion,movementBackend;public bool disableRedundantEventsMerging,interactiveInputProfileRequested;public double sampleElapsedSeconds;public float cameraDistance;public int vramMB,warmupSeconds,sampleSeconds,frames;public float meanMs,p95Ms,p99Ms;public string[] failures;}
    }
}
