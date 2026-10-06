#include "KKBenchmarkController.h"
#include "KKBenchmarkUnit.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "InputCoreTypes.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "GameFramework/PlayerInput.h"

AKKBenchmarkController::AKKBenchmarkController()
{
    bShowMouseCursor=true;
    DefaultMouseCursor=EMouseCursor::Default;
}
void AKKBenchmarkController::BeginPlay()
{
    Super::BeginPlay();
    bPerformanceLocked=FParse::Param(FCommandLine::Get(),TEXT("KKPerf")) || FParse::Param(FCommandLine::Get(),TEXT("KKPerfMoving")) || FParse::Param(FCommandLine::Get(),TEXT("KKShowcase")) || FParse::Param(FCommandLine::Get(),TEXT("KKSkinReview"));
    FInputModeGameAndUI Mode;
    Mode.SetHideCursorDuringCapture(false);
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    SetInputMode(Mode);
    BenchmarkCamera=GetWorld()->SpawnActor<ACameraActor>();
    BenchmarkCamera->GetCameraComponent()->SetFieldOfView(62.9448f);
    BenchmarkCamera->GetCameraComponent()->PostProcessSettings.bOverride_MotionBlurAmount=true;
    BenchmarkCamera->GetCameraComponent()->PostProcessSettings.MotionBlurAmount=0;
    SetViewTarget(BenchmarkCamera);
    ResetCamera();
    if(!Selected) NextUnit();
}
void AKKBenchmarkController::SetupInputComponent()
{
    Super::SetupInputComponent();
    InputComponent->BindKey(EKeys::LeftMouseButton,IE_Pressed,this,&AKKBenchmarkController::SelectAtCursor);
    InputComponent->BindKey(EKeys::RightMouseButton,IE_Pressed,this,&AKKBenchmarkController::MoveAtCursor);
    InputComponent->BindKey(EKeys::Tab,IE_Pressed,this,&AKKBenchmarkController::NextUnit);
    InputComponent->BindKey(EKeys::A,IE_Pressed,this,&AKKBenchmarkController::Melee);
    InputComponent->BindKey(EKeys::F,IE_Pressed,this,&AKKBenchmarkController::Shoot);
    InputComponent->BindKey(EKeys::H,IE_Pressed,this,&AKKBenchmarkController::Hit);
    InputComponent->BindKey(EKeys::V,IE_Pressed,this,&AKKBenchmarkController::Variant);
    InputComponent->BindKey(EKeys::E,IE_Pressed,this,&AKKBenchmarkController::FacePerformance);
    InputComponent->BindKey(EKeys::C,IE_Pressed,this,&AKKBenchmarkController::TogglePortrait);
    InputComponent->BindKey(EKeys::F8,IE_Pressed,this,&AKKBenchmarkController::CaptureReview);
    InputComponent->BindKey(EKeys::Home,IE_Pressed,this,&AKKBenchmarkController::ResetCamera);
    InputComponent->BindKey(EKeys::Escape,IE_Pressed,this,&AKKBenchmarkController::Quit);
    InputComponent->BindKey(EKeys::MouseScrollUp,IE_Pressed,this,&AKKBenchmarkController::ZoomIn);
    InputComponent->BindKey(EKeys::MouseScrollDown,IE_Pressed,this,&AKKBenchmarkController::ZoomOut);
}
bool AKKBenchmarkController::InputKey(const FInputKeyEventArgs& Params)
{
    if(FParse::Param(FCommandLine::Get(),TEXT("KKInputState")) && Params.Key.IsMouseButton())
    {
        float X=0,Y=0;const bool bPointer=GetMousePosition(X,Y);
        UE_LOG(LogTemp,Display,TEXT("KK_INPUT_MOUSE key=%s event=%d pointer=%d xy=(%.2f,%.2f)"),*Params.Key.ToString(),int32(Params.Event),bPointer?1:0,X,Y);
    }
    return Super::InputKey(Params);
}
void AKKBenchmarkController::ResetCamera()
{
    bPortrait=false;PortraitPan=FVector::ZeroVector;Focus=FVector(-7.5f,-5.f,205.f);
    FVector UnitFeet=FVector::ZeroVector;int32 Count=0;
    for(TActorIterator<AKKBenchmarkUnit> It(GetWorld());It;++It)
    {UnitFeet+=It->GetActorLocation()-FVector(0,0,It->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());++Count;}
    if(Count)Focus=UnitFeet/Count+FVector(0,0,95.f);
    Distance=640;Yaw=75;Pitch=-22;
}
void AKKBenchmarkController::ZoomIn(){if(!bPerformanceLocked)Distance=FMath::Max(bPortrait?60.f:260.f,Distance*.9f);}
void AKKBenchmarkController::ZoomOut(){if(!bPerformanceLocked)Distance=FMath::Min(2800.f,Distance/ .9f);}
void AKKBenchmarkController::SelectUnit(AKKBenchmarkUnit* Unit)
{
    if(Selected) Selected->SetSelected(false);
    Selected=Unit;
    if(Selected){Selected->SetSelected(true);UE_LOG(LogTemp,Display,TEXT("KK_SELECTED %s"),*Selected->GetVariantLabel());}
}
void AKKBenchmarkController::SelectAtCursor()
{
    if(bPerformanceLocked)return;
    FHitResult Result;
    const bool bHit=GetHitResultUnderCursor(ECC_Visibility,false,Result);
    if(FParse::Param(FCommandLine::Get(),TEXT("KKInputState")))
        UE_LOG(LogTemp,Display,TEXT("KK_SELECT_TRACE hit=%d actor=%s point=%s"),bHit?1:0,*GetNameSafe(Result.GetActor()),*Result.ImpactPoint.ToString());
    if(bHit)
        if(auto* Unit=Cast<AKKBenchmarkUnit>(Result.GetActor())) SelectUnit(Unit);
}
void AKKBenchmarkController::MoveAtCursor()
{
    if(bPerformanceLocked || !Selected) return;
    FHitResult Result;
    if(GetHitResultUnderCursor(ECC_Visibility,true,Result) && !Cast<AKKBenchmarkUnit>(Result.GetActor())) Selected->MoveTo(Result.ImpactPoint,IsInputKeyDown(EKeys::LeftShift)||IsInputKeyDown(EKeys::RightShift));
}
void AKKBenchmarkController::NextUnit()
{
    if(bPerformanceLocked)return;
    TArray<AKKBenchmarkUnit*> Units;
    for(TActorIterator<AKKBenchmarkUnit> It(GetWorld());It;++It) Units.Add(*It);
    if(Units.Num()) SelectUnit(Units[(Units.IndexOfByKey(Selected)+1)%Units.Num()]);
}
void AKKBenchmarkController::Melee(){if(!bPerformanceLocked && Selected) Selected->PlayDemoAction("Melee");}
void AKKBenchmarkController::Shoot(){if(!bPerformanceLocked && Selected) Selected->PlayDemoAction("Shoot");}
void AKKBenchmarkController::Hit(){if(!bPerformanceLocked && Selected) Selected->PlayDemoAction("Hit");}
void AKKBenchmarkController::Variant(){if(!bPerformanceLocked && Selected) Selected->CycleVariant();}
void AKKBenchmarkController::FacePerformance(){if(!bPerformanceLocked && Selected)Selected->PlayFacePerformance();}
void AKKBenchmarkController::CaptureReview()
{
    if(bPerformanceLocked)return;
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("Benchmark");IFileManager::Get().MakeDirectory(*Dir,true);
    FScreenshotRequest::RequestScreenshot(Dir/TEXT("input-review.png"),true,true);
}
void AKKBenchmarkController::TogglePortrait()
{
    if(bPerformanceLocked)return;
    if(bPortrait){ResetCamera();return;}
    FocusPortrait(Selected);
}
void AKKBenchmarkController::FocusPortrait(AKKBenchmarkUnit* Unit)
{
    if(!Unit)return;SelectUnit(Unit);
    bPortrait=true;PortraitPan=FVector::ZeroVector;Distance=Unit->IsKrag()?135.f:145.f;
    Yaw=Unit->GetActorRotation().Yaw+180.f;Pitch=-3.f;
}
void AKKBenchmarkController::FocusActionPortrait(AKKBenchmarkUnit* Unit)
{
    if(!Unit)return;FocusPortrait(Unit);
    // The fixed head portrait crops Krag's foreshortened firearm. This separate
    // showcase view keeps the face and the active upper-body weapon together.
    Distance=240.f;PortraitPan=FVector(0,0,-18.f);Yaw+=15.f;
}
void AKKBenchmarkController::SetShowcaseFraming(const FBox& VisibleBounds,float InYaw,float InPitch,float DeltaSeconds)
{
    if(!VisibleBounds.IsValid || !BenchmarkCamera)return;
    bPortrait=false;Focus=VisibleBounds.GetCenter();Yaw=InYaw;Pitch=InPitch;
    int32 Width=1920,Height=1080;GetViewportSize(Width,Height);
    const float Aspect=Height>0?float(Width)/Height:16.f/9.f;
    const float TanHorizontal=FMath::Tan(FMath::DegreesToRadians(BenchmarkCamera->GetCameraComponent()->FieldOfView*.5f));
    const float TanVertical=TanHorizontal/FMath::Max(.01f,Aspect);
    const FRotator ViewRotation(InPitch,InYaw,0.f);
    float RequiredDistance=640.f;
    for(int32 Corner=0;Corner<8;++Corner)
    {
        const FVector WorldPoint(Corner&1?VisibleBounds.Max.X:VisibleBounds.Min.X,
                                 Corner&2?VisibleBounds.Max.Y:VisibleBounds.Min.Y,
                                 Corner&4?VisibleBounds.Max.Z:VisibleBounds.Min.Z);
        const FVector ViewPoint=ViewRotation.UnrotateVector(WorldPoint-Focus);
        // Unreal view X is forward, Y right, Z up. Reserve matched HUD margins.
        RequiredDistance=FMath::Max(RequiredDistance,float(FMath::Abs(ViewPoint.Y)/(TanHorizontal*.88f)-ViewPoint.X));
        RequiredDistance=FMath::Max(RequiredDistance,float(FMath::Abs(ViewPoint.Z)/(TanVertical*.73f)-ViewPoint.X));
    }
    // Widen immediately to retain feet/ears; shrink gently at 0.55m/s.
    Distance=RequiredDistance>Distance?RequiredDistance:FMath::Max(RequiredDistance,Distance-55.f*FMath::Max(0.f,DeltaSeconds));
}
void AKKBenchmarkController::Quit(){UKismetSystemLibrary::QuitGame(this,this,EQuitPreference::Quit,false);}
void AKKBenchmarkController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if(!BenchmarkCamera) return;
    if(!bPerformanceLocked && IsInputKeyDown(EKeys::MiddleMouseButton))
    {
        float DX,DY;GetInputMouseDelta(DX,DY);
        // DefaultInput supplies unit mouse axes without template FOV scaling or
        // smoothing. These explicit degrees/count match the Unity inspection camera.
        Yaw+=DX*.17f;Pitch=FMath::Clamp(Pitch+DY*.13f,-75.f,bPortrait?25.f:-8.f);
        if(FParse::Param(FCommandLine::Get(),TEXT("KKInputState")) && (!FMath::IsNearlyZero(DX) || !FMath::IsNearlyZero(DY)))
        {
            UE_LOG(LogTemp,Display,TEXT("KK_INPUT_ORBIT raw=(%.3f,%.3f) processed=(%.3f,%.3f) sensitivity=(%.3f,%.3f) yaw=%.3f pitch=%.3f action=%s"),
                PlayerInput?PlayerInput->GetRawKeyValue(EKeys::MouseX):0.f,PlayerInput?PlayerInput->GetRawKeyValue(EKeys::MouseY):0.f,DX,DY,
                PlayerInput?PlayerInput->GetMouseSensitivityX():0.f,PlayerInput?PlayerInput->GetMouseSensitivityY():0.f,Yaw,Pitch,
                Selected?*Selected->GetActionLabel():TEXT("None"));
        }
    }
    const FRotator PanRotation(0,Yaw,0);
    const FVector Forward=PanRotation.Vector(),Right=FRotationMatrix(PanRotation).GetUnitAxis(EAxis::Y);
    FVector Pan=FVector::ZeroVector;
    if(!bPerformanceLocked)
    {
        if(IsInputKeyDown(EKeys::Up)) Pan+=Forward;
        if(IsInputKeyDown(EKeys::Down)) Pan-=Forward;
        if(IsInputKeyDown(EKeys::Right)) Pan+=Right;
        if(IsInputKeyDown(EKeys::Left)) Pan-=Right;
    }
    const FVector PanDelta=Pan.GetClampedToMaxSize(1)*DeltaTime*Distance*.6f;
    if(bPortrait && Selected){PortraitPan+=PanDelta;Focus=Selected->GetMesh()->GetSocketLocation(TEXT("Head"))+FVector(0,0,5.f)+PortraitPan;}
    else if(!PanDelta.IsNearlyZero())
    {
        FHitResult PriorGround,NextGround;FCollisionQueryParams PanParams;
        const bool bPriorGround=GetWorld()->LineTraceSingleByObjectType(PriorGround,FVector(Focus.X,Focus.Y,6000.f),FVector(Focus.X,Focus.Y,-6000.f),FCollisionObjectQueryParams(ECC_WorldStatic),PanParams);
        const float HeightAboveGround=bPriorGround?Focus.Z-PriorGround.ImpactPoint.Z:0.f;
        Focus+=PanDelta;
        Focus.X=FMath::Clamp(Focus.X,-70000.f,70000.f);Focus.Y=FMath::Clamp(Focus.Y,-70000.f,70000.f);
        if(bPriorGround && GetWorld()->LineTraceSingleByObjectType(NextGround,FVector(Focus.X,Focus.Y,6000.f),FVector(Focus.X,Focus.Y,-6000.f),FCollisionObjectQueryParams(ECC_WorldStatic),PanParams))Focus.Z=NextGround.ImpactPoint.Z+HeightAboveGround;
    }
    Focus.X=FMath::Clamp(Focus.X,-70000.f,70000.f);Focus.Y=FMath::Clamp(Focus.Y,-70000.f,70000.f);
    const FRotator Rotation(Pitch,Yaw,0);
    FVector CameraPosition=Focus-Rotation.Vector()*Distance;
    FHitResult Ground;FCollisionQueryParams Params;
    if(GetWorld()->LineTraceSingleByObjectType(Ground,CameraPosition+FVector(0,0,5000),CameraPosition-FVector(0,0,10000),FCollisionObjectQueryParams(ECC_WorldStatic),Params))
        CameraPosition.Z=FMath::Max(CameraPosition.Z,Ground.ImpactPoint.Z+40.f);
    BenchmarkCamera->SetActorLocationAndRotation(CameraPosition,(Focus-CameraPosition).Rotation());
}
