#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "KKBenchmarkGameMode.generated.h"
class UKKBenchmarkAssets;
class AKKBenchmarkUnit;
class AStaticMeshActor;
class ASkyLight;
UCLASS()
class KRAGKINGSBENCHMARK_API AKKBenchmarkGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AKKBenchmarkGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<UKKBenchmarkAssets> AssetSet;
    UPROPERTY() TObjectPtr<AStaticMeshActor> TerrainActor;
    UPROPERTY() TObjectPtr<ASkyLight> SkyLightActor;
    bool bLightingDiagnosticsWritten=false;
    void WriteLightingDiagnostics();
    bool TryStartDemo();
    bool bWaitingForTerrain=false;
    bool bWindowTitleApplied=false;
    bool bReviewFrameWritten=false;
    bool bSkinReview=false;
    bool bGroundBounceReview=false;
    FLinearColor GroundBounceRadiance=FLinearColor::Black;
    bool bSkinReviewAwaitingCapture=false;
    int32 SkinReviewIndex=0;
    double SkinReviewNextTime=16.0;
    FString SkinReviewOutput;
    void TickSkinReview();
    double TerrainWaitStarted=0.0;
    TArray<float> FrameTimes;
    float Elapsed=0;
    double BenchmarkStartTime=0.0;
    double LastFrameTime=0.0;
    bool bSavedMetrics=false;
    void WriteMetrics();
    void TickSmoke();
    void TickMovingWorkload(double WallElapsed);
    void WriteInputState();
    void TickShowcase();
    void BeginShowcaseRecording();
    void FinishShowcaseRecording();
    void SmokeCheck(bool bPass,const FString& Name);
    UPROPERTY() TArray<TObjectPtr<AKKBenchmarkUnit>> DemoUnits;
    bool bSmoke=false;
    bool bPerformancePass=false;
    bool bPerformanceMoving=false;
    FName RequestedSkinMode=TEXT("Generic");
    int32 PerformanceWorkloadCycle=INDEX_NONE;
    int32 PerformanceWorkloadPhase=0;
    FVector PerformanceOrigins[2]={FVector::ZeroVector,FVector::ZeroVector};
    bool bInputState=false;
    bool bShowcase=false;
    bool bShowcaseWaiting=false;
    bool bShowcaseReady=false;
    bool bShowcaseComplete=false;
    bool bShowcaseAudioRecording=false;
    int32 ShowcasePreviousNeverDisableSubmixes=INDEX_NONE;
    int32 ShowcasePhase=0;
    double ShowcaseStartTime=0.0;
    FString ShowcaseGate;
    float NextInputStateTime=0.f;
    int32 SmokePhase=0;
    int32 SmokeFailures=0;
    float NextSmokeTime=5;
    FVector SmokeMoveStart=FVector::ZeroVector;
    FString SmokeResults;
};
UCLASS()
class KRAGKINGSBENCHMARK_API AKKBenchmarkHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
