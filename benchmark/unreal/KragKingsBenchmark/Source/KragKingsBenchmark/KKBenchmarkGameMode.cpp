#include "KKBenchmarkGameMode.h"
#include "KKBenchmarkAssets.h"
#include "KKBenchmarkUnit.h"
#include "KKBenchmarkController.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Components/DirectionalLightComponent.h"
#include "Engine/SkyLight.h"
#include "Components/SkyLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/Canvas.h"
#include "Engine/World.h"
#include "GameFramework/GameUserSettings.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/DateTime.h"
#include "Misc/EngineVersion.h"
#include "UnrealClient.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformMemory.h"
#include "RHIGlobals.h"
#include "DynamicRHI.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Widgets/SWindow.h"
#include "AudioMixerBlueprintLibrary.h"

AKKBenchmarkGameMode::AKKBenchmarkGameMode()
{
    PlayerControllerClass=AKKBenchmarkController::StaticClass();
    HUDClass=AKKBenchmarkHUD::StaticClass();
    DefaultPawnClass=nullptr;
    PrimaryActorTick.bCanEverTick=true;
}
void AKKBenchmarkGameMode::BeginPlay()
{
    Super::BeginPlay();
    bPerformanceMoving=FParse::Param(FCommandLine::Get(),TEXT("KKPerfMoving"));
    bPerformancePass=bPerformanceMoving || FParse::Param(FCommandLine::Get(),TEXT("KKPerf"));
    bShowcase=!bPerformancePass && FParse::Param(FCommandLine::Get(),TEXT("KKShowcase"));
    bSmoke=!bPerformancePass && !bShowcase && FParse::Param(FCommandLine::Get(),TEXT("KKSmoke"));
    bInputState=!bPerformancePass && !bShowcase && FParse::Param(FCommandLine::Get(),TEXT("KKInputState"));
    if(auto* Settings=UGameUserSettings::GetGameUserSettings())
    {
        Settings->SetFullscreenMode(EWindowMode::WindowedFullscreen);
        Settings->SetScreenResolution(FIntPoint(1920,1080));
        Settings->SetVSyncEnabled(false);Settings->SetFrameRateLimit(0.f);
        Settings->ApplyResolutionSettings(false);
    }
    AssetSet=LoadObject<UKKBenchmarkAssets>(nullptr,TEXT("/Game/Benchmark/DA_Benchmark.DA_Benchmark"));
    if(!AssetSet || !AssetSet->Terrain || AssetSet->Krags.IsEmpty() || AssetSet->Nibs.IsEmpty())
    {
        UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED import shared assets first"));
        if(bSmoke || bPerformancePass)UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
        return;
    }
    if(bPerformancePass)
    {
        if(auto* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("r.ScreenPercentage")))CVar->Set(100.f,ECVF_SetByCode);
        if(auto* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync")))CVar->Set(0,ECVF_SetByCode);
    }
    AStaticMeshActor* Ground=GetWorld()->SpawnActor<AStaticMeshActor>();
    Ground->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Ground->GetStaticMeshComponent()->SetStaticMesh(AssetSet->Terrain);
    Ground->GetStaticMeshComponent()->SetMaterial(0,AssetSet->SandMaterial);
    Ground->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
    Ground->GetStaticMeshComponent()->SetCastShadow(true);
    // Unity Euler(42,-140,0): horizontal Unity X/Z -> Unreal X/-Y.
    auto* Sun=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,2000),FRotator(-42,130,0));
    auto* SunComponent=Cast<UDirectionalLightComponent>(Sun->GetLightComponent());
    SunComponent->SetMobility(EComponentMobility::Movable);
    SunComponent->SetIntensity(55000.f);
    SunComponent->SetLightColor(FLinearColor::White);
    SunComponent->SetAtmosphereSunLight(true);
    SunComponent->SetCastShadows(true);
    SunComponent->SetLightSourceAngle(1.5f);
    auto* Atmosphere=GetWorld()->SpawnActor<ASkyAtmosphere>();
    Atmosphere->GetComponent()->SetRayleighScatteringScale(.75f);
    auto* Sky=GetWorld()->SpawnActor<ASkyLight>();
    Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Sky->GetLightComponent()->SetIntensity(.85f);
    Sky->GetLightComponent()->SetRealTimeCaptureEnabled(true);
    auto* Fog=GetWorld()->SpawnActor<AExponentialHeightFog>();
    Fog->GetComponent()->SetFogDensity(.002f);
    Fog->GetComponent()->SetFogHeightFalloff(.12f);
    auto* PP=GetWorld()->SpawnActor<APostProcessVolume>();
    PP->bUnbound=true;
    PP->Settings.bOverride_AutoExposureMethod=true;
    PP->Settings.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
    PP->Settings.bOverride_AutoExposureBias=true;
    PP->Settings.AutoExposureBias=0.f;
    PP->Settings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;
    PP->Settings.AutoExposureApplyPhysicalCameraExposure=true;
    PP->Settings.bOverride_CameraISO=true;PP->Settings.CameraISO=100.f;
    PP->Settings.bOverride_CameraShutterSpeed=true;PP->Settings.CameraShutterSpeed=125.f;
    PP->Settings.bOverride_DepthOfFieldFstop=true;PP->Settings.DepthOfFieldFstop=7.3f;
    PP->Settings.bOverride_BloomIntensity=true;PP->Settings.BloomIntensity=.15f;
    PP->Settings.bOverride_MotionBlurAmount=true;PP->Settings.MotionBlurAmount=0;
    PP->Settings.bOverride_VignetteIntensity=true;PP->Settings.VignetteIntensity=.16f;
    auto SpawnUnit=[this](bool bKrag,FVector Position)
    {
        FHitResult Hit;
        if(GetWorld()->LineTraceSingleByChannel(Hit,Position+FVector(0,0,3000),Position-FVector(0,0,3000),ECC_Visibility)) Position.Z=Hit.ImpactPoint.Z+112;
        FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Unit=GetWorld()->SpawnActor<AKKBenchmarkUnit>(Position,FRotator(0,-90,0),Params);
        Unit->InitializeUnit(AssetSet,bKrag);
        DemoUnits.Add(Unit);
        return Unit;
    };
    auto* Krag=SpawnUnit(true,FVector(-135,0,0));
    SpawnUnit(false,FVector(120,-10,0));
    for(int32 Index=0;Index<2;++Index)PerformanceOrigins[Index]=DemoUnits[Index]->GetActorLocation();
    if(auto* PC=Cast<AKKBenchmarkController>(UGameplayStatics::GetPlayerController(this,0))){PC->SelectUnit(Krag);PC->ResetCamera();}
    BenchmarkStartTime=LastFrameTime=FPlatformTime::Seconds();
    UE_LOG(LogTemp,Display,TEXT("KK_EVIDENCE_PATH %s"),*FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Benchmark")));
    UE_LOG(LogTemp,Display,TEXT("KK_READY shared dune mesh, two species, keyboard actions and variant swapping"));
    if(GEngine && GEngine->GameViewport && GEngine->GameViewport->GetWindow().IsValid())GEngine->GameViewport->GetWindow()->SetTitle(FText::FromString(TEXT("Krag Kings - Unreal Benchmark")));
    if(bShowcase)
    {
        bShowcaseWaiting=FParse::Param(FCommandLine::Get(),TEXT("KKShowcaseWait"));
        if(!FParse::Value(FCommandLine::Get(),TEXT("KKShowcaseGate="),ShowcaseGate))ShowcaseGate=FPaths::ProjectSavedDir()/TEXT("Benchmark/showcase-start.flag");
        if(bShowcaseWaiting)IFileManager::Get().Delete(*ShowcaseGate);
    }
}
void AKKBenchmarkGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);Elapsed+=DeltaSeconds;
    if(bShowcase){TickShowcase();return;}
    const double Now=FPlatformTime::Seconds();
    const double WallElapsed=Now-BenchmarkStartTime;
    const double Warmup=bPerformancePass?15.0:10.0;
    const double End=bPerformancePass?45.0:70.0;
    if(bPerformanceMoving && BenchmarkStartTime>0.0 && WallElapsed<End)TickMovingWorkload(WallElapsed);
    if(BenchmarkStartTime>0.0 && WallElapsed>=Warmup && WallElapsed<End) FrameTimes.Add(static_cast<float>((Now-LastFrameTime)*1000.0));
    LastFrameTime=Now;
    if(BenchmarkStartTime>0.0 && WallElapsed>=End && !bSavedMetrics)
    {
        WriteMetrics();
        if(bPerformancePass)UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
    }
    if(bSmoke) TickSmoke();
    if(bInputState && Elapsed>=NextInputStateTime){WriteInputState();NextInputStateTime=Elapsed+.1f;}
}
void AKKBenchmarkGameMode::WriteInputState()
{
    auto* PC=Cast<AKKBenchmarkController>(UGameplayStatics::GetPlayerController(this,0));if(!PC)return;
    FString Units;
    for(const auto& UnitPtr:DemoUnits)
    {
        const AKKBenchmarkUnit* Unit=UnitPtr.Get();
        if(!Unit)continue;
        FVector2D Screen=FVector2D::ZeroVector;
        bool bVisible=PC->ProjectWorldLocationToScreen(Unit->GetActorLocation(),Screen);
        const FVector P=Unit->GetActorLocation();
        if(!Units.IsEmpty())Units+=TEXT(",");
        Units+=FString::Printf(TEXT("{\"species\":\"%s\",\"variant\":\"%s\",\"action\":\"%s\",\"selected\":%s,\"face_active\":%s,\"facial_morph_weight\":%.5f,\"body_morph_weight\":%.5f,\"screen_visible\":%s,\"screen_x\":%.3f,\"screen_y\":%.3f,\"x\":%.3f,\"y\":%.3f,\"z\":%.3f}"),Unit->IsKrag()?TEXT("Krag"):TEXT("Nib"),*Unit->GetVariantLabel(),*Unit->GetActionLabel(),PC->SelectedUnit()==Unit?TEXT("true"):TEXT("false"),Unit->IsFaceActing()?TEXT("true"):TEXT("false"),Unit->GetMaximumAppliedMorphWeight(TEXT("facial")),Unit->GetMaximumAppliedMorphWeight(TEXT("body")),bVisible?TEXT("true"):TEXT("false"),Screen.X,Screen.Y,P.X,P.Y,P.Z);
    }
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("Benchmark");IFileManager::Get().MakeDirectory(*Dir,true);
    FVector CameraPosition;FRotator CameraRotation;PC->GetPlayerViewPoint(CameraPosition,CameraRotation);
    const FString State=FString::Printf(TEXT("{\"elapsed\":%.3f,\"portrait\":%s,\"camera\":{\"x\":%.3f,\"y\":%.3f,\"z\":%.3f,\"pitch\":%.3f,\"yaw\":%.3f},\"units\":[%s]}"),Elapsed,PC->IsPortraitView()?TEXT("true"):TEXT("false"),CameraPosition.X,CameraPosition.Y,CameraPosition.Z,CameraRotation.Pitch,CameraRotation.Yaw,*Units);
    FFileHelper::SaveStringToFile(State,*(Dir/TEXT("input-state.tmp")));
    IFileManager::Get().Move(*(Dir/TEXT("input-state.json")),*(Dir/TEXT("input-state.tmp")),true,true);
}
void AKKBenchmarkGameMode::EndPlay(const EEndPlayReason::Type Reason){FinishShowcaseRecording();WriteMetrics();Super::EndPlay(Reason);}
void AKKBenchmarkGameMode::WriteMetrics()
{
    if(bSavedMetrics || FrameTimes.Num()==0) return;
    bSavedMetrics=true;
    FString CSV=TEXT("sample,frame_ms\n");double Sum=0;
    for(int32 i=0;i<FrameTimes.Num();i++){CSV+=FString::Printf(TEXT("%d,%.5f\n"),i,FrameTimes[i]);Sum+=FrameTimes[i];}
    TArray<float> Sorted=FrameTimes;Sorted.Sort();
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("Benchmark");IFileManager::Get().MakeDirectory(*Dir,true);
    const FString Prefix=bPerformanceMoving?TEXT("performance-moving"):bPerformancePass?TEXT("performance-idle"):TEXT("performance-diagnostic");
    FFileHelper::SaveStringToFile(CSV,*(Dir/(Prefix+TEXT("-frames.csv"))));
    const FIntPoint ViewSize=GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport?GEngine->GameViewport->Viewport->GetSizeXY():FIntPoint::ZeroValue;
    TSharedRef<FJsonObject> Report=MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("mode"),bPerformanceMoving?TEXT("natural pair movement/action workload; includes animation, movement, effects and audio costs"):bPerformancePass?TEXT("natural pair idle comparison"):TEXT("diagnostic session; not a controlled engine comparison"));
    Report->SetBoolField(TEXT("comparison_pass"),bPerformancePass);
    Report->SetBoolField(TEXT("completed_sample_window"),Sum*.001>=(bPerformancePass?29.5:59.5));
    Report->SetNumberField(TEXT("width"),ViewSize.X);Report->SetNumberField(TEXT("height"),ViewSize.Y);
    Report->SetNumberField(TEXT("samples"),Sorted.Num());Report->SetNumberField(TEXT("average_fps"),1000.0*Sorted.Num()/Sum);
    Report->SetNumberField(TEXT("mean_frame_ms"),Sum/Sorted.Num());
    Report->SetNumberField(TEXT("p50_frame_ms"),Sorted[Sorted.Num()/2]);
    Report->SetNumberField(TEXT("p95_frame_ms"),Sorted[FMath::Min(Sorted.Num()-1,FMath::FloorToInt(Sorted.Num()*.95f))]);
    Report->SetNumberField(TEXT("p99_frame_ms"),Sorted[FMath::Min(Sorted.Num()-1,FMath::FloorToInt(Sorted.Num()*.99f))]);
    Report->SetNumberField(TEXT("capture_seconds"),Sum*.001);Report->SetNumberField(TEXT("warmup_seconds"),bPerformancePass?15:10);
    if(bPerformanceMoving)
    {
        Report->SetNumberField(TEXT("workload_cycle_seconds"),12);
        Report->SetStringField(TEXT("workload"),TEXT("t0 both Run to initial+Krag(0.6,0,2)m/Nib(-0.4,0,1.8)m in Unity coordinates; t3 KragMelee/NibShoot; t4.3 KragHit/NibMelee; t6 Run to initial; t9 KragShoot/NibHit; idle remainder. Fixed default camera, natural variants."));
    }
    Report->SetStringField(TEXT("cpu"),FPlatformMisc::GetCPUBrand());Report->SetStringField(TEXT("gpu"),GRHIAdapterName);
    Report->SetStringField(TEXT("engine_version"),FEngineVersion::Current().ToString());
    Report->SetStringField(TEXT("rhi"),GDynamicRHI?GDynamicRHI->GetName():TEXT("unavailable"));
    Report->SetNumberField(TEXT("physical_ram_gib"),double(FPlatformMemory::GetConstants().TotalPhysical)/1073741824.0);
    Report->SetBoolField(TEXT("running_on_battery"),FPlatformMisc::IsRunningOnBattery());
    Report->SetStringField(TEXT("camera"),TEXT("distance6.4m; pitch22deg; verticalFOV38deg; fixedEV12.7"));
    Report->SetStringField(TEXT("requested_sun"),TEXT("55000lux; RGB(1,1,1); angular diameter1.5deg; pitch-42/yaw130deg in Unreal coordinates"));
    Report->SetStringField(TEXT("requested_profile"),TEXT("DX12 SM6; Epic; software Lumen; virtual shadow maps; TSR; 100% render scale"));
    TSharedRef<FJsonObject> Settings=MakeShared<FJsonObject>();
    for(const TCHAR* Name:{TEXT("r.ScreenPercentage"),TEXT("r.DynamicRes.OperationMode"),TEXT("r.VSync"),TEXT("r.AntiAliasingMethod"),TEXT("r.DynamicGlobalIlluminationMethod"),TEXT("r.ReflectionMethod"),TEXT("r.Shadow.Virtual.Enable"),TEXT("r.RayTracing"),TEXT("r.Lumen.HardwareRayTracing"),TEXT("r.VolumetricFog"),TEXT("sg.ResolutionQuality"),TEXT("sg.AntiAliasingQuality"),TEXT("sg.PostProcessQuality"),TEXT("sg.ViewDistanceQuality"),TEXT("sg.ShadowQuality"),TEXT("sg.GlobalIlluminationQuality"),TEXT("sg.ReflectionQuality"),TEXT("sg.TextureQuality"),TEXT("sg.EffectsQuality")})
        if(const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(Name))Settings->SetNumberField(Name,CVar->GetFloat());
    Report->SetObjectField(TEXT("actual_cvars"),Settings);
    TArray<TSharedPtr<FJsonValue>> Variants;
    for(const auto& Unit:DemoUnits)if(Unit)Variants.Add(MakeShared<FJsonValueString>(Unit->GetVariantLabel()));
    Report->SetArrayField(TEXT("variants"),Variants);
    FString Summary;TSharedRef<TJsonWriter<>> Writer=TJsonWriterFactory<>::Create(&Summary);
    FJsonSerializer::Serialize(Report,Writer);
    FFileHelper::SaveStringToFile(Summary,*(Dir/(Prefix+TEXT(".json"))));
    UE_LOG(LogTemp,Display,TEXT("KK_METRICS mode=%s samples=%d average_fps=%.2f"),*Prefix,Sorted.Num(),1000.0*Sorted.Num()/Sum);
}
void AKKBenchmarkGameMode::TickMovingWorkload(double WallElapsed)
{
    if(DemoUnits.Num()!=2)return;
    const int32 Cycle=FMath::FloorToInt(WallElapsed/12.0);
    if(Cycle!=PerformanceWorkloadCycle){PerformanceWorkloadCycle=Cycle;PerformanceWorkloadPhase=0;}
    const double PhaseTime=FMath::Fmod(WallElapsed,12.0);
    const double Times[]={0.0,3.0,4.3,6.0,9.0};
    auto* Krag=DemoUnits[0].Get();auto* Nib=DemoUnits[1].Get();
    while(PerformanceWorkloadPhase<UE_ARRAY_COUNT(Times) && PhaseTime>=Times[PerformanceWorkloadPhase])
    {
        switch(PerformanceWorkloadPhase)
        {
        // Shared Unity horizontal X/Z maps to Unreal X/-Y, meters to centimeters.
        case 0:Krag->MoveTo(PerformanceOrigins[0]+FVector(60,-200,0));Nib->MoveTo(PerformanceOrigins[1]+FVector(-40,-180,0));break;
        case 1:Krag->PlayDemoAction(TEXT("Melee"));Nib->PlayDemoAction(TEXT("Shoot"));break;
        case 2:Krag->PlayDemoAction(TEXT("Hit"));Nib->PlayDemoAction(TEXT("Melee"));break;
        case 3:Krag->MoveTo(PerformanceOrigins[0]);Nib->MoveTo(PerformanceOrigins[1]);break;
        case 4:Krag->PlayDemoAction(TEXT("Shoot"));Nib->PlayDemoAction(TEXT("Hit"));break;
        }
        ++PerformanceWorkloadPhase;
    }
}
void AKKBenchmarkHUD::DrawHUD()
{
    Super::DrawHUD();if(!Canvas)return;
    const float X=32,Y=28;
    DrawRect(FLinearColor(.016f,.024f,.028f,.82f),20,16,475,94);
    DrawText(TEXT("KRAG KINGS  /  UNREAL"),FLinearColor(.89f,.83f,.70f),X,Y,nullptr,1.35f);
    auto* PC=Cast<AKKBenchmarkController>(GetOwningPlayerController());
    if(PC && PC->SelectedUnit())
    {
        DrawText(PC->SelectedUnit()->GetVariantLabel(),FLinearColor(.3f,.85f,.76f),X,Y+30,nullptr,1.2f);
        const FString ActionLabel=PC->SelectedUnit()->IsFaceActing() && PC->SelectedUnit()->GetActionLabel()==TEXT("Idle")?TEXT("EXPRESSION"):PC->SelectedUnit()->GetActionLabel();
        DrawText(ActionLabel,FLinearColor(.7f,.73f,.71f),X,Y+55,nullptr,1.f);
    }
    DrawRect(FLinearColor(.016f,.024f,.028f,.8f),20,Canvas->SizeY-62,Canvas->SizeX-40,42);
    DrawText(TEXT("LMB Select  RMB Run  SHIFT+RMB Walk  A Melee  F Shoot  H Hit  V Bionics  E Face  C Portrait  TAB Unit  Arrows Pan  MMB Orbit  Wheel Zoom  HOME Reset"),FLinearColor(.84f,.81f,.72f),32,Canvas->SizeY-49,nullptr,1.f);
}

void AKKBenchmarkGameMode::SmokeCheck(bool bPass,const FString& Name)
{
    if(!SmokeResults.IsEmpty()) SmokeResults+=TEXT(",\n");
    SmokeResults+=FString::Printf(TEXT("    {\"check\": \"%s\", \"passed\": %s}"),*Name,bPass?TEXT("true"):TEXT("false"));
    if(!bPass) ++SmokeFailures;
    UE_LOG(LogTemp,Display,TEXT("KK_SMOKE %s %s"),bPass?TEXT("PASS"):TEXT("FAIL"),*Name);
}
void AKKBenchmarkGameMode::BeginShowcaseRecording()
{
    const FString AudioStartUtc=FDateTime::UtcNow().ToIso8601();
    UAudioMixerBlueprintLibrary::StartRecordingOutput(this,75.f,nullptr);bShowcaseAudioRecording=true;
    ShowcaseStartTime=FPlatformTime::Seconds();UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_STARTED utc=%s"),*AudioStartUtc);
}
void AKKBenchmarkGameMode::FinishShowcaseRecording()
{
    if(!bShowcaseAudioRecording)return;bShowcaseAudioRecording=false;
    const FString AudioDir=FPaths::ConvertRelativePathToFull(FPaths::GetPath(ShowcaseGate));IFileManager::Get().MakeDirectory(*AudioDir,true);
    UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("showcase-engine-audio"),AudioDir,nullptr);
    UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_AUDIO_EXPORT_REQUESTED %s"),*(AudioDir/TEXT("showcase-engine-audio.wav")));
}
void AKKBenchmarkGameMode::TickShowcase()
{
    if(bShowcaseComplete || DemoUnits.Num()!=2)return;
    if(!bShowcaseReady)
    {
        if(FPlatformTime::Seconds()-BenchmarkStartTime<15.0)return;
        bShowcaseReady=true;
        UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_READY gate=%s waiting=%d duration=72 window=Krag Kings - Unreal Benchmark"),*ShowcaseGate,bShowcaseWaiting?1:0);
        if(!bShowcaseWaiting)BeginShowcaseRecording();
    }
    if(bShowcaseWaiting)
    {
        if(!IFileManager::Get().FileExists(*ShowcaseGate))return;
        IFileManager::Get().Delete(*ShowcaseGate);bShowcaseWaiting=false;
        BeginShowcaseRecording();
    }
    auto* PC=Cast<AKKBenchmarkController>(UGameplayStatics::GetPlayerController(this,0));if(!PC)return;
    auto* Krag=DemoUnits[0].Get();auto* Nib=DemoUnits[1].Get();
    const double Time=FPlatformTime::Seconds()-ShowcaseStartTime;
    const double Times[]={0,6,10,14,16,18,20,24,26.5,28,36,36.5,38,45.5,47,48,52,56,60,62,65,68,72};
    while(ShowcasePhase<UE_ARRAY_COUNT(Times) && Time>=Times[ShowcasePhase])
    {
        switch(ShowcasePhase)
        {
        case 0:PC->ResetCamera();break;
        case 1:Krag->MoveTo(PerformanceOrigins[0]+FVector(-70,-400,0),true);Nib->MoveTo(PerformanceOrigins[1]+FVector(90,-400,0));break;
        case 2:Nib->MoveTo(PerformanceOrigins[1]);break;
        case 3:PC->SelectUnit(Krag);Krag->PlayDemoAction(TEXT("Melee"));PC->SelectUnit(Nib);Nib->PlayDemoAction(TEXT("Shoot"));break;
        case 4:Krag->SetVariantIndex(1);Nib->SetVariantIndex(1);Krag->PlayDemoAction(TEXT("Melee"));Nib->PlayDemoAction(TEXT("Shoot"));break;
        case 5:Krag->PlayDemoAction(TEXT("Hit"));Nib->PlayDemoAction(TEXT("Hit"));break;
        case 6:Krag->SetVariantIndex(2);Nib->SetVariantIndex(2);Krag->MoveTo(PerformanceOrigins[0]);Nib->MoveTo(PerformanceOrigins[1]);break;
        case 7:Krag->SetVariantIndex(3);Krag->PlayDemoAction(TEXT("Shoot"));Nib->PlayDemoAction(TEXT("Melee"));break;
        case 8:Nib->SetVariantIndex(0);Nib->MoveTo(Nib->GetActorLocation()+FVector(0,-60,0),true);break;
        case 9:Nib->SetVariantIndex(0);PC->FocusPortrait(Nib);Nib->PlayFacePerformance();break;
        case 10:Krag->SetVariantIndex(0);Krag->MoveTo(Krag->GetActorLocation()+FVector(0,-60,0),true);break;
        case 11:Nib->PlayDemoAction(TEXT("Shoot"));break;
        case 12:Krag->SetVariantIndex(0);PC->FocusPortrait(Krag);Krag->PlayFacePerformance();break;
        case 13:Krag->PlayDemoAction(TEXT("Melee"));break;
        case 14:Krag->PlayDemoAction(TEXT("Shoot"));break;
        case 15:case 16:case 17:case 18:
        {
            const int32 Cycle=ShowcasePhase-15;const float Side=Cycle%2==0?1.f:-1.f;
            Krag->SetVariantIndex(1+Cycle%3);Nib->SetVariantIndex(1+Cycle%2);
            Krag->MoveTo(PerformanceOrigins[0]+FVector(-70,-Side*200,0),Cycle%2==0);
            Nib->MoveTo(PerformanceOrigins[1]+FVector(70,-Side*200,0));break;
        }
        case 19:PC->ResetCamera();Krag->SetVariantIndex(0);Nib->SetVariantIndex(0);Krag->MoveTo(PerformanceOrigins[0]+FVector(0,100,0));Nib->MoveTo(PerformanceOrigins[1]+FVector(0,100,0));break;
        case 20:Krag->MoveTo(PerformanceOrigins[0]);Nib->MoveTo(PerformanceOrigins[1]);break;
        case 21:PC->SelectUnit(Krag);Krag->PlayDemoAction(TEXT("Melee"));Nib->PlayDemoAction(TEXT("Shoot"));break;
        case 22:bShowcaseComplete=true;FinishShowcaseRecording();PC->EndShowcase();PC->ResetCamera();UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_COMPLETE duration=72 visual_acceptance_pending=1"));break;
        }
        ++ShowcasePhase;
    }
    if((Time<28 || Time>=48) && Time<72)
    {
        FBox VisibleBounds(ForceInit);
        for(const AKKBenchmarkUnit* Unit:{Krag,Nib})
        {
            VisibleBounds+=Unit->GetMesh()->Bounds.GetBox();
            VisibleBounds+=Unit->GetCapsuleComponent()->Bounds.GetBox();
        }
        float CameraYaw=75.f+FMath::Sin(Time*.15)*30.f;
        if(Time>=62)
        {
            const float Settle=FMath::Clamp(float((Time-62)/7),0.f,1.f);
            CameraYaw=FMath::Lerp(CameraYaw,75.f,Settle);
        }
        PC->SetShowcaseFraming(VisibleBounds,CameraYaw,-22.f,GetWorld()->GetDeltaSeconds());
    }
}
void AKKBenchmarkGameMode::TickSmoke()
{
    if(Elapsed<NextSmokeTime) return;
    auto* PC=Cast<AKKBenchmarkController>(UGameplayStatics::GetPlayerController(this,0));
    if(!PC || DemoUnits.Num()!=2)
    {
        SmokeCheck(false,TEXT("two runtime units and controller exist"));
        bSmoke=false;return;
    }
    auto CheckGround=[this](AKKBenchmarkUnit* Unit)
    {
        FHitResult Ground;FCollisionQueryParams Params;Params.AddIgnoredActor(Unit);
        const FVector P=Unit->GetActorLocation();
        bool bGround=GetWorld()->LineTraceSingleByChannel(Ground,P+FVector(0,0,200),P-FVector(0,0,1000),ECC_Visibility,Params);
        const float Gap=bGround?P.Z-Unit->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-Ground.ImpactPoint.Z:1000;
        SmokeCheck(bGround && FMath::Abs(Gap)<12.f,FString::Printf(TEXT("%s dune grounding under 12cm capsule tolerance"),Unit->IsKrag()?TEXT("Krag"):TEXT("Nib")));
    };
    auto MoveUnit=[this,PC](AKKBenchmarkUnit* Unit,const FVector& XY)
    {
        PC->SelectUnit(Unit);SmokeMoveStart=Unit->GetActorLocation();
        FHitResult Ground;
        bool bGround=GetWorld()->LineTraceSingleByChannel(Ground,XY+FVector(0,0,3000),XY-FVector(0,0,3000),ECC_Visibility);
        SmokeCheck(bGround,TEXT("movement destination hits dune collider"));
        if(bGround) Unit->MoveTo(Ground.ImpactPoint);
    };
    const FString EvidenceDir=FPaths::ProjectSavedDir()/TEXT("Benchmark");
    IFileManager::Get().MakeDirectory(*EvidenceDir,true);
    switch(SmokePhase)
    {
        case 0:
            SmokeCheck(AssetSet && AssetSet->Krags.Num()>=3 && AssetSet->Nibs.Num()>=3,TEXT("both species have requested variant families"));
            FScreenshotRequest::RequestScreenshot(EvidenceDir/TEXT("smoke-initial.png"),true,false);
            MoveUnit(DemoUnits[0],FVector(-700,500,0));NextSmokeTime=11;break;
        case 1:
            SmokeCheck(FVector::Dist2D(SmokeMoveStart,DemoUnits[0]->GetActorLocation())>400,TEXT("Krag traverses dune terrain"));
            CheckGround(DemoUnits[0]);DemoUnits[0]->PlayDemoAction("Melee");
            SmokeCheck(DemoUnits[0]->GetActionLabel()==TEXT("Melee"),TEXT("Krag melee action selected"));
            PC->SelectUnit(DemoUnits[1]);DemoUnits[1]->PlayDemoAction("Shoot");
            SmokeCheck(DemoUnits[0]->GetActionLabel()==TEXT("Melee") && DemoUnits[1]->GetActionLabel()==TEXT("Shoot"),TEXT("independent units perform overlapping actions after selection changes"));
            NextSmokeTime=13;break;
        case 2:
            DemoUnits[0]->PlayDemoAction("Shoot");SmokeCheck(DemoUnits[0]->GetActionLabel()==TEXT("Shoot"),TEXT("Krag shoot action selected"));NextSmokeTime=15;break;
        case 3:
            DemoUnits[0]->PlayDemoAction("Hit");SmokeCheck(DemoUnits[0]->GetActionLabel()==TEXT("Hit"),TEXT("Krag hit action selected"));NextSmokeTime=17;break;
        case 4:
        {
            const FString Before=DemoUnits[0]->GetVariantLabel();DemoUnits[0]->CycleVariant();
            SmokeCheck(Before!=DemoUnits[0]->GetVariantLabel(),TEXT("Krag bionic variant switches"));
            MoveUnit(DemoUnits[1],FVector(700,-500,0));NextSmokeTime=23;break;
        }
        case 5:
            SmokeCheck(PC->SelectedUnit()==DemoUnits[1],TEXT("selection changes to Nib"));
            SmokeCheck(FVector::Dist2D(SmokeMoveStart,DemoUnits[1]->GetActorLocation())>400,TEXT("Nib traverses dune terrain"));
            CheckGround(DemoUnits[1]);DemoUnits[1]->PlayDemoAction("Melee");
            SmokeCheck(DemoUnits[1]->GetActionLabel()==TEXT("Melee"),TEXT("Nib melee action selected"));NextSmokeTime=25;break;
        case 6:
            DemoUnits[1]->PlayDemoAction("Shoot");SmokeCheck(DemoUnits[1]->GetActionLabel()==TEXT("Shoot"),TEXT("Nib shoot action selected"));NextSmokeTime=27;break;
        case 7:
            DemoUnits[1]->PlayDemoAction("Hit");SmokeCheck(DemoUnits[1]->GetActionLabel()==TEXT("Hit"),TEXT("Nib hit action selected"));NextSmokeTime=29;break;
        case 8:
        {
            const FString Before=DemoUnits[1]->GetVariantLabel();DemoUnits[1]->CycleVariant();
            SmokeCheck(Before!=DemoUnits[1]->GetVariantLabel(),TEXT("Nib replacement variant switches"));
            MoveUnit(DemoUnits[0],FVector(-135,0,0));
            MoveUnit(DemoUnits[1],FVector(120,-10,0));PC->ResetCamera();NextSmokeTime=36;break;
        }
        case 9:
            CheckGround(DemoUnits[0]);CheckGround(DemoUnits[1]);
            FScreenshotRequest::RequestScreenshot(EvidenceDir/TEXT("smoke-final.png"),true,false);NextSmokeTime=71;break;
        case 10:
        {
            const FString Report=FString::Printf(TEXT("{\n  \"source\": \"packaged runtime scripted exercise\",\n  \"mouse_keyboard_delivery_tested\": false,\n  \"failures\": %d,\n  \"checks\": [\n%s\n  ]\n}\n"),SmokeFailures,*SmokeResults);
            FFileHelper::SaveStringToFile(Report,*(EvidenceDir/TEXT("smoke-report.json")));
            UE_LOG(LogTemp,Display,TEXT("KK_SMOKE_COMPLETE failures=%d"),SmokeFailures);
            bSmoke=false;UKismetSystemLibrary::QuitGame(this,PC,EQuitPreference::Quit,false);break;
        }
        default:bSmoke=false;break;
    }
    ++SmokePhase;
}
