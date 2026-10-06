#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "KKBenchmarkAssets.h"
#include "KKBenchmarkAnimInstance.generated.h"
class UAnimSequence;

/** Shared skeletal animation graph with short crossfades and authored in-place clips. */
UCLASS(Transient)
class KRAGKINGSBENCHMARK_API UKKBenchmarkAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void Configure(UAnimSequence* InIdle,UAnimSequence* InWalk,UAnimSequence* InRun);
    void SetRunning(bool bInRunning,bool bInWalking=false) { bRunning=bInRunning; bWalking=bInWalking; bActionActive=false; }
    void PlayAction(UAnimSequence* InAction) { ActionClip=InAction;bRunning=false;bActionActive=true;++ActionSerial; }
    void PlayFace(UAnimSequence* InFace) { FaceClip=InFace;bFaceActive=true;++FaceSerial; }
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> RunClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActionClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> FaceClip;
    UPROPERTY(Transient) TArray<FKKMorphDriver> MorphDrivers;
    bool bRunning=false;
    bool bWalking=false;
    bool bActionActive=false;
    bool bFaceActive=false;
    uint32 ActionSerial=0;
    uint32 FaceSerial=0;
    float LocomotionSpeedRatio=1.f;
    float WalkCycleSeconds=0.f;
    float RunCycleSeconds=0.f;
    float WalkStanceFraction=.62f;
    float RunStanceFraction=.42f;
    TArray<float> WalkLeftContacts,WalkRightContacts,RunLeftContacts,RunRightContacts;
    float LocomotionPhase=0.f;
    uint32 LocomotionSerial=0;
    bool bLocomotionPhaseRunning=false,bLocomotionPhaseWalking=false;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;
};
