#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "KKBenchmarkAssets.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UStaticMesh;
class UMaterialInterface;
class USoundBase;

USTRUCT(BlueprintType)
struct FKKMorphDriver
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName Morph;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName Bone;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) FName Channel;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float Start=0.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float End=1.f;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) float MaxWeight=1.f;
};

USTRUCT(BlueprintType)
struct FKKCharacterVariant
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Label;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<USkeletalMesh> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Run;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Walk;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Melee;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Shoot;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> Hit;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UAnimSequence> FacePerformance;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FKKMorphDriver> MorphDrivers;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName WeaponMuzzleBone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName WeaponAimBone;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<float> FireTimesNormalized;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float WalkSpeedMeters=1.15f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float RunSpeedMeters=3.2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float WalkCycleSeconds=0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float RunCycleSeconds=0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float WalkStanceFraction=.62f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float RunStanceFraction=.42f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<float> WalkLeftContacts={0.f};
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<float> WalkRightContacts={.5f};
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<float> RunLeftContacts={0.f};
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<float> RunRightContacts={.5f};
};

UCLASS(BlueprintType)
class KRAGKINGSBENCHMARK_API UKKBenchmarkAssets : public UDataAsset
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Benchmark validation")
    static TArray<FName> GetMeshBoneNames(USkeletalMesh* Mesh);
    UFUNCTION(BlueprintCallable,Category="Benchmark validation")
    static TArray<FName> GetAnimationBoneNames(UAnimSequence* Clip);
    UFUNCTION(BlueprintCallable,Category="Benchmark validation")
    static TArray<FName> GetFaciallyAnimatedBones(UAnimSequence* Clip,USkeletalMesh* Mesh);
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FKKCharacterVariant> Krags;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FKKCharacterVariant> Nibs;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UStaticMesh> Terrain;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UMaterialInterface> SandMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FRotator MeshRotation = FRotator(0,-90,0);
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<USoundBase>> KragSandSteps;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TArray<TObjectPtr<USoundBase>> NibSandSteps;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> SandDustMaterial;
    UPROPERTY(EditAnywhere,BlueprintReadWrite) TObjectPtr<UMaterialInterface> WeaponFlashMaterial;
};
