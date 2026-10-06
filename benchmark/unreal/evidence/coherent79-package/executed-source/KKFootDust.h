#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KKFootDust.generated.h"
class UMaterialBillboardComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
UCLASS()
class KRAGKINGSBENCHMARK_API AKKFootDust : public AActor
{
    GENERATED_BODY()
public:
    AKKFootDust();
    void InitializeDust(UMaterialInterface* Material,bool bKrag,bool bWalking,const FVector& Normal);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UMaterialBillboardComponent> Sprite;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> DynamicMaterial;
    FVector Drift=FVector::ZeroVector;
    float Age=0.f,Duration=.5f,Opacity=.25f;
};
