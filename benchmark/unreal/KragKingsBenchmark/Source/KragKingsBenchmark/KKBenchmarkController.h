#pragma once
#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "KKBenchmarkController.generated.h"
class AKKBenchmarkUnit;
class ACameraActor;
UCLASS()
class KRAGKINGSBENCHMARK_API AKKBenchmarkController : public APlayerController
{
    GENERATED_BODY()
public:
    AKKBenchmarkController();
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
    virtual void PlayerTick(float DeltaTime) override;
    AKKBenchmarkUnit* SelectedUnit() const { return Selected; }
    void SelectUnit(AKKBenchmarkUnit* Unit);
    void ResetCamera();
    void FocusPortrait(AKKBenchmarkUnit* Unit);
    void SetShowcaseCamera(const FVector& Target,float InYaw,float InPitch,float InDistance);
    void EndShowcase() { bPerformanceLocked=false; }
    bool IsPortraitView() const { return bPortrait; }
private:
    void SelectAtCursor(); void MoveAtCursor(); void NextUnit();
    void Melee(); void Shoot(); void Hit(); void Variant(); void Quit();
    void FacePerformance();void TogglePortrait();
    void CaptureReview();
    void ZoomIn(); void ZoomOut();
    UPROPERTY() TObjectPtr<AKKBenchmarkUnit> Selected;
    UPROPERTY() TObjectPtr<ACameraActor> BenchmarkCamera;
    FVector Focus=FVector(0,0,150);
    float Distance=640.f;
    float Yaw=75.f;
    float Pitch=-22.f;
    bool bPortrait=false;
    bool bPerformanceLocked=false;
    FVector PortraitPan=FVector::ZeroVector;
};
