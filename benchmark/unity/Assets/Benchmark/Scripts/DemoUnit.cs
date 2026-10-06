using System;
using System.Collections.Generic;
using UnityEngine;

namespace KragKings.Benchmark
{
    public sealed class DemoUnit : MonoBehaviour
    {
        public string species;
        public GameObject[] variants;
        public string[] variantLabels;
        public float runSpeed = 3.4f;
        public float walkSpeed = 1.25f;
        [Serializable] public class LocomotionCycle
        {
            public float speedMetersPerSecond,cycleSeconds,stanceFraction;
            public float[] leftContacts,rightContacts;
        }
        [Serializable] public class LocomotionSet {public LocomotionCycle Walk,Run;}
        public LocomotionSet locomotion;
        [Serializable] public class WeaponContract {public string muzzleBone,aimBone;public float[] fireTimesNormalized;}
        public WeaponContract weapon;
        public float bodyHeight = 2.1f;
        public int VariantIndex { get; private set; }
        public string CurrentAction { get; private set; } = "Idle";
        public int ActionVersion {get;private set;}
        public Vector3 ShotOrigin=>muzzle.position;
        public Vector3 ShotDirection=>(weaponAim.position-muzzle.position).normalized;
        public bool IsMoving { get; private set; }
        public bool IsWalking { get; private set; }
        public bool FacePlaying => facialRemaining>0;
        public Vector3 PortraitFocus => head ? head.position+Vector3.up*(species=="Krag"?.11f:.08f) : transform.position+Vector3.up*bodyHeight*.85f;
        public Vector3 Destination { get; private set; }
        public GameObject Model { get; private set; }
        Renderer[] modelRenderers=Array.Empty<Renderer>();
        public Bounds VisualBounds
        {
            get
            {
                Bounds bounds=new(transform.position+Vector3.up*bodyHeight*.5f,new Vector3(FootprintRadius*2,bodyHeight,FootprintRadius*2));
                foreach(var renderer in modelRenderers)
                    if(renderer && renderer.enabled && renderer.gameObject.activeInHierarchy)bounds.Encapsulate(renderer.bounds);
                return bounds;
            }
        }
        public string VariantLabel => variantLabels != null && VariantIndex < variantLabels.Length ? variantLabels[VariantIndex] : "Natural";
        public event Action<DemoUnit, string> ActionStarted;
        public event Action<DemoUnit, Vector3, Vector3> FootContact;
        Animation animationPlayer;
        readonly Dictionary<string, AnimationClip> clips = new();
        readonly List<Leg> legs = new();
        float actionRemaining;
        float facialRemaining;
        Transform head;
        Transform muzzle,weaponAim;
        float travelSpeed;
        string contactClip;
        float previousContactTime;
        bool hasDestination;
        static readonly HashSet<DemoUnit> activeUnits=new();
        public float FootprintRadius=>species=="Krag"?.47f:.29f;
        void OnEnable()=>activeUnits.Add(this);
        void OnDisable()=>activeUnits.Remove(this);
        bool ClearFootprint(Vector3 end,bool swept)
        {
            Vector3 start=transform.position;start.y=0;end.y=0;
            Vector3 segment=end-start;
            foreach(var other in activeUnits)
            {
                if(!other||other==this)continue;
                Vector3 center=other.transform.position;center.y=0;
                float radius=FootprintRadius+other.FootprintRadius+.025f;
                float initial=(start-center).sqrMagnitude;
                // Let either unit move out of an existing overlap during recovery.
                if(swept&&initial<radius*radius&&(end-center).sqrMagnitude>initial)continue;
                Vector3 nearest=swept?start+segment*Mathf.Clamp01(Vector3.Dot(center-start,segment)/Mathf.Max(.000001f,segment.sqrMagnitude)):end;
                if((nearest-center).sqrMagnitude<radius*radius)return false;
            }
            return true;
        }
        class Leg { public Transform hip, knee, ankle; public float sole;public string side;public bool planted;public Vector3 plantPosition; }

        public void Initialize()
        {
            var capsule = GetComponent<CapsuleCollider>() ?? gameObject.AddComponent<CapsuleCollider>();
            capsule.height = bodyHeight;
            capsule.radius = FootprintRadius;
            capsule.center = Vector3.up * bodyHeight * .5f;
            gameObject.layer = 9;
            Ground();
            SetVariant(0);
        }

        public void SetVariant(int index)
        {
            if (variants == null || variants.Length == 0) throw new InvalidOperationException($"Missing {species} variants");
            VariantIndex = (index % variants.Length + variants.Length) % variants.Length;
            if (Model) { Model.SetActive(false); Destroy(Model); }
            Model = Instantiate(variants[VariantIndex], transform);
            Model.name = variants[VariantIndex].name;
            Model.transform.localPosition = Vector3.zero;
            Model.transform.localRotation = Quaternion.identity;
            modelRenderers=Model.GetComponentsInChildren<Renderer>();
            foreach (var child in Model.GetComponentsInChildren<Transform>()) child.gameObject.layer = 9;
            foreach (var animator in Model.GetComponentsInChildren<Animator>()) animator.enabled = false;
            animationPlayer = Model.GetComponent<Animation>() ?? Model.AddComponent<Animation>();
            animationPlayer.cullingType = AnimationCullingType.AlwaysAnimate;
            clips.Clear();
            foreach (AnimationState state in animationPlayer)
            {
                string key = CanonicalClip(state.name);
                if (key != null) clips[key] = state.clip;
            }
            // The importer assigns canonical names to the seven required clips.
            foreach (var pair in clips)
            {
                if (!animationPlayer.GetClip(pair.Key)) animationPlayer.AddClip(pair.Value, pair.Key);
                animationPlayer[pair.Key].wrapMode = pair.Key == "Idle" || pair.Key == "Walk" || pair.Key == "Run" ? WrapMode.Loop : WrapMode.Once;
            }
            head=Bone("Head");
            muzzle=Bone(weapon.muzzleBone);weaponAim=Bone(weapon.aimBone);
            if(!muzzle||!weaponAim)throw new InvalidOperationException(Model.name+": missing animated weapon markers");
            Transform faceRoot=Bone("FaceRoot");
            if(clips.ContainsKey("FacePerformance"))
            {
                if(!faceRoot) throw new InvalidOperationException(Model.name+": FacePerformance requires a FaceRoot subtree");
                var facial=animationPlayer["FacePerformance"];
                facial.layer=1;facial.AddMixingTransform(faceRoot,true);
            }
            legs.Clear();
            FindLeg("L"); FindLeg("R");
            hasDestination = IsMoving = false;
            actionRemaining = 0;
            facialRemaining = 0;
            travelSpeed=0;contactClip=null;
            CurrentAction = "";
            Play("Idle");
        }

        public static string CanonicalClip(string name)
        {
            foreach (string clip in new[] { "Idle", "Walk", "Run", "Melee", "Shoot", "Hit", "FacePerformance" })
                if (name.Equals(clip, StringComparison.OrdinalIgnoreCase) || name.EndsWith("|" + clip, StringComparison.OrdinalIgnoreCase) || name.EndsWith("_" + clip, StringComparison.OrdinalIgnoreCase)) return clip;
            return null;
        }
        public bool HasAction(string name) => clips.ContainsKey(name);
        public float ActionDuration(string name) => clips.TryGetValue(name,out var clip)?clip.length:0;
        public float MaximumMorphWeight(string kind)
        {
            var deformation=Model?Model.GetComponent<DemoDeformation>():null;
            return deformation?deformation.MaximumAppliedWeight(kind):0;
        }

        Transform Bone(params string[] names)
        {
            foreach (var bone in Model.GetComponentsInChildren<Transform>())
                foreach (var name in names)
                    if (bone.name.Equals(name, StringComparison.OrdinalIgnoreCase)) return bone;
            return null;
        }
        void FindLeg(string side)
        {
            Transform hip = Bone("Thigh_"+side, "Thigh."+side, "UpperLeg_"+side);
            Transform knee = Bone("Shin_"+side, "Shin."+side, "LowerLeg_"+side);
            Transform foot = Bone("Foot_"+side, "Foot."+side);
            if (hip && knee && foot) legs.Add(new Leg {hip=hip,knee=knee,ankle=foot,side=side,sole=Mathf.Clamp(foot.position.y-transform.position.y,.06f,.26f)});
        }

        public bool MoveTo(Vector3 destination, bool walk=false)
        {
            if(Mathf.Abs(destination.x)>700||Mathf.Abs(destination.z)>700)return false;
            if (!DemoScene.TryGround(destination, out var hit) || Vector3.Angle(hit.normal, Vector3.up) > 40 || !ClearFootprint(hit.point,false)) return false;
            Destination = hit.point;
            IsWalking = walk;
            hasDestination = true;
            return true;
        }
        public void Trigger(string action)
        {
            if (action != "Melee" && action != "Shoot" && action != "Hit") return;
            if (!clips.TryGetValue(action, out var clip)) { Debug.LogError($"{Model.name} missing {action}"); return; }
            // A new action supersedes the previous move. A fresh right-click during
            // this action can still queue the next destination independently.
            hasDestination = false;
            IsMoving = false;
            travelSpeed=0;
            actionRemaining = Mathf.Max(.15f, clip.length);
            Play(action, true);
            ActionStarted?.Invoke(this,action);
        }
        public void TriggerFace()
        {
            if(!clips.TryGetValue("FacePerformance",out var clip)) {Debug.LogError(Model.name+": missing facial performance");return;}
            animationPlayer["FacePerformance"].time=0;
            animationPlayer.CrossFade("FacePerformance",.15f,PlayMode.StopSameLayer);
            facialRemaining=clip.length;
        }
        void Play(string action, bool restart=false)
        {
            if (!restart && CurrentAction == action) return;
            // Provisional presentation tuning: independent breathing/attention
            // on each Idle entry. Continuous Idle returns above without seeking.
            float phase=action=="Idle" && species=="Nib" ? .37f : 0;
            bool oldGait=CurrentAction=="Walk"||CurrentAction=="Run";
            bool newGait=action=="Walk"||action=="Run";
            if(!restart && IsMoving && oldGait && newGait && animationPlayer[CurrentAction]!=null)
            {
                var oldCycle=CurrentAction=="Walk"?locomotion?.Walk:locomotion?.Run;
                var newCycle=action=="Walk"?locomotion?.Walk:locomotion?.Run;
                float oldLeft=oldCycle?.leftContacts?.Length>0?oldCycle.leftContacts[0]:0;
                float newLeft=newCycle?.leftContacts?.Length>0?newCycle.leftContacts[0]:0;
                phase=Mathf.Repeat(animationPlayer[CurrentAction].normalizedTime-oldLeft+newLeft,1);
            }
            ActionVersion++;
            CurrentAction = action;
            if (!clips.ContainsKey(action)) return;
            animationPlayer[action].time = phase*clips[action].length;
            animationPlayer.CrossFade(action, .12f, PlayMode.StopSameLayer);
        }
        void Update()
        {
            facialRemaining=Mathf.Max(0,facialRemaining-Time.deltaTime);
            if (actionRemaining > 0)
            {
                actionRemaining -= Time.deltaTime;
                if (actionRemaining <= 0) Play("Idle");
                return;
            }
            Vector3 delta = Destination-transform.position;
            delta.y=0;
            IsMoving = hasDestination && delta.sqrMagnitude > .018f;
            if (!IsMoving) {hasDestination=false;travelSpeed=0;Play("Idle");return;}
            Quaternion facing=Quaternion.LookRotation(delta.normalized,Vector3.up);
            transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,(species=="Krag"?300:720)*Time.deltaTime);
            float nominal=IsWalking?walkSpeed:runSpeed;
            float acceleration=species=="Krag"?7:12;
            float stoppingSpeed=Mathf.Sqrt(2*acceleration*delta.magnitude);
            float turnLimit=Quaternion.Angle(transform.rotation,facing)>70?0:nominal;
            travelSpeed=Mathf.MoveTowards(travelSpeed,Mathf.Min(turnLimit,stoppingSpeed),acceleration*Time.deltaTime);
            float speed=travelSpeed;
            Vector3 next=transform.position+delta.normalized*Mathf.Min(delta.magnitude,speed*Time.deltaTime);
            if (ClearFootprint(next,true) && DemoScene.TryGround(next,out var hit) && Vector3.Angle(hit.normal,Vector3.up)<40)
            {
                Vector3 difference=hit.point-transform.position;
                // Keep speed in surface meters/sec, including the hill's vertical component.
                if(difference.magnitude>speed*Time.deltaTime) next=transform.position+difference.normalized*speed*Time.deltaTime;
                if(DemoScene.TryGround(next,out var corrected)) transform.position=corrected.point;
            }
            else { hasDestination=false; IsMoving=false; }
            Play(IsMoving?(IsWalking?"Walk":"Run"):"Idle");
            if(IsMoving && animationPlayer[CurrentAction]!=null)
            {
                var cycle=IsWalking?locomotion?.Walk:locomotion?.Run;
                float durationScale=cycle!=null && cycle.cycleSeconds>0?clips[CurrentAction].length/cycle.cycleSeconds:1;
                animationPlayer[CurrentAction].speed=speed/Mathf.Max(.01f,nominal)*durationScale;
            }
        }
        void Ground() { if(DemoScene.TryGround(transform.position,out var hit)) transform.position=hit.point; }
        void LateUpdate()
        {
            if(!Model) return;
            LocomotionCycle cycle=IsMoving?(IsWalking?locomotion?.Walk:locomotion?.Run):null;
            float cycleTime=cycle!=null && animationPlayer[CurrentAction]!=null?animationPlayer[CurrentAction].normalizedTime:0;
            bool changed=contactClip!=CurrentAction;
            if(changed)
            {
                bool switchedGait=(contactClip=="Walk"||contactClip=="Run")&&(CurrentAction=="Walk"||CurrentAction=="Run");
                contactClip=CurrentAction;previousContactTime=cycleTime-(switchedGait?0:.001f);
                foreach(var leg in legs)leg.planted=false;
            }
            foreach(var leg in legs)
            {
                if(!DemoScene.TryGround(leg.ankle.position,out var contact)) continue;
                Vector3 target=leg.ankle.position;
                float groundY=contact.point.y+leg.sole;
                // An action may deliberately lift a foot. Preserve its authored
                // height above the neutral root/sole plane when adapting to sand.
                bool action=CurrentAction=="Melee"||CurrentAction=="Shoot"||CurrentAction=="Hit";
                float actionLift=Mathf.Max(0,leg.ankle.position.y-transform.position.y-leg.sole);
                if(action&&actionLift>.06f)groundY+=actionLift;
                float[] contacts=leg.side=="L"?cycle?.leftContacts:cycle?.rightContacts;
                bool plantedPhase=false,footfall=false;
                if(contacts!=null)foreach(float phase in contacts)
                {
                    plantedPhase|=Mathf.Repeat(cycleTime-phase,1)<cycle.stanceFraction;
                    footfall|=Mathf.FloorToInt(cycleTime-phase)>Mathf.FloorToInt(previousContactTime-phase);
                }
                if(cycle!=null && plantedPhase)
                {
                    if(!leg.planted){leg.plantPosition=contact.point;leg.planted=true;}
                    // Limit locking during a sharp steering correction; the next
                    // authored contact establishes a fresh world-space support.
                    Vector3 offset=leg.plantPosition-contact.point;offset.y=0;
                    if(offset.magnitude<.32f && DemoScene.TryGround(leg.plantPosition,out var anchor))
                    {target=anchor.point+Vector3.up*leg.sole;contact=anchor;groundY=target.y;}
                }
                else leg.planted=false;
                // Preserve airborne run feet; support planted feet and idle stance on dune slopes.
                if(IsMoving && !plantedPhase && target.y>groundY+.06f) continue;
                target.y=Mathf.Clamp(groundY, target.y-.27f, target.y+.27f);
                Quaternion animatedFoot=leg.ankle.rotation;
                SolveLeg(leg,target);
                // Bone-local Y points along the bone, not necessarily out of the sole.
                // Preserve the authored foot orientation and add only terrain tilt.
                var tilt=Quaternion.FromToRotation(Vector3.up,contact.normal);
                leg.ankle.rotation=Quaternion.Slerp(animatedFoot,tilt*animatedFoot,.8f);
                if(footfall && travelSpeed>.05f)FootContact?.Invoke(this,contact.point,contact.normal);
            }
            previousContactTime=cycleTime;
        }
        static void SolveLeg(Leg leg, Vector3 target)
        {
            Vector3 root=leg.hip.position, knee=leg.knee.position, ankle=leg.ankle.position;
            float upper=Vector3.Distance(root,knee), lower=Vector3.Distance(knee,ankle);
            Vector3 direction=target-root;
            float distance=Mathf.Clamp(direction.magnitude,.001f,upper+lower-.001f);
            direction.Normalize();
            Vector3 bend=knee-root-Vector3.Dot(knee-root,direction)*direction;
            if(bend.sqrMagnitude<.00001f) bend=Vector3.Cross(direction,leg.hip.right);
            bend.Normalize();
            float along=(upper*upper-lower*lower+distance*distance)/(2*distance);
            float height=Mathf.Sqrt(Mathf.Max(0,upper*upper-along*along));
            Vector3 desiredKnee=root+direction*along+bend*height;
            leg.hip.rotation=Quaternion.FromToRotation(knee-root,desiredKnee-root)*leg.hip.rotation;
            leg.knee.rotation=Quaternion.FromToRotation(leg.ankle.position-leg.knee.position,target-leg.knee.position)*leg.knee.rotation;
        }
    }
}
