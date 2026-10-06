#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GroomCharacterLibrary.generated.h"

class USkeletalMesh;
class UGroomBindingAsset;
class UGroomAsset;

/** Isolated editor probes. No production/runtime module depends on this library. */
UCLASS()
class GROOMPROBE_API UGroomCharacterLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="GroomProbe")
    static FString ApplyVerifiedStrandSidecar(UGroomAsset* Groom,
        const TArray<FVector>& PositionsCentimeters, const TArray<int32>& StrandPointCounts,
        const TArray<float>& DiametersCentimeters, const TArray<FVector>& ColorsLinearRgb,
        float PositionToleranceCentimeters);

    UFUNCTION(BlueprintCallable, Category="GroomProbe")
    static FString EnableAndReadBindingMask(USkeletalMesh* Mesh, FName AttributeName);

    UFUNCTION(BlueprintCallable, Category="GroomProbe")
    static FString ReadBindingProjection(UGroomBindingAsset* Binding, FName AttributeName);

    UFUNCTION(BlueprintCallable, Category="GroomProbe")
    static FString BuildMaskedBinding(UGroomBindingAsset* Binding, UGroomAsset* Groom,
        USkeletalMesh* Mesh, FName AttributeName);
};
