#include "KKBenchmarkGameMode.h"
#include "KKBenchmarkAssets.h"
#include "KKBenchmarkUnit.h"
#include "KKBenchmarkController.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "DistanceFieldAtlas.h"
#include "MeshCardBuild.h"
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
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

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
    bSkinReview=FParse::Param(FCommandLine::Get(),TEXT("KKSkinReview"));
    if(bSkinReview && (bPerformancePass || bShowcase || bSmoke || bInputState))
    {
        UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED skin review must be a separate capture-only launch"));
        UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);return;
    }
    if(bSkinReview)
    {
        if(!FParse::Value(FCommandLine::Get(),TEXT("KKSkinReviewOutput="),SkinReviewOutput))
            SkinReviewOutput=FPaths::ProjectSavedDir()/TEXT("Benchmark/SkinAB")/FDateTime::UtcNow().ToString(TEXT("%Y%m%d-%H%M%S"));
        IFileManager::Get().MakeDirectory(*SkinReviewOutput,true);
    }
    FString SkinModeArgument;
    if(FParse::Value(FCommandLine::Get(),TEXT("KKSkinMode="),SkinModeArgument))RequestedSkinMode=FName(*SkinModeArgument);
    if(RequestedSkinMode!=TEXT("Generic") && RequestedSkinMode!=TEXT("DefaultLit") && RequestedSkinMode!=TEXT("Profile"))
    {
        UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED unknown KKSkinMode"));
        UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);return;
    }
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
    TerrainActor=Ground;
    Ground->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Ground->GetStaticMeshComponent()->SetStaticMesh(AssetSet->Terrain);
    Ground->GetStaticMeshComponent()->SetMaterial(0,AssetSet->SandMaterial);
    Ground->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
    Ground->GetStaticMeshComponent()->SetCastShadow(true);
    // Unity Euler(42,-140,0): horizontal Unity X/Z -> Unreal X/-Y.
    auto* Sun=GetWorld()->SpawnActor<ADirectionalLight>(FVector(0,0,2000),FRotator(-42,130,0));
    // ADirectionalLight's CDO supplies a -46-degree root rotation. Spawn composes
    // it with the requested transform, so explicitly establish the final angle.
    auto* SunComponent=Cast<UDirectionalLightComponent>(Sun->GetLightComponent());
    SunComponent->SetMobility(EComponentMobility::Movable);
    Sun->SetActorRotation(FRotator(-42,130,0));
    if(!Sun->GetActorRotation().Equals(FRotator(-42,130,0),.01f))
    {
        UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED final sun rotation did not match the requested transform"));
        UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
        return;
    }
    SunComponent->SetIntensity(55000.f);
    SunComponent->SetLightColor(FLinearColor::White);
    SunComponent->SetAtmosphereSunLight(true);
    SunComponent->SetCastShadows(true);
    SunComponent->SetLightSourceAngle(1.5f);
    auto* Atmosphere=GetWorld()->SpawnActor<ASkyAtmosphere>();
    // This is an absolute coefficient, not a normalized intensity multiplier.
    // Keep UE's Earth-like 0.0331 default for the neutral comparison lighting.
    UE_LOG(LogTemp,Display,TEXT("KK_LIGHTING sun_lux=%.1f color=%s rotation=%s rayleigh_scale=%.6f"),
        SunComponent->Intensity,*SunComponent->GetLightColor().ToString(),*Sun->GetActorRotation().ToString(),Atmosphere->GetComponent()->RayleighScatteringScale);
    auto* Sky=GetWorld()->SpawnActor<ASkyLight>();
    SkyLightActor=Sky;
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
    bWaitingForTerrain=true;
    TerrainWaitStarted=FPlatformTime::Seconds();
    if(!TryStartDemo())UE_LOG(LogTemp,Display,TEXT("KK_WAITING_FOR_TERRAIN actual collision queries must succeed before spawning"));
}
bool AKKBenchmarkGameMode::TryStartDemo()
{
    FVector Positions[2]={FVector(-135,0,0),FVector(120,-10,0)};
    for(FVector& Position:Positions)
    {
        FHitResult GroundHit;
        if(!GetWorld()->LineTraceSingleByObjectType(GroundHit,Position+FVector(0,0,6000),Position-FVector(0,0,6000),FCollisionObjectQueryParams(ECC_WorldStatic))
            || GroundHit.GetActor()!=TerrainActor || GroundHit.ImpactNormal.Z<.7f)return false;
        Position.Z=GroundHit.ImpactPoint.Z+112.f;
        UE_LOG(LogTemp,Display,TEXT("KK_START_GROUND point=%s normal=%s"),*GroundHit.ImpactPoint.ToString(),*GroundHit.ImpactNormal.ToString());
    }
    auto SpawnUnit=[this](bool bKrag,FVector Position)
    {
        FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Unit=GetWorld()->SpawnActor<AKKBenchmarkUnit>(Position,FRotator(0,-90,0),Params);
        Unit->InitializeUnit(AssetSet,bKrag);
        DemoUnits.Add(Unit);
        return Unit;
    };
    auto* Krag=SpawnUnit(true,Positions[0]);
    SpawnUnit(false,Positions[1]);
    for(const auto& Unit:DemoUnits)
    {
        if(!Unit->SetSkinMode(RequestedSkinMode))
        {
            bWaitingForTerrain=false;
            UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED requested skin alternatives are absent or invalid"));
            UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);return false;
        }
    }
    bWaitingForTerrain=false;Elapsed=0.f;
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
    return true;
}
void AKKBenchmarkGameMode::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if(bWaitingForTerrain)
    {
        if(!TryStartDemo() && FPlatformTime::Seconds()-TerrainWaitStarted>30.0)
        {
            bWaitingForTerrain=false;
            UE_LOG(LogTemp,Error,TEXT("KK_SETUP_FAILED terrain collision did not become ready within 30 seconds; no units spawned"));
            UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
        }
        return;
    }
    if(DemoUnits.Num()!=2)return;
    Elapsed+=DeltaSeconds;
    // Startup diagnostics only; finish before either performance sample begins.
    if(!bLightingDiagnosticsWritten && Elapsed>3.f){WriteLightingDiagnostics();bLightingDiagnosticsWritten=true;}
    if(!bWindowTitleApplied && Elapsed>1.f && GEngine && GEngine->GameViewport && GEngine->GameViewport->GetWindow().IsValid())
    {
        GEngine->GameViewport->GetWindow()->SetTitle(FText::FromString(TEXT("Krag Kings - Unreal Benchmark")));
        bWindowTitleApplied=true;
    }
    if(!bReviewFrameWritten && Elapsed>20.f && FParse::Param(FCommandLine::Get(),TEXT("KKReviewFrame")))
    {
        const FString Dir=FPaths::ProjectSavedDir()/TEXT("Benchmark");IFileManager::Get().MakeDirectory(*Dir,true);
        FScreenshotRequest::RequestScreenshot(Dir/TEXT("review-frame.png"),true,false);
        bReviewFrameWritten=true;
    }
    if(bShowcase){TickShowcase();return;}
    if(bSkinReview){TickSkinReview();return;}
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
void AKKBenchmarkGameMode::WriteLightingDiagnostics()
{
    if(SkyLightActor)
    {
        const auto* Sky=SkyLightActor->GetLightComponent();
        UE_LOG(LogTemp,Display,TEXT("KK_SKYLIGHT visible=%d registered=%d affects_world=%d affects_gi=%d mobility=%d source=%d realtime_requested=%d realtime_effective=%d intensity=%.4f indirect=%.4f lower_solid=%d lower_color=%s cubemap_resolution=%d sky_distance_cm=%.1f occlusion_max_cm=%.1f min_occlusion=%.3f position=%s"),
            Sky->IsVisible(),Sky->IsRegistered(),Sky->bAffectsWorld,Sky->bAffectGlobalIllumination,int32(Sky->Mobility),int32(Sky->SourceType),Sky->bRealTimeCapture,Sky->IsRealTimeCaptureEnabled(),Sky->Intensity,Sky->IndirectLightingIntensity,Sky->bLowerHemisphereIsBlack,*Sky->LowerHemisphereColor.ToString(),Sky->CubemapResolution,Sky->SkyDistanceThreshold,Sky->OcclusionMaxDistance,Sky->MinOcclusion,*Sky->GetComponentLocation().ToString());
        // CPU irradiance/AverageBrightness are not the real-time GPU capture result.
    }
    if(TerrainActor && AssetSet && AssetSet->Terrain)
    {
        const auto* Data=AssetSet->Terrain->GetRenderData();
        if(Data && Data->LODResources.Num()>0)
        {
            const auto& LOD=Data->LODResources[0];
            const auto* DF=LOD.DistanceFieldData;const auto* Cards=LOD.CardRepresentationData;
            const auto* Ground=TerrainActor->GetStaticMeshComponent();
            UE_LOG(LogTemp,Display,TEXT("KK_TERRAIN_INDIRECT df_present=%d df_valid=%d df_async=%d df_two_sided=%d df_grid=%s card_count=%d affects_df=%d cast_shadow=%d bounds_cm=%s"),
                DF!=nullptr,DF && DF->IsValid(),DF && DF->bAsyncBuilding,DF && DF->bMostlyTwoSided,DF?*DF->Mips[0].IndirectionDimensions.ToString():TEXT("none"),Cards?Cards->MeshCardsBuildData.CardBuildData.Num():0,Ground->bAffectDistanceFieldLighting,Ground->CastShadow,*Ground->Bounds.BoxExtent.ToString());
        }
    }
    for(const TCHAR* Name:{TEXT("r.SkyLight.RealTimeReflectionCapture"),TEXT("r.SkyLight.RealTimeReflectionCapture.TimeSlice"),TEXT("r.SkyLightingQuality"),TEXT("r.DynamicGlobalIlluminationMethod"),TEXT("r.Lumen.DiffuseIndirect.Allow"),TEXT("r.LumenScene.Radiosity"),TEXT("r.Lumen.ScreenProbeGather.ShortRangeAO"),TEXT("r.DistanceFieldAO"),TEXT("r.GenerateMeshDistanceFields"),TEXT("r.Lumen.TraceMeshSDFs.Allow")})
        if(auto* CVar=IConsoleManager::Get().FindConsoleVariable(Name))UE_LOG(LogTemp,Display,TEXT("KK_LIGHTING_CVAR %s=%s"),Name,*CVar->GetString());
}
void AKKBenchmarkGameMode::TickSkinReview()
{
    const double Now=FPlatformTime::Seconds()-BenchmarkStartTime;
    if(Now<SkinReviewNextTime)return;
    auto* PC=Cast<AKKBenchmarkController>(UGameplayStatics::GetPlayerController(this,0));if(!PC)return;
    const TCHAR* Modes[]={TEXT("Generic"),TEXT("DefaultLit"),TEXT("Profile")};
    const TCHAR* Views[]={TEXT("Wide"),TEXT("Nib"),TEXT("Krag")};
    auto Fail=[this](const FString& Reason)
    {
        SkinReviewNextTime=DBL_MAX;UE_LOG(LogTemp,Error,TEXT("KK_SKIN_REVIEW_FAILED %s"),*Reason);
        UKismetSystemLibrary::QuitGame(this,UGameplayStatics::GetPlayerController(this,0),EQuitPreference::Quit,false);
    };
    if(SkinReviewIndex>=9)
    {
        TArray<TSharedPtr<FJsonValue>> Images;
        for(const TCHAR* Mode:Modes)for(const TCHAR* View:Views)
        {
            const FString File=SkinReviewOutput/FString::Printf(TEXT("%s-%s.png"),Mode,View);
            if(IFileManager::Get().FileSize(*File)<1024){Fail(TEXT("Missing actual screenshot ")+File);return;}
            Images.Add(MakeShared<FJsonValueString>(File));
        }
        TSharedRef<FJsonObject> Report=MakeShared<FJsonObject>();
        Report->SetStringField(TEXT("source"),TEXT("Actual running engine; same fixed idle pose across all skin material/view combinations"));
        Report->SetBoolField(TEXT("visual_acceptance"),false);Report->SetBoolField(TEXT("performance_sample"),false);
        Report->SetArrayField(TEXT("screenshots"),Images);
        TSharedRef<FJsonObject> CVars=MakeShared<FJsonObject>();
        for(const TCHAR* Name:{TEXT("r.Substrate"),TEXT("r.SSS.Scale"),TEXT("r.SSS.Quality"),TEXT("r.SSS.Burley.Quality"),TEXT("r.ScreenPercentage")})
            if(const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(Name))CVars->SetNumberField(Name,CVar->GetFloat());
        Report->SetObjectField(TEXT("actual_cvars"),CVars);
        const FIntPoint Size=GEngine->GameViewport->Viewport->GetSizeXY();
        Report->SetNumberField(TEXT("width"),Size.X);Report->SetNumberField(TEXT("height"),Size.Y);
        FString JSON;const auto Writer=TJsonWriterFactory<>::Create(&JSON);FJsonSerializer::Serialize(Report,Writer);
        if(!FFileHelper::SaveStringToFile(JSON,*(SkinReviewOutput/TEXT("skin-review.json")))){Fail(TEXT("Cannot save report"));return;}
        UE_LOG(LogTemp,Display,TEXT("KK_SKIN_REVIEW_COMPLETE %s"),*SkinReviewOutput);SkinReviewNextTime=DBL_MAX;
        UKismetSystemLibrary::QuitGame(this,PC,EQuitPreference::Quit,false);return;
    }
    const FName Mode(Modes[SkinReviewIndex/3]);
    const int32 View=SkinReviewIndex%3;
    if(!bSkinReviewAwaitingCapture)
    {
        for(const auto& Unit:DemoUnits)
        {
            Unit->GetMesh()->bPauseAnims=true;
            if(!Unit->SetSkinMode(Mode)){Fail(TEXT("Missing or invalid review material"));return;}
        }
        if(View==0){PC->SelectUnit(DemoUnits[0]);PC->ResetCamera();}
        else PC->FocusPortrait(DemoUnits[View==1?1:0]);
        bSkinReviewAwaitingCapture=true;SkinReviewNextTime=Now+3.0;
        UE_LOG(LogTemp,Display,TEXT("KK_SKIN_REVIEW_VIEW mode=%s view=%s"),*Mode.ToString(),Views[View]);
        return;
    }
    const FString File=SkinReviewOutput/FString::Printf(TEXT("%s-%s.png"),*Mode.ToString(),Views[View]);
    if(IFileManager::Get().FileExists(*File)){Fail(TEXT("Existing review image preserved ")+File);return;}
    FScreenshotRequest::RequestScreenshot(File,true,false);
    ++SkinReviewIndex;bSkinReviewAwaitingCapture=false;SkinReviewNextTime=Now+1.0;
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
        Units+=FString::Printf(TEXT("{\"species\":\"%s\",\"variant\":\"%s\",\"action\":\"%s\",\"selected\":%s,\"face_active\":%s,\"facial_morph_weight\":%.5f,\"body_morph_weight\":%.5f,\"screen_visible\":%s,\"screen_x\":%.3f,\"screen_y\":%.3f,\"x\":%.3f,\"y\":%.3f,\"z\":%.3f,\"shots\":%s}"),Unit->IsKrag()?TEXT("Krag"):TEXT("Nib"),*Unit->GetVariantLabel(),*Unit->GetActionLabel(),PC->SelectedUnit()==Unit?TEXT("true"):TEXT("false"),Unit->IsFaceActing()?TEXT("true"):TEXT("false"),Unit->GetMaximumAppliedMorphWeight(TEXT("facial")),Unit->GetMaximumAppliedMorphWeight(TEXT("body")),bVisible?TEXT("true"):TEXT("false"),Screen.X,Screen.Y,P.X,P.Y,P.Z,*Unit->GetShotDiagnosticsJson());
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
    // UE5.8's Windows helper tests BatteryFlag presence/charging, not AC supply.
    Report->SetBoolField(TEXT("ue_battery_presence_flag"),FPlatformMisc::IsRunningOnBattery());
    Report->SetField(TEXT("running_on_battery"),MakeShared<FJsonValueNull>());
#if PLATFORM_WINDOWS
    SYSTEM_POWER_STATUS PowerStatus{};
    if(::GetSystemPowerStatus(&PowerStatus))
    {
        Report->SetNumberField(TEXT("windows_ac_line_status"),PowerStatus.ACLineStatus);
        if(PowerStatus.ACLineStatus<=1)Report->SetBoolField(TEXT("running_on_battery"),PowerStatus.ACLineStatus==0);
        if(PowerStatus.BatteryLifePercent!=255)Report->SetNumberField(TEXT("battery_percent"),PowerStatus.BatteryLifePercent);
    }
#endif
    Report->SetStringField(TEXT("camera"),TEXT("distance6.4m; pitch22deg; verticalFOV38deg; fixedEV12.7"));
    Report->SetStringField(TEXT("requested_sun"),TEXT("55000lux; RGB(1,1,1); angular diameter1.5deg; pitch-42/yaw130deg in Unreal coordinates"));
    Report->SetStringField(TEXT("requested_profile"),TEXT("DX12 SM6; Epic; software Lumen; virtual shadow maps; TSR; 100% render scale"));
    Report->SetStringField(TEXT("skin_mode"),RequestedSkinMode.ToString());
    TSharedRef<FJsonObject> Settings=MakeShared<FJsonObject>();
    for(const TCHAR* Name:{TEXT("r.ScreenPercentage"),TEXT("r.DynamicRes.OperationMode"),TEXT("r.VSync"),TEXT("r.AntiAliasingMethod"),TEXT("r.DynamicGlobalIlluminationMethod"),TEXT("r.ReflectionMethod"),TEXT("r.Shadow.Virtual.Enable"),TEXT("r.RayTracing"),TEXT("r.Lumen.HardwareRayTracing"),TEXT("r.VolumetricFog"),TEXT("sg.ResolutionQuality"),TEXT("sg.AntiAliasingQuality"),TEXT("sg.PostProcessQuality"),TEXT("sg.ViewDistanceQuality"),TEXT("sg.ShadowQuality"),TEXT("sg.GlobalIlluminationQuality"),TEXT("sg.ReflectionQuality"),TEXT("sg.TextureQuality"),TEXT("sg.EffectsQuality")})
        if(const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(Name))Settings->SetNumberField(Name,CVar->GetFloat());
    Report->SetObjectField(TEXT("actual_cvars"),Settings);
    for(const TCHAR* Name:{TEXT("r.Substrate"),TEXT("r.SSS.Scale"),TEXT("r.SSS.Quality"),TEXT("r.SSS.Burley.Quality"),TEXT("r.SSS.Checkerboard")})
        if(const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(Name))Settings->SetNumberField(Name,CVar->GetFloat());
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
    Super::DrawHUD();if(!Canvas || !GEngine)return;
    // Match the inspection space reserved by the other engine: readable
    // controls sit outside the models, with the selected actor/action explicit.
    const float Scale=FMath::Min(Canvas->SizeX/1920.f,Canvas->SizeY/1080.f);
    const float Left=34.f*Scale,TopHeight=94.f*Scale,BottomHeight=96.f*Scale;
    const float Bottom=Canvas->SizeY-BottomHeight;
    const FLinearColor Panel(.018f,.024f,.020f,.95f),Gold(.84f,.57f,.24f);
    const FLinearColor Teal(.035f,.65f,.58f),Text(.89f,.90f,.85f),Muted(.46f,.49f,.42f);
    UFont* Font=GEngine->GetMediumFont();
    auto Label=[&](const FString& Value,const FLinearColor& Color,float X,float Y,float Height,float MaxWidth=0.f,bool bAlignRight=false)
    {
        float Width=0.f,MeasuredHeight=0.f;
        GetTextSize(Value,Width,MeasuredHeight,Font,1.f);
        float FontScale=Height*Scale/FMath::Max(MeasuredHeight,1.f);
        if(MaxWidth>0.f && Width>0.f)FontScale=FMath::Min(FontScale,MaxWidth/Width);
        DrawText(Value,Color,bAlignRight?X-Width*FontScale:X,Y,Font,FontScale);
    };
    DrawRect(Panel,0,0,Canvas->SizeX,TopHeight);
    DrawRect(Panel,0,Bottom,Canvas->SizeX,BottomHeight);
    Label(TEXT("KRAG KINGS"),Gold,Left,20.f*Scale,30.f);
    Label(TEXT("DUNES / CHARACTER & MOVEMENT STUDY"),Muted,Left,59.f*Scale,15.f,610.f*Scale);
    Label(TEXT("UNREAL"),Text,Canvas->SizeX-Left,26.f*Scale,21.f,220.f*Scale,true);
    auto* PC=Cast<AKKBenchmarkController>(GetOwningPlayerController());
    if(PC && PC->SelectedUnit())
    {
        const auto* Unit=PC->SelectedUnit();
        const float UnitX=700.f*Scale;
        Label(Unit->GetVariantLabel().ToUpper(),Teal,UnitX,21.f*Scale,25.f,840.f*Scale);
        Label(Unit->IsKrag()?TEXT("Heavy armor and industrial bionics."):TEXT("Restores ordinary function. No upgrades."),Muted,UnitX,59.f*Scale,15.f,840.f*Scale);
        const FString ActionLabel=Unit->IsFaceActing() && Unit->GetActionLabel()==TEXT("Idle")?TEXT("EXPRESSION"):Unit->GetActionLabel().ToUpper();
        Label(ActionLabel,Teal,Canvas->SizeX-Left,Bottom+30.f*Scale,24.f,280.f*Scale,true);
    }
    const float ControlsWidth=Canvas->SizeX-Left-350.f*Scale;
    Label(TEXT("SELECT  Left click    RUN  Right click    WALK  Shift + Right click    MELEE  A    SHOOT  F    HIT  H    BIONICS  V    NEXT  Tab"),Text,Left,Bottom+20.f*Scale,19.f,ControlsWidth);
    Label(TEXT("FACE  E    PORTRAIT  C    CAMERA  Arrows / Middle drag / Scroll    RESET  Home    EXIT  Esc"),Muted,Left,Bottom+58.f*Scale,16.f,ControlsWidth);
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
    // UE's submix auto-disable returns before the recording buffer append on
    // silent blocks. Keep the audio clock continuous only for this recording;
    // otherwise silent intervals disappear and sound no longer matches video.
    if(IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("au.NeverDisableSubmixes")))
    {
        ShowcasePreviousNeverDisableSubmixes=CVar->GetInt();
        CVar->Set(1,ECVF_SetByCode);
        UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_AUDIO_CONTINUOUS previous=%d actual=%d"),ShowcasePreviousNeverDisableSubmixes,CVar->GetInt());
    }
    const FString AudioStartUtc=FDateTime::UtcNow().ToIso8601();
    UAudioMixerBlueprintLibrary::StartRecordingOutput(this,75.f,nullptr);bShowcaseAudioRecording=true;
    ShowcaseStartTime=FPlatformTime::Seconds();UE_LOG(LogTemp,Display,TEXT("KK_SHOWCASE_STARTED utc=%s"),*AudioStartUtc);
}
void AKKBenchmarkGameMode::FinishShowcaseRecording()
{
    if(!bShowcaseAudioRecording)return;bShowcaseAudioRecording=false;
    const FString AudioDir=FPaths::ConvertRelativePathToFull(FPaths::GetPath(ShowcaseGate));IFileManager::Get().MakeDirectory(*AudioDir,true);
    UAudioMixerBlueprintLibrary::StopRecordingOutput(this,EAudioRecordingExportType::WavFile,TEXT("showcase-engine-audio"),AudioDir,nullptr);
    // StopRecordingOutput copies the stopped buffer before asynchronous WAV IO.
    if(ShowcasePreviousNeverDisableSubmixes!=INDEX_NONE)
    {
        if(IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("au.NeverDisableSubmixes")))CVar->Set(ShowcasePreviousNeverDisableSubmixes,ECVF_SetByCode);
        ShowcasePreviousNeverDisableSubmixes=INDEX_NONE;
    }
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
        case 13:PC->FocusActionPortrait(Krag);Krag->PlayDemoAction(TEXT("Melee"));break;
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
            SmokeCheck(DemoUnits[0]->GetShotEventCount()>=2,TEXT("Krag emitted both authored discharges from animated weapon markers"));
            SmokeCheck(DemoUnits[0]->GetShotEventCount()>=2 && DemoUnits[0]->GetMaximumShotForwardAngle()<=10.f,TEXT("Krag actual discharge marker direction within 10-degree repaired-aim regression tolerance"));
            SmokeCheck(DemoUnits[1]->GetShotEventCount()>=2,TEXT("Nib emitted authored discharges from animated weapon markers"));
            FScreenshotRequest::RequestScreenshot(EvidenceDir/TEXT("smoke-final.png"),true,false);NextSmokeTime=71;break;
        case 10:
        {
            const FString Report=FString::Printf(TEXT("{\n  \"source\": \"runtime scripted exercise; see launch evidence for editor-game or standalone process\",\n  \"mouse_keyboard_delivery_tested\": false,\n  \"failures\": %d,\n  \"checks\": [\n%s\n  ],\n  \"shots\":{\"Krag\":%s,\"Nib\":%s}\n}\n"),SmokeFailures,*SmokeResults,*DemoUnits[0]->GetShotDiagnosticsJson(),*DemoUnits[1]->GetShotDiagnosticsJson());
            FFileHelper::SaveStringToFile(Report,*(EvidenceDir/TEXT("smoke-report.json")));
            UE_LOG(LogTemp,Display,TEXT("KK_SMOKE_COMPLETE failures=%d"),SmokeFailures);
            bSmoke=false;UKismetSystemLibrary::QuitGame(this,PC,EQuitPreference::Quit,false);break;
        }
        default:bSmoke=false;break;
    }
    ++SmokePhase;
}
