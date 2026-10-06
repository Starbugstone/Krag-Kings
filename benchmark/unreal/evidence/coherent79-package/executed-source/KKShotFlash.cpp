#include "KKShotFlash.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "Engine/StaticMesh.h"

AKKShotFlash::AKKShotFlash()
{
    PrimaryActorTick.bCanEverTick=true;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Origin"));
    Flash=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MuzzleFlash"));Flash->SetupAttachment(RootComponent);
    Tracer=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VisualTracer"));Tracer->SetupAttachment(RootComponent);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    for(auto* Component:{Flash.Get(),Tracer.Get()})
    {
        Component->SetStaticMesh(Sphere.Object);Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCastShadow(false);Component->bReceivesDecals=false;
    }
    Light=CreateDefaultSubobject<UPointLightComponent>(TEXT("ShotLight"));Light->SetupAttachment(RootComponent);
    Light->SetCastShadows(false);Light->SetLightColor(FLinearColor(1.f,.56f,.19f));Light->SetAttenuationRadius(140.f);
    SetLifeSpan(.12f);
}
void AKKShotFlash::InitializeFlash(UMaterialInterface* Material,const FVector& Direction,const FVector& End,bool bKrag)
{
    const FRotator Rotation=Direction.Rotation();const FVector Origin=GetActorLocation();
    Flash->SetWorldLocationAndRotation(Origin+Direction*(bKrag?8.f:5.f),Rotation);
    Flash->SetWorldScale3D(bKrag?FVector(.23f,.075f,.055f):FVector(.14f,.04f,.03f));
    const float Length=FVector::Dist(Origin,End);
    Tracer->SetWorldLocationAndRotation((Origin+End)*.5f,Rotation);
    Tracer->SetWorldScale3D(FVector(Length/100.f,.002f,.002f));
    FlashMaterial=UMaterialInstanceDynamic::Create(Material,this);TracerMaterial=UMaterialInstanceDynamic::Create(Material,this);
    Flash->SetMaterial(0,FlashMaterial);Tracer->SetMaterial(0,TracerMaterial);
    Light->SetIntensity(bKrag?120.f:55.f);
}
void AKKShotFlash::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);Age+=DeltaSeconds;
    if(FlashMaterial)FlashMaterial->SetScalarParameterValue(TEXT("Intensity"),FMath::Max(0.f,1.f-Age/.065f));
    if(TracerMaterial)TracerMaterial->SetScalarParameterValue(TEXT("Intensity"),.25f*FMath::Max(0.f,1.f-Age/.08f));
    if(Age>=.065f)Light->SetIntensity(0.f);
}
