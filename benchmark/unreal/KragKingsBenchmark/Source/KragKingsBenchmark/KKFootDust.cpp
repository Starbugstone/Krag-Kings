#include "KKFootDust.h"
#include "Components/MaterialBillboardComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AKKFootDust::AKKFootDust()
{
    PrimaryActorTick.bCanEverTick=true;
    Sprite=CreateDefaultSubobject<UMaterialBillboardComponent>(TEXT("SandContact"));
    RootComponent=Sprite;Sprite->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sprite->SetCastShadow(false);
}
void AKKFootDust::InitializeDust(UMaterialInterface* Material,bool bKrag,bool bWalking,const FVector& Normal)
{
    if(!Material){Destroy();return;}
    Duration=bKrag?.48f:.28f;Opacity=bKrag?.25f:.11f;
    if(!bWalking)Opacity*=1.15f;
    const float Radius=(bKrag?12.f:5.f)*(bWalking?1.f:1.25f);
    Drift=Normal*(bKrag?8.f:5.f)+FVector(2.f,1.f,0.f);
    DynamicMaterial=UMaterialInstanceDynamic::Create(Material,this);
    DynamicMaterial->SetScalarParameterValue(TEXT("Opacity"),0.f);
    Sprite->AddElement(DynamicMaterial,nullptr,false,Radius,Radius,nullptr);
    SetLifeSpan(Duration+.1f);
}
void AKKFootDust::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);Age+=DeltaSeconds;
    const float T=FMath::Clamp(Age/Duration,0.f,1.f);
    if(DynamicMaterial)DynamicMaterial->SetScalarParameterValue(TEXT("Opacity"),Opacity*FMath::Min(1.f,T/.08f)*FMath::Square(1.f-T));
    SetActorScale3D(FVector(1.f+.8f*T));AddActorWorldOffset(Drift*DeltaSeconds,false);
}
