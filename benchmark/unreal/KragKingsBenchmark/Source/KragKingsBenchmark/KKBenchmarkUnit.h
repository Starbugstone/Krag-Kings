#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "KKBenchmarkAssets.h"
#include "KKBenchmarkUnit.generated.h"
class USoundAttenuation;

UCLASS()
class KRAGKINGSBENCHMARK_API AKKBenchmarkUnit : public ACharacter
{
    GENERATED_BODY()
public:
    AKKBenchmarkUnit();
    virtual void Tick(float DeltaSeconds) override;
    void InitializeUnit(UKKBenchmarkAssets* Assets, bool bIsKrag);
    void MoveTo(const FVector& Destination,bool bWalk=false);
    void PlayDemoAction(const FName& Action);
    void PlayFacePerformance();
    UFUNCTION(BlueprintImplementableEvent,Category="Presentation")
    void OnFootstepImpact(FName Foot,FVector Location,FVector SurfaceNormal,float Strength,bool bIsWalking);
    void CycleVariant();
    void SetVariantIndex(int32 Index);
    void SetSelected(bool bNewSelected) { bSelected = bNewSelected; }
    FString GetVariantLabel() const;
    FString GetActionLabel() const { return CurrentAction.ToString(); }
    bool IsKrag() const { return bKrag; }
    bool HasMovementTarget() const { return bMoving; }
    bool IsFaceActing() const { return FaceTimeRemaining>0.f; }
    float GetMaximumAppliedMorphWeight(const FName& Kind) const;
private:
    void ApplyVariant();
    void PlayLocomotion(bool bRunning);
    const FKKCharacterVariant* Variant() const;
    UPROPERTY() TObjectPtr<UKKBenchmarkAssets> AssetSet;
    int32 VariantIndex = 0;
    bool bKrag = true;
    bool bSelected = false;
    bool bMoving = false;
    bool bWasRunning = false;
    bool bWalking = false;
    float FootContactCooldown[2] = {0.f,0.f};
    float PreviousContactPhase=.99f;
    int32 FootSoundIndex=0;
    UPROPERTY() TObjectPtr<USoundAttenuation> FootstepAttenuation;
    UPROPERTY() TObjectPtr<USoundAttenuation> ActionAttenuation;
    FVector MoveTarget = FVector::ZeroVector;
    FName CurrentAction = "Idle";
    float ActionTimeRemaining = 0;
    float ActionDuration = 0;
    int32 NextFireContact=0;
    bool bHitSoundPending=false;
    float FaceTimeRemaining = 0;
    void UpdateFootContacts(float DeltaSeconds);
    void EmitShot();
    void EmitHitSound();
};
