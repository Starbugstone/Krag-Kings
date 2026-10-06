#include "KKBenchmarkUnit.h"
#include "KKBenchmarkAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "DrawDebugHelpers.h"
#include "KKFootDust.h"
#include "KKShotFlash.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Materials/MaterialInterface.h"

AKKBenchmarkUnit::AKKBenchmarkUnit()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(42.f, 110.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    GetMesh()->SetAnimInstanceClass(UKKBenchmarkAnimInstance::StaticClass());
    GetMesh()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    GetMesh()->bCastDynamicShadow=true;
    bUseControllerRotationYaw=false;
    GetCharacterMovement()->bOrientRotationToMovement=true;
    GetCharacterMovement()->RotationRate=FRotator(0,540,0);
    GetCharacterMovement()->MaxWalkSpeed=320.f;
    GetCharacterMovement()->MaxAcceleration=1300.f;
    GetCharacterMovement()->BrakingDecelerationWalking=1600.f;
    GetCharacterMovement()->MaxStepHeight=40.f;
    GetCharacterMovement()->SetWalkableFloorAngle(40.f);
    GetCharacterMovement()->bRunPhysicsWithNoController=true;
}

void AKKBenchmarkUnit::InitializeUnit(UKKBenchmarkAssets* Assets, bool bIsKrag)
{
    AssetSet=Assets; bKrag=bIsKrag;
    bShotDiagnostics=FParse::Param(FCommandLine::Get(),TEXT("KKInputState")) || FParse::Param(FCommandLine::Get(),TEXT("KKSmoke"));
    GetCharacterMovement()->MaxWalkSpeed=bKrag?320.f:270.f;
    GetCharacterMovement()->RotationRate=FRotator(0,bKrag?300.f:720.f,0);
    GetCharacterMovement()->MaxAcceleration=bKrag?700.f:1200.f;
    GetCharacterMovement()->BrakingDecelerationWalking=bKrag?700.f:1200.f;
    FootstepAttenuation=NewObject<USoundAttenuation>(this);
    FootstepAttenuation->Attenuation.bAttenuate=true;
    FootstepAttenuation->Attenuation.AttenuationShape=EAttenuationShape::Sphere;
    FootstepAttenuation->Attenuation.AttenuationShapeExtents=FVector(100.f);
    FootstepAttenuation->Attenuation.FalloffDistance=2400.f;
    ActionAttenuation=NewObject<USoundAttenuation>(this);
    ActionAttenuation->Attenuation.bAttenuate=true;
    ActionAttenuation->Attenuation.bSpatialize=true;
    ActionAttenuation->Attenuation.DistanceAlgorithm=EAttenuationDistanceModel::Linear;
    ActionAttenuation->Attenuation.AttenuationShape=EAttenuationShape::Sphere;
    ActionAttenuation->Attenuation.AttenuationShapeExtents=FVector(400.f);
    ActionAttenuation->Attenuation.FalloffDistance=5600.f;
    VariantIndex=0;
    ApplyVariant();
}

const FKKCharacterVariant* AKKBenchmarkUnit::Variant() const
{
    if(!AssetSet) return nullptr;
    const auto& Variants=bKrag?AssetSet->Krags:AssetSet->Nibs;
    return Variants.IsValidIndex(VariantIndex)?&Variants[VariantIndex]:nullptr;
}

void AKKBenchmarkUnit::ApplyVariant()
{
    const FKKCharacterVariant* V=Variant();
    if(!V || !V->Mesh) { UE_LOG(LogTemp,Error,TEXT("KK_ASSET_MISSING character variant %d"),VariantIndex); return; }
    bMoving=false;bWalking=false;
    GetCharacterMovement()->StopMovementImmediately();
    PreviousContactPhase=.99f;FootContactCooldown[0]=FootContactCooldown[1]=0.f;
    const float OldHalf=GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    GetMesh()->SetSkeletalMesh(V->Mesh);
    if(!SetSkinMode(SkinMode))UE_LOG(LogTemp,Error,TEXT("KK_SKIN_AB_FAILED variant=%s"),*V->Id);
    GetMesh()->SetAnimInstanceClass(UKKBenchmarkAnimInstance::StaticClass());
    if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance()))
    {
        Anim->Configure(V->Idle,V->Walk,V->Run);Anim->MorphDrivers=V->MorphDrivers;
        Anim->WalkCycleSeconds=V->WalkCycleSeconds;Anim->RunCycleSeconds=V->RunCycleSeconds;
        Anim->WalkStanceFraction=V->WalkStanceFraction;Anim->RunStanceFraction=V->RunStanceFraction;
    }
    GetMesh()->SetRelativeRotation(AssetSet->MeshRotation);
    const FBoxSphereBounds B=V->Mesh->GetBounds();
    const float Half=FMath::Max(45.f,B.BoxExtent.Z);
    const float Radius=bKrag?47.f:29.f;
    GetCapsuleComponent()->SetCapsuleSize(Radius,Half,true);
    AddActorWorldOffset(FVector(0,0,Half-OldHalf),false);
    GetMesh()->SetRelativeLocation(FVector(0,0,-Half-(B.Origin.Z-B.BoxExtent.Z)));
    CurrentAction="Idle";ActionDuration=0;NextFireContact=0;bHitSoundPending=false;ActionTimeRemaining=0;FaceTimeRemaining=0; bWasRunning=false;
    PlayLocomotion(false);
    UE_LOG(LogTemp,Display,TEXT("KK_VARIANT species=%s id=%s height_cm=%.2f"),bKrag?TEXT("Krag"):TEXT("Nib"),*V->Id,Half*2);
}

bool AKKBenchmarkUnit::SetSkinMode(FName Mode)
{
    if(Mode!=TEXT("Generic") && Mode!=TEXT("DefaultLit") && Mode!=TEXT("Profile"))return false;
    const FKKCharacterVariant* V=Variant();if(!V || !V->Mesh || !AssetSet)return false;
    const auto* Overrides=Mode==TEXT("Profile")?&AssetSet->SkinProfile:Mode==TEXT("DefaultLit")?&AssetSet->SkinDefaultLit:nullptr;
    if(Overrides && Overrides->IsEmpty())return false;
    TArray<TPair<int32,UMaterialInterface*>> Pending;
    if(Overrides)
    {
        const auto& Slots=V->Mesh->GetMaterials();
        for(int32 Index=0;Index<Slots.Num();++Index)
        {
            UMaterialInterface* Original=Slots[Index].MaterialInterface;
            if(!Original)continue;
            if(const auto* Alternative=Overrides->Find(Original->GetFName()))
            {
                if(!Alternative->Get())return false;
                Pending.Emplace(Index,Alternative->Get());
            }
            else if(Original->GetShadingModels().HasShadingModel(MSM_Subsurface))return false;
        }
        if(Pending.IsEmpty())return false;
    }
    GetMesh()->EmptyOverrideMaterials();
    for(const auto& Override:Pending)GetMesh()->SetMaterial(Override.Key,Override.Value);
    SkinMode=Mode;
    UE_LOG(LogTemp,Display,TEXT("KK_SKIN_MODE species=%s mode=%s overrides=%d"),bKrag?TEXT("Krag"):TEXT("Nib"),*Mode.ToString(),Pending.Num());
    return true;
}

void AKKBenchmarkUnit::CycleVariant()
{
    if(!AssetSet) return;
    const int32 Count=bKrag?AssetSet->Krags.Num():AssetSet->Nibs.Num();
    if(Count==0) return;
    VariantIndex=(VariantIndex+1)%Count;
    ApplyVariant();
}
void AKKBenchmarkUnit::SetVariantIndex(int32 Index)
{
    if(!AssetSet)return;
    const int32 Count=bKrag?AssetSet->Krags.Num():AssetSet->Nibs.Num();if(!Count)return;
    VariantIndex=FMath::Clamp(Index,0,Count-1);ApplyVariant();
}

FString AKKBenchmarkUnit::GetVariantLabel() const
{
    const auto* V=Variant();
    return V?V->Label:TEXT("MISSING CHARACTER ASSET");
}

float AKKBenchmarkUnit::GetMaximumAppliedMorphWeight(const FName& Kind) const
{
    const auto* V=Variant();const auto* SkinnedComponent=GetMesh();
    if(!V || !SkinnedComponent || !SkinnedComponent->GetSkeletalMeshAsset())return 0.f;
    float Maximum=0.f;
    const auto& Indices=SkinnedComponent->GetSkeletalMeshAsset()->GetMorphTargetIndexMap();
    for(const auto& Driver:V->MorphDrivers)
        if(Driver.Kind==Kind)
            if(const int32* Index=Indices.Find(Driver.Morph);Index && SkinnedComponent->MorphTargetWeights.IsValidIndex(*Index))
                Maximum=FMath::Max(Maximum,FMath::Abs(SkinnedComponent->MorphTargetWeights[*Index]));
    return Maximum;
}

void AKKBenchmarkUnit::MoveTo(const FVector& Destination,bool bWalk)
{
    if(FMath::Abs(Destination.X)>70000.f || FMath::Abs(Destination.Y)>70000.f)return;
    FHitResult Ground;FCollisionQueryParams Params;Params.AddIgnoredActor(this);
    if(!GetWorld()->LineTraceSingleByObjectType(Ground,FVector(Destination.X,Destination.Y,6000.f),FVector(Destination.X,Destination.Y,-6000.f),FCollisionObjectQueryParams(ECC_WorldStatic),Params)
        || Ground.ImpactNormal.Z<FMath::Cos(FMath::DegreesToRadians(40.f)))return;
    for(TActorIterator<AKKBenchmarkUnit> It(GetWorld());It;++It)
        if(*It!=this && FVector::DistSquared2D(Ground.ImpactPoint,It->GetActorLocation())<FMath::Square(GetCapsuleComponent()->GetScaledCapsuleRadius()+It->GetCapsuleComponent()->GetScaledCapsuleRadius()+2.5f))return;
    bWalking=bWalk;
    const auto* V=Variant();
    GetCharacterMovement()->MaxWalkSpeed=V?100.f*(bWalking?V->WalkSpeedMeters:V->RunSpeedMeters):(bWalking?(bKrag?115.f:90.f):(bKrag?320.f:270.f));
    MoveTarget=Ground.ImpactPoint;
    bMoving=true;
    UE_LOG(LogTemp,Display,TEXT("KK_MOVE species=%s target=%s"),bKrag?TEXT("Krag"):TEXT("Nib"),*MoveTarget.ToString());
}

void AKKBenchmarkUnit::PlayLocomotion(bool bRunning)
{
    const auto* V=Variant();
    if(!V) return;
    UAnimSequence* Clip=bRunning?V->Run.Get():V->Idle.Get();
    if(Clip)
        if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance())) Anim->SetRunning(bRunning,bWalking);
    CurrentAction=bRunning?(bWalking?"Walk":"Run"):"Idle";
    bWasRunning=bRunning;
}

void AKKBenchmarkUnit::PlayFacePerformance()
{
    const auto* V=Variant();
    if(!V || !V->FacePerformance){UE_LOG(LogTemp,Warning,TEXT("KK_FACE_MISSING selected variant has no reviewed FacePerformance clip"));return;}
    FaceTimeRemaining=V->FacePerformance->GetPlayLength();
    if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance()))Anim->PlayFace(V->FacePerformance);
    UE_LOG(LogTemp,Display,TEXT("KK_FACE_START species=%s duration=%.2f"),bKrag?TEXT("Krag"):TEXT("Nib"),FaceTimeRemaining);
}

void AKKBenchmarkUnit::UpdateFootContacts(float DeltaSeconds)
{
    const auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance());const auto* V=Variant();
    if(!Anim || !V)return;
    const float Phase=Anim->LocomotionPhase;
    if(GetVelocity().SizeSquared2D()<225.f){PreviousContactPhase=Phase;return;}
    const FReferenceSkeleton& Ref=GetMesh()->GetSkeletalMeshAsset()->GetRefSkeleton();
    const FName Feet[2]={TEXT("Foot_L"),TEXT("Foot_R")};
    for(int32 i=0;i<2;i++)
    {
        FootContactCooldown[i]=FMath::Max(0.f,FootContactCooldown[i]-DeltaSeconds);
        int32 BoneIndex=Ref.FindBoneIndex(Feet[i]);if(BoneIndex==INDEX_NONE)continue;
        FTransform Rest=Ref.GetRefBonePose()[BoneIndex];
        for(int32 Parent=Ref.GetParentIndex(BoneIndex);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))Rest=Rest*Ref.GetRefBonePose()[Parent];
        const FBoxSphereBounds Bounds=GetMesh()->GetSkeletalMeshAsset()->GetBounds();
        const float AnkleHeight=Rest.GetLocation().Z-(Bounds.Origin.Z-Bounds.BoxExtent.Z);
        const FVector Foot=GetMesh()->GetSocketLocation(Feet[i]);
        FHitResult Ground;FCollisionQueryParams Params;Params.AddIgnoredActor(this);
        if(!GetWorld()->LineTraceSingleByObjectType(Ground,Foot+FVector(0,0,60),Foot-FVector(0,0,120),FCollisionObjectQueryParams(ECC_WorldStatic),Params))continue;
        const float Lift=Foot.Z-Ground.ImpactPoint.Z-AnkleHeight;
        const TArray<float>& Contacts=bWalking?(i==0?V->WalkLeftContacts:V->WalkRightContacts):(i==0?V->RunLeftContacts:V->RunRightContacts);
        bool bContact=false;
        for(float Contact:Contacts)bContact|=Phase>=PreviousContactPhase?(Contact>PreviousContactPhase && Contact<=Phase):(Contact>PreviousContactPhase || Contact<=Phase);
        if(bContact && FMath::Abs(Lift)<10.f && FootContactCooldown[i]<=0.f)
        {
            FootContactCooldown[i]=.15f;
            const float Strength=bKrag?(bWalking?.8f:1.f):(bWalking?.12f:.24f);
            OnFootstepImpact(Feet[i],Ground.ImpactPoint,Ground.ImpactNormal,Strength,bWalking);
            const auto& Sounds=bKrag?AssetSet->KragSandSteps:AssetSet->NibSandSteps;
            if(Sounds.Num())
            {
                const float Pitch=1.f+.01f*((FootSoundIndex%5)-2);
                UGameplayStatics::PlaySoundAtLocation(this,Sounds[FootSoundIndex%Sounds.Num()],Ground.ImpactPoint,bWalking?.8f:1.f,Pitch,0.f,FootstepAttenuation);
                ++FootSoundIndex;
            }
            if(AssetSet->SandDustMaterial)
            {
                auto* Dust=GetWorld()->SpawnActor<AKKFootDust>(Ground.ImpactPoint+Ground.ImpactNormal*3.f,FRotator::ZeroRotator);
                if(Dust)Dust->InitializeDust(AssetSet->SandDustMaterial,bKrag,bWalking,Ground.ImpactNormal);
            }
            UE_LOG(LogTemp,Verbose,TEXT("KK_FOOT_CONTACT species=%s foot=%s strength=%.2f surface=%s"),bKrag?TEXT("Krag"):TEXT("Nib"),*Feet[i].ToString(),Strength,*Ground.ImpactPoint.ToString());
        }
    }
    PreviousContactPhase=Phase;
}

void AKKBenchmarkUnit::PlayDemoAction(const FName& Action)
{
    const auto* V=Variant(); if(!V) return;
    UAnimSequence* Clip=Action=="Melee"?V->Melee.Get():Action=="Shoot"?V->Shoot.Get():Action=="Hit"?V->Hit.Get():nullptr;
    if(!Clip) { UE_LOG(LogTemp,Error,TEXT("KK_ANIMATION_MISSING action=%s"),*Action.ToString()); return; }
    bMoving=false;
    GetCharacterMovement()->StopMovementImmediately();
    CurrentAction=Action;
    ActionTimeRemaining=FMath::Max(.1f,Clip->GetPlayLength());
    ActionDuration=ActionTimeRemaining;NextFireContact=0;
    bHitSoundPending=Action==TEXT("Hit");
    if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance())) Anim->PlayAction(Clip);
    UE_LOG(LogTemp,Display,TEXT("KK_ACTION species=%s action=%s duration=%.2f"),bKrag?TEXT("Krag"):TEXT("Nib"),*Action.ToString(),ActionTimeRemaining);
}

void AKKBenchmarkUnit::EmitShot()
{
    const auto* V=Variant();if(!V || !AssetSet)return;
    if(V->WeaponMuzzleBone.IsNone() || V->WeaponAimBone.IsNone())return;
    const FVector Muzzle=GetMesh()->GetSocketLocation(V->WeaponMuzzleBone);
    const FVector Direction=(GetMesh()->GetSocketLocation(V->WeaponAimBone)-Muzzle).GetSafeNormal();
    if(bShotDiagnostics)
    {
        ++ShotEventCount;LastShotMuzzle=Muzzle;LastShotDirection=Direction;LastShotActorForward=GetActorForwardVector();
        LastShotPhase=FMath::Clamp(1.f-ActionTimeRemaining/FMath::Max(.001f,ActionDuration),0.f,1.f);
        LastShotForwardAngle=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Direction,LastShotActorForward),-1.f,1.f)));
        MaximumShotForwardAngle=FMath::Max(MaximumShotForwardAngle,LastShotForwardAngle);
        const float AuthoredPhase=V->FireTimesNormalized.IsValidIndex(NextFireContact)?V->FireTimesNormalized[NextFireContact]:-1.f;
        const FString Event=FString::Printf(TEXT("{\"event\":%d,\"variant\":\"%s\",\"authored_phase\":%.6f,\"phase\":%.6f,\"angle_degrees\":%.6f,\"muzzle_cm\":[%.6f,%.6f,%.6f],\"direction\":[%.6f,%.6f,%.6f],\"actor_forward\":[%.6f,%.6f,%.6f]}"),
            ShotEventCount,*V->Id,AuthoredPhase,LastShotPhase,LastShotForwardAngle,
            Muzzle.X,Muzzle.Y,Muzzle.Z,Direction.X,Direction.Y,Direction.Z,
            LastShotActorForward.X,LastShotActorForward.Y,LastShotActorForward.Z);
        if(ShotDiagnosticEvents.Num()>=64)ShotDiagnosticEvents.RemoveAt(0);
        ShotDiagnosticEvents.Add(Event);
        UE_LOG(LogTemp,Display,TEXT("KK_SHOT_DIAGNOSTIC species=%s %s"),bKrag?TEXT("Krag"):TEXT("Nib"),*Event);
    }
    if(Direction.IsNearlyZero())return;
    FVector End=Muzzle+Direction*3000.f;FHitResult Hit;FCollisionQueryParams Params;Params.AddIgnoredActor(this);
    if(GetWorld()->LineTraceSingleByObjectType(Hit,Muzzle,End,FCollisionObjectQueryParams(ECC_WorldStatic),Params))End=Hit.ImpactPoint;
    if(USoundBase* Sound=bKrag?AssetSet->KragShot.Get():AssetSet->NibShot.Get())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Muzzle,.55f,1.f,0.f,ActionAttenuation);
    if(AssetSet->WeaponFlashMaterial)
        if(auto* Shot=GetWorld()->SpawnActor<AKKShotFlash>(Muzzle,Direction.Rotation()))Shot->InitializeFlash(AssetSet->WeaponFlashMaterial,Direction,End,bKrag);
    UE_LOG(LogTemp,Verbose,TEXT("KK_SHOT species=%s muzzle=%s direction=%s"),bKrag?TEXT("Krag"):TEXT("Nib"),*Muzzle.ToString(),*Direction.ToString());
}

FString AKKBenchmarkUnit::GetShotDiagnosticsJson() const
{
    return FString::Printf(TEXT("{\"count\":%d,\"phase\":%.6f,\"angle_degrees\":%.6f,\"maximum_angle_degrees\":%.6f,\"muzzle\":[%.6f,%.6f,%.6f],\"direction\":[%.6f,%.6f,%.6f],\"actor_forward\":[%.6f,%.6f,%.6f],\"events\":[%s]}"),
        ShotEventCount,LastShotPhase,LastShotForwardAngle,MaximumShotForwardAngle,
        LastShotMuzzle.X,LastShotMuzzle.Y,LastShotMuzzle.Z,LastShotDirection.X,LastShotDirection.Y,LastShotDirection.Z,
        LastShotActorForward.X,LastShotActorForward.Y,LastShotActorForward.Z,*FString::Join(ShotDiagnosticEvents,TEXT(",")));
}

void AKKBenchmarkUnit::EmitHitSound()
{
    if(!AssetSet)return;
    const FVector Torso=GetActorLocation()+FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()*.2f);
    if(USoundBase* Sound=bKrag?AssetSet->KragHit.Get():AssetSet->NibHit.Get())
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Torso,.6f,1.f,0.f,ActionAttenuation);
}

void AKKBenchmarkUnit::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(FaceTimeRemaining>0.f)
    {
        FaceTimeRemaining-=DeltaSeconds;
        if(FaceTimeRemaining<=0.f)
            if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance()))Anim->bFaceActive=false;
    }
    if(ActionTimeRemaining>0)
    {
        ActionTimeRemaining-=DeltaSeconds;
        const float Phase=FMath::Clamp(1.f-ActionTimeRemaining/FMath::Max(.001f,ActionDuration),0.f,1.f);
        if(CurrentAction==TEXT("Shoot"))
        {
            const auto* V=Variant();
            if(V)while(V->FireTimesNormalized.IsValidIndex(NextFireContact) && Phase>=V->FireTimesNormalized[NextFireContact]){EmitShot();++NextFireContact;}
        }
        if(CurrentAction==TEXT("Hit") && bHitSoundPending && Phase>=.22f){bHitSoundPending=false;EmitHitSound();}
        if(ActionTimeRemaining<=0) PlayLocomotion(false);
    }
    else
    {
        if(bMoving)
        {
            FVector ToTarget=MoveTarget-GetActorLocation(); ToTarget.Z=0;
            if(ToTarget.SizeSquared()<FMath::Square(25.f)) bMoving=false;
            else
            {
                const float DesiredYaw=ToTarget.Rotation().Yaw;
                const float Angle=FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,DesiredYaw));
                if(Angle>70.f)
                {
                    GetCharacterMovement()->StopMovementImmediately();
                    SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(),FRotator(0,DesiredYaw,0),DeltaSeconds,GetCharacterMovement()->RotationRate.Yaw));
                }
                else
                {
                    const auto* V=Variant();
                    const float Nominal=V?100.f*(bWalking?V->WalkSpeedMeters:V->RunSpeedMeters):0.f;
                    const float StopSpeed=FMath::Sqrt(2.f*GetCharacterMovement()->BrakingDecelerationWalking*FMath::Max(0.f,ToTarget.Size()-25.f));
                    GetCharacterMovement()->MaxWalkSpeed=FMath::Min(Nominal,StopSpeed);
                    AddMovementInput(ToTarget.GetSafeNormal(),1.f);
                }
            }
        }
        const bool bRunning=GetVelocity().SizeSquared2D()>FMath::Square(10.f);
        if(bRunning!=bWasRunning || (bRunning && CurrentAction!=(bWalking?FName("Walk"):FName("Run")))) PlayLocomotion(bRunning);
    }
    if(const auto* V=Variant())
        if(auto* Anim=Cast<UKKBenchmarkAnimInstance>(GetMesh()->GetAnimInstance()))
            Anim->LocomotionSpeedRatio=FMath::Clamp(GetVelocity().Size2D()/FMath::Max(1.f,100.f*(bWalking?V->WalkSpeedMeters:V->RunSpeedMeters)),0.f,1.2f);
    if(GetMesh()->GetSkeletalMeshAsset())UpdateFootContacts(DeltaSeconds);
    if(bSelected)
    {
        const FVector Centre=GetActorLocation()-FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        const float Radius=bKrag?83.f:48.f;
        FVector Previous; bool bHavePrevious=false;
        FCollisionQueryParams Params; Params.AddIgnoredActor(this);
        for(int32 i=0;i<=64;++i)
        {
            float Angle=2.f*PI*i/64.f;
            FVector P=Centre+FVector(FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius,0);
            FHitResult Hit;
            if(GetWorld()->LineTraceSingleByObjectType(Hit,P+FVector(0,0,200),P-FVector(0,0,200),FCollisionObjectQueryParams(ECC_WorldStatic),Params)) P.Z=Hit.ImpactPoint.Z+3;
            if(bHavePrevious) DrawDebugLine(GetWorld(),Previous,P,FColor(70,205,189),false,0,0,2.f);
            Previous=P; bHavePrevious=true;
        }
    }
}
