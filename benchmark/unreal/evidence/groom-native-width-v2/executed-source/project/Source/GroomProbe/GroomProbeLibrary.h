#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GroomProbeLibrary.generated.h"
class UGroomAsset;

UCLASS()
class GROOMPROBE_API UGroomProbeLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Isolated groom fixture")
    static FString ReadDescription(UGroomAsset* Asset);
    UFUNCTION(BlueprintCallable,Category="Isolated groom fixture")
    static FString RestorePointWidths(UGroomAsset* Asset, const TArray<FVector>& ExpectedPositionsCentimeters,
        const TArray<int32>& ExpectedStrandPointCounts, const TArray<float>& WidthsCentimeters);
};
