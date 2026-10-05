#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KKShotFlash.generated.h"
class UStaticMeshComponent;
class UPointLightComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;

UCLASS()
class KRAGKINGSBENCHMARK_API AKKShotFlash : public AActor
{
    GENERATED_BODY()
public:
    AKKShotFlash();
    void InitializeFlash(UMaterialInterface* Material,const FVector& Direction,const FVector& End,bool bKrag);
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Flash;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Tracer;
    UPROPERTY() TObjectPtr<UPointLightComponent> Light;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> FlashMaterial;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> TracerMaterial;
    float Age=0.f;
};
