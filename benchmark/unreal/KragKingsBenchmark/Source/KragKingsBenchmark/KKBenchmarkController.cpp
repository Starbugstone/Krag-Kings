#include "KKBenchmarkController.h"
#include "KKBenchmarkUnit.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "InputCoreTypes.h"
#include "Components/SkeletalMeshComponent.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

AKKBenchmarkController::AKKBenchmarkController()
{
    bShowMouseCursor=true;
    DefaultMouseCursor=EMouseCursor::Default;
}
void AKKBenchmarkController::BeginPlay()
{
    Super::BeginPlay();
    bPerformanceLocked=FParse::Param(FCommandLine::Get(),TEXT("KKPerf")) || FParse::Param(FCommandLine::Get(),TEXT("KKShowcase"));
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
void AKKBenchmarkController::ResetCamera(){bPortrait=false;PortraitPan=FVector::ZeroVector;Focus=FVector(-7.5f,5.f,205.f);Distance=850;Yaw=75;Pitch=-22;}
void AKKBenchmarkController::ZoomIn(){if(!bPerformanceLocked)Distance=FMath::Max(bPortrait?60.f:260.f,Distance*.9f);}
void AKKBenchmarkController::ZoomOut(){if(!bPerformanceLocked)Distance=FMath::Min(5200.f,Distance/ .9f);}
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
    if(GetHitResultUnderCursor(ECC_Visibility,false,Result))
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
    bPortrait=true;PortraitPan=FVector::ZeroVector;Distance=Unit->IsKrag()?135.f:95.f;
    Yaw=Unit->GetActorRotation().Yaw+180.f;Pitch=-3.f;
}
void AKKBenchmarkController::SetShowcaseCamera(const FVector& Target,float InYaw,float InPitch,float InDistance)
{bPortrait=false;Focus=Target;Yaw=InYaw;Pitch=InPitch;Distance=InDistance;}
void AKKBenchmarkController::Quit(){UKismetSystemLibrary::QuitGame(this,this,EQuitPreference::Quit,false);}
void AKKBenchmarkController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if(!BenchmarkCamera) return;
    if(!bPerformanceLocked && IsInputKeyDown(EKeys::MiddleMouseButton))
    {
        float DX,DY;GetInputMouseDelta(DX,DY);
        Yaw+=DX*.35f;Pitch=FMath::Clamp(Pitch+DY*.25f,-75.f,bPortrait?25.f:-8.f);
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
    else Focus+=PanDelta;
    Focus.X=FMath::Clamp(Focus.X,-3400.f,3400.f);Focus.Y=FMath::Clamp(Focus.Y,-3400.f,3400.f);
    const FRotator Rotation(Pitch,Yaw,0);
    BenchmarkCamera->SetActorLocationAndRotation(Focus-Rotation.Vector()*Distance,Rotation);
}
