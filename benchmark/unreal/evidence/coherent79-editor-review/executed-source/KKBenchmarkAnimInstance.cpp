#include "KKBenchmarkAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNode_SequencePlayer.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "AnimNodes/AnimNode_LayeredBoneBlend.h"
#include "BoneControllers/AnimNode_TwoBoneIK.h"
#include "BoneControllers/AnimNode_ModifyBone.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

/** Portable bind-relative corrective curves, evaluated from this frame's final local pose. */
struct FKKMorphCurveNode : FAnimNode_Base
{
    FPoseLink Source;
    TArray<FKKMorphDriver> Drivers;
    FTransform MeshToWorld=FTransform::Identity;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override {Source.Initialize(Context);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override {Source.CacheBones(Context);}
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override {Source.Update(Context);}
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);
        const FBoneContainer& Bones=Output.Pose.GetBoneContainer();
        for(const auto& Driver:Drivers)
        {
            const int32 MeshIndex=Bones.GetReferenceSkeleton().FindBoneIndex(Driver.Bone);
            if(MeshIndex==INDEX_NONE)continue;
            const FCompactPoseBoneIndex Bone=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
            if(Bone.GetInt()==INDEX_NONE)continue;
            const FTransform& Current=Output.Pose[Bone];
            const FTransform& Bind=Bones.GetRefPoseTransform(Bone);
            float Value=0.f;
            if(Driver.Channel==TEXT("rotationMagnitudeDegrees"))Value=FMath::RadiansToDegrees(Current.GetRotation().AngularDistance(Bind.GetRotation()));
            else if(Driver.Channel==TEXT("translationDistanceMeters"))
            {
                // A bone translation is measured in its parent's space. FBX may
                // retain scale on the armature/root, so include the full chain
                // and component scale before converting world centimeters to meters.
                FVector Delta=Current.GetLocation()-Bind.GetLocation();
                for(FCompactPoseBoneIndex Parent=Bones.GetParentBoneIndex(Bone);Parent.GetInt()!=INDEX_NONE;Parent=Bones.GetParentBoneIndex(Parent))
                    Delta=Output.Pose[Parent].TransformVector(Delta);
                Value=MeshToWorld.TransformVector(Delta).Size()*.01f;
            }
            else continue;
            const float Weight=FMath::Clamp((Value-Driver.Start)/FMath::Max(.000001f,Driver.End-Driver.Start),0.f,1.f)*Driver.MaxWeight;
            Output.Curve.Set(Driver.Morph,Weight);
        }
    }
};

/** Preserve authored action lift from this frame's pre-IK pose, not last frame's
 * already planted socket position. Terrain queries remain on the game thread. */
struct FKKActionAwareFootIK : FAnimNode_TwoBoneIK
{
    bool bPreserveActionLift=false;
    float RootFeetWorldZ=0.f,BindAnkleHeight=0.f;
    FVector GroundPoint=FVector::ZeroVector,GroundNormal=FVector::UpVector;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& OutBoneTransforms) override
    {
        if(bPreserveActionLift)
        {
            const FCompactPoseBoneIndex Foot=IKBone.GetCompactPoseIndex(Output.Pose.GetPose().GetBoneContainer());
            if(Foot.GetInt()!=INDEX_NONE)
            {
                const FVector AnimatedFoot=Output.AnimInstanceProxy->GetComponentTransform().TransformPosition(Output.Pose.GetComponentSpaceTransform(Foot).GetLocation());
                const float Lift=FMath::Max(0.f,AnimatedFoot.Z-RootFeetWorldZ-BindAnkleHeight);
                const float PlaneZ=GroundPoint.Z-(GroundNormal.X*(AnimatedFoot.X-GroundPoint.X)+GroundNormal.Y*(AnimatedFoot.Y-GroundPoint.Y))/FMath::Max(.1f,GroundNormal.Z);
                EffectorLocation=AnimatedFoot;
                EffectorLocation.Z=FMath::Clamp(PlaneZ+BindAnkleHeight+(Lift>6.f?Lift:0.f),AnimatedFoot.Z-27.f,AnimatedFoot.Z+27.f);
            }
        }
        FAnimNode_TwoBoneIK::EvaluateSkeletalControl_AnyThread(Output,OutBoneTransforms);
    }
};

/** Game-thread input copy, with the graph evaluated by Unreal's animation scheduler. */
struct FKKBenchmarkAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequencePlayer_Standalone IdlePlayer,RunPlayer,ActionPlayer,FacePlayer;
    FAnimNode_TwoWayBlend LocomotionBlend,ActionBlend;
    FAnimNode_LayeredBoneBlend FaceLayer;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FKKActionAwareFootIK LeftFootIK,RightFootIK;
    FAnimNode_ModifyBone LeftFootTilt,RightFootTilt;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    FKKMorphCurveNode MorphCurves;
    FVector FootTargets[2]={FVector::ZeroVector,FVector::ZeroVector};
    FVector KneeTargets[2]={FVector::ZeroVector,FVector::ZeroVector};
    float FootAlphas[2]={0,0};
    bool bFeetPlanted[2]={false,false};
    FVector PlantLocations[2]={FVector::ZeroVector,FVector::ZeroVector};
    FRotator GroundTilts[2]={FRotator::ZeroRotator,FRotator::ZeroRotator};
    bool bRunning=false,bPreviousWalking=false,bActionActive=false,bFaceActive=false;
    uint32 LastActionSerial=0;
    uint32 LastFaceSerial=0;
    uint32 LastIdleInitializationSerial=~0u;
    explicit FKKBenchmarkAnimProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        IdlePlayer.SetLoopAnimation(true);RunPlayer.SetLoopAnimation(true);ActionPlayer.SetLoopAnimation(false);
        FacePlayer.SetLoopAnimation(false);
        LocomotionBlend.A.SetLinkNode(&IdlePlayer);LocomotionBlend.B.SetLinkNode(&RunPlayer);
        ActionBlend.A.SetLinkNode(&LocomotionBlend);ActionBlend.B.SetLinkNode(&ActionPlayer);
        LocomotionBlend.Alpha=0;ActionBlend.Alpha=0;
        FaceLayer.BasePose.SetLinkNode(&ActionBlend);
        FaceLayer.AddPose();FaceLayer.BlendPoses[0].SetLinkNode(&FacePlayer);
        FBranchFilter FacialBranch;FacialBranch.BoneName=TEXT("FaceRoot");FacialBranch.BlendDepth=0;
        FaceLayer.LayerSetup[0].BranchFilters.Add(FacialBranch);
        FaceLayer.BlendWeights[0]=0.f;
        FaceLayer.CurveBlendOption=ECurveBlendOption::UseMaxValue;
        ToComponent.LocalPose.SetLinkNode(&FaceLayer);
        LeftFootIK.ComponentPose.SetLinkNode(&ToComponent);
        RightFootIK.ComponentPose.SetLinkNode(&LeftFootIK);
        LeftFootTilt.ComponentPose.SetLinkNode(&RightFootIK);
        RightFootTilt.ComponentPose.SetLinkNode(&LeftFootTilt);
        ToLocal.ComponentPose.SetLinkNode(&RightFootTilt);
        LeftFootTilt.BoneToModify.BoneName=TEXT("Foot_L");RightFootTilt.BoneToModify.BoneName=TEXT("Foot_R");
        for(auto* Tilt:{&LeftFootTilt,&RightFootTilt})
        {
            Tilt->RotationMode=BMM_Additive;Tilt->RotationSpace=BCS_WorldSpace;Tilt->Alpha=0.f;
        }
        MorphCurves.Source.SetLinkNode(&ToLocal);
        LeftFootIK.IKBone.BoneName=TEXT("Foot_L");RightFootIK.IKBone.BoneName=TEXT("Foot_R");
        for(auto* Node:{&LeftFootIK,&RightFootIK})
        {
            Node->EffectorTarget.BoneReference.BoneName=Node->IKBone.BoneName;
            Node->JointTarget.BoneReference.BoneName=Node->IKBone.BoneName;
            Node->EffectorLocationSpace=BCS_WorldSpace;
            Node->JointTargetLocationSpace=BCS_WorldSpace;
            Node->bAllowStretching=false;
            Node->bTakeRotationFromEffectorSpace=false;
            Node->bMaintainEffectorRelRot=true;
            Node->Alpha=0;
        }
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &MorphCurves; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& OutNodes) override
    {
        OutNodes.Add(&IdlePlayer);OutNodes.Add(&RunPlayer);OutNodes.Add(&ActionPlayer);OutNodes.Add(&FacePlayer);
        OutNodes.Add(&LocomotionBlend);OutNodes.Add(&ActionBlend);OutNodes.Add(&FaceLayer);
        OutNodes.Add(&ToComponent);OutNodes.Add(&LeftFootIK);OutNodes.Add(&RightFootIK);OutNodes.Add(&ToLocal);
        OutNodes.Add(&LeftFootTilt);OutNodes.Add(&RightFootTilt);
        OutNodes.Add(&MorphCurves);
    }
    virtual void PreUpdate(UAnimInstance* Instance,float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,DeltaSeconds);
        auto* Anim=CastChecked<UKKBenchmarkAnimInstance>(Instance);
        MorphCurves.Drivers=Anim->MorphDrivers;
        MorphCurves.MeshToWorld=GetComponentTransform();
        const bool bEnteringIdle=!Anim->bRunning && !Anim->bActionActive && (bRunning || bActionActive);
        const bool bInitializeIdle=LastIdleInitializationSerial!=Anim->IdleInitializationSerial || IdlePlayer.GetSequence()!=Anim->IdleClip.Get() || bEnteringIdle;
        IdlePlayer.SetSequence(Anim->IdleClip);
        if(bInitializeIdle && Anim->IdleClip)
        {
            // Seek once on configuration/Idle entry, never on continuous Idle.
            // StartPosition also survives initial graph-node initialization.
            const float Time=Anim->IdleInitialPhase*Anim->IdleClip->GetPlayLength();
            IdlePlayer.SetStartPosition(Time);IdlePlayer.SetAccumulatedTime(Time);
            LastIdleInitializationSerial=Anim->IdleInitializationSerial;
        }
        const UAnimSequence* PreviousMovingClip=Cast<UAnimSequence>(RunPlayer.GetSequence());
        const float PreviousPhase=PreviousMovingClip && PreviousMovingClip->GetPlayLength()>0.f?FMath::Frac(RunPlayer.GetAccumulatedTime()/PreviousMovingClip->GetPlayLength()):0.f;
        const UAnimSequence* MovingClip=Anim->bWalking && Anim->WalkClip?Anim->WalkClip.Get():Anim->RunClip.Get();
        RunPlayer.SetSequence(Anim->bWalking && Anim->WalkClip?Anim->WalkClip.Get():Anim->RunClip.Get());
        if(Anim->bRunning && (!bRunning || bPreviousWalking!=Anim->bWalking))
        {
            float Phase=0.f;
            if(bRunning)
            {
                const TArray<float>& OldLeft=bPreviousWalking?Anim->WalkLeftContacts:Anim->RunLeftContacts;
                const TArray<float>& NewLeft=Anim->bWalking?Anim->WalkLeftContacts:Anim->RunLeftContacts;
                Phase=FMath::Frac(PreviousPhase-(OldLeft.Num()?OldLeft[0]:0.f)+(NewLeft.Num()?NewLeft[0]:0.f)+1.f);
            }
            RunPlayer.SetAccumulatedTime(Phase*(MovingClip?MovingClip->GetPlayLength():0.f));
            Anim->LocomotionPhase=Phase;++Anim->LocomotionSerial;
            Anim->bLocomotionPhaseRunning=true;Anim->bLocomotionPhaseWalking=Anim->bWalking;
            bFeetPlanted[0]=bFeetPlanted[1]=false;
        }
        const float CycleSeconds=Anim->bWalking?Anim->WalkCycleSeconds:Anim->RunCycleSeconds;
        const float CycleRate=MovingClip && CycleSeconds>0.f?MovingClip->GetPlayLength()/CycleSeconds:1.f;
        RunPlayer.SetPlayRate(Anim->LocomotionSpeedRatio*CycleRate);
        ActionPlayer.SetSequence(Anim->ActionClip?Anim->ActionClip.Get():Anim->IdleClip.Get());
        FacePlayer.SetSequence(Anim->FaceClip?Anim->FaceClip.Get():Anim->IdleClip.Get());
        bRunning=Anim->bRunning;bPreviousWalking=Anim->bWalking;bActionActive=Anim->bActionActive;
        bFaceActive=Anim->bFaceActive && Anim->FaceClip;
        USkeletalMeshComponent* Mesh=Instance->GetSkelMeshComponent();
        if(Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetWorld())
        {
            const FReferenceSkeleton& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
            const FName Feet[2]={TEXT("Foot_L"),TEXT("Foot_R")};
            for(int32 i=0;i<2;i++)
            {
                auto& FootIK=i==0?LeftFootIK:RightFootIK;
                FootIK.bPreserveActionLift=false;
                FootAlphas[i]=0;
                int32 BoneIndex=Ref.FindBoneIndex(Feet[i]);
                if(BoneIndex==INDEX_NONE) continue;
                FTransform RefTransform=Ref.GetRefBonePose()[BoneIndex];
                for(int32 Parent=Ref.GetParentIndex(BoneIndex);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent)) RefTransform=RefTransform*Ref.GetRefBonePose()[Parent];
                const FVector FootWorld=Mesh->GetSocketLocation(Feet[i]);
                FHitResult Ground;FCollisionQueryParams Params;Params.AddIgnoredActor(Mesh->GetOwner());
                if(!Mesh->GetWorld()->LineTraceSingleByObjectType(Ground,FootWorld+FVector(0,0,90),FootWorld-FVector(0,0,140),FCollisionObjectQueryParams(ECC_WorldStatic),Params))continue;
                const float RefZ=RefTransform.GetLocation().Z;
                const float SoleZ=Mesh->GetSkeletalMeshAsset()->GetBounds().Origin.Z-Mesh->GetSkeletalMeshAsset()->GetBounds().BoxExtent.Z;
                const float AnkleOffset=FMath::Max(3.f,RefZ-SoleZ);
                FootIK.bPreserveActionLift=bActionActive || ActionBlend.Alpha>.01f;
                FootIK.RootFeetWorldZ=Mesh->GetComponentTransform().TransformPosition(FVector(0,0,SoleZ)).Z;
                FootIK.BindAnkleHeight=Mesh->GetComponentTransform().TransformVector(FVector(0,0,RefZ-SoleZ)).Size();
                FootIK.GroundPoint=Ground.ImpactPoint;FootIK.GroundNormal=Ground.ImpactNormal;
                const float Stance=Anim->bWalking?Anim->WalkStanceFraction:Anim->RunStanceFraction;
                const TArray<float>& Contacts=Anim->bWalking?(i==0?Anim->WalkLeftContacts:Anim->WalkRightContacts):(i==0?Anim->RunLeftContacts:Anim->RunRightContacts);
                bool bStance=false;float StanceAlpha=0.f;
                if(bRunning)for(float Contact:Contacts)
                {
                    const float Phase=FMath::Frac(Anim->LocomotionPhase-Contact+1.f);
                    if(Phase>=Stance)continue;
                    bStance=true;
                    StanceAlpha=FMath::Max(StanceAlpha,FMath::Min(FMath::Clamp(Phase/.06f,0.f,1.f),FMath::Clamp((Stance-Phase)/.08f,0.f,1.f)));
                }
                const FVector ContactTarget=Ground.ImpactPoint+Ground.ImpactNormal*(AnkleOffset+1.f);
                if(bStance && !bFeetPlanted[i])PlantLocations[i]=ContactTarget;
                if(!bStance || !bFeetPlanted[i])GroundTilts[i]=FQuat::FindBetweenNormals(FVector::UpVector,Ground.ImpactNormal).Rotator();
                bFeetPlanted[i]=bStance;
                const float Alpha=bRunning?(bStance?StanceAlpha:0.f):1.f;
                FootTargets[i]=bStance?PlantLocations[i]:ContactTarget;
                KneeTargets[i]=FootWorld+Mesh->GetOwner()->GetActorForwardVector()*80.f+FVector(0,0,60);
                FootAlphas[i]=Alpha;
            }
        }
        if(LastActionSerial!=Anim->ActionSerial)
        {
            ActionPlayer.SetAccumulatedTime(0.f);
            LastActionSerial=Anim->ActionSerial;
        }
        if(LastFaceSerial!=Anim->FaceSerial)
        {
            FacePlayer.SetAccumulatedTime(0.f);LastFaceSerial=Anim->FaceSerial;
        }
    }
    virtual void PostUpdate(UAnimInstance* Instance) const override
    {
        FAnimInstanceProxy::PostUpdate(Instance);
        auto* Anim=CastChecked<UKKBenchmarkAnimInstance>(Instance);
        const UAnimSequence* Clip=Cast<UAnimSequence>(RunPlayer.GetSequence());
        if(Clip && Clip->GetPlayLength()>0.f)Anim->LocomotionPhase=FMath::Fmod(RunPlayer.GetAccumulatedTime()/Clip->GetPlayLength(),1.f);
        Anim->bLocomotionPhaseRunning=bRunning;Anim->bLocomotionPhaseWalking=bPreviousWalking;
    }
    virtual void Update(float DeltaSeconds) override
    {
        FAnimInstanceProxy::Update(DeltaSeconds);
        LocomotionBlend.Alpha=FMath::FInterpConstantTo(LocomotionBlend.Alpha,bRunning?1.f:0.f,DeltaSeconds,1.f/.16f);
        ActionBlend.Alpha=FMath::FInterpConstantTo(ActionBlend.Alpha,bActionActive?1.f:0.f,DeltaSeconds,1.f/.10f);
        FaceLayer.BlendWeights[0]=FMath::FInterpConstantTo(FaceLayer.BlendWeights[0],bFaceActive?1.f:0.f,DeltaSeconds,5.f);
        FAnimNode_TwoBoneIK* Feet[2]={&LeftFootIK,&RightFootIK};
        FAnimNode_ModifyBone* Tilts[2]={&LeftFootTilt,&RightFootTilt};
        for(int32 i=0;i<2;i++)
        {
            Feet[i]->EffectorLocation=FootTargets[i];Feet[i]->JointTargetLocation=KneeTargets[i];
            Feet[i]->Alpha=FMath::FInterpTo(Feet[i]->Alpha,FootAlphas[i],DeltaSeconds,12.f);
            Tilts[i]->Rotation=GroundTilts[i];Tilts[i]->Alpha=Feet[i]->Alpha;
        }
    }
};

void UKKBenchmarkAnimInstance::Configure(UAnimSequence* InIdle,UAnimSequence* InWalk,UAnimSequence* InRun,float InIdlePhase)
{
    IdleClip=InIdle;WalkClip=InWalk;RunClip=InRun;ActionClip=InIdle;bRunning=false;bWalking=false;bActionActive=false;bFaceActive=false;
    IdleInitialPhase=FMath::Clamp(InIdlePhase,0.f,.999999f);++IdleInitializationSerial;
}
FAnimInstanceProxy* UKKBenchmarkAnimInstance::CreateAnimInstanceProxy(){return new FKKBenchmarkAnimProxy(this);}
void UKKBenchmarkAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy){delete InProxy;}
