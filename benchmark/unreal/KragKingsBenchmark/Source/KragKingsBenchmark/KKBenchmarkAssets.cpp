#include "KKBenchmarkAssets.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#endif

TArray<FName> UKKBenchmarkAssets::GetMeshBoneNames(USkeletalMesh* Mesh)
{
    TArray<FName> Names;
    if(Mesh)
    {
        const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
        for(int32 Index=0;Index<Ref.GetNum();Index++)Names.Add(Ref.GetBoneName(Index));
    }
    return Names;
}
TMap<FName,FName> UKKBenchmarkAssets::GetMeshBoneParents(USkeletalMesh* Mesh)
{
    TMap<FName,FName> Parents;
    if(Mesh)
    {
        const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
        for(int32 Index=0;Index<Ref.GetNum();++Index)
        {
            const int32 Parent=Ref.GetParentIndex(Index);
            Parents.Add(Ref.GetBoneName(Index),Parent==INDEX_NONE?NAME_None:Ref.GetBoneName(Parent));
        }
    }
    return Parents;
}
TMap<FName,FTransform> UKKBenchmarkAssets::GetMeshBoneReferenceTransforms(USkeletalMesh* Mesh)
{
    TMap<FName,FTransform> Transforms;
    if(Mesh)
    {
        const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
        for(int32 Index=0;Index<Ref.GetNum();++Index)Transforms.Add(Ref.GetBoneName(Index),Ref.GetRefBonePose()[Index]);
    }
    return Transforms;
}
TArray<FName> UKKBenchmarkAssets::GetAnimationBoneNames(UAnimSequence* Clip)
{
    TArray<FName> Names;
#if WITH_EDITOR
    if(Clip && Clip->GetDataModel())Clip->GetDataModel()->GetBoneTrackNames(Names);
#endif
    return Names;
}
TArray<FTransform> UKKBenchmarkAssets::GetAnimationBoneTrackSamples(UAnimSequence* Clip,FName Bone)
{
    TArray<FTransform> Samples;
#if WITH_EDITOR
    if(Clip && Clip->GetDataModel())Clip->GetDataModel()->GetBoneTrackTransforms(Bone,Samples);
#endif
    return Samples;
}
TMap<FName,FVector> UKKBenchmarkAssets::GetMeshBoneReferenceScales(USkeletalMesh* Mesh)
{
    TMap<FName,FVector> Scales;
    if(Mesh)
    {
        const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
        for(int32 Index=0;Index<Ref.GetNum();++Index)Scales.Add(Ref.GetBoneName(Index),Ref.GetRefBonePose()[Index].GetScale3D());
    }
    return Scales;
}
TArray<FName> UKKBenchmarkAssets::GetFaciallyAnimatedBones(UAnimSequence* Clip,USkeletalMesh* Mesh)
{
    TArray<FName> Animated;
#if WITH_EDITOR
    if(!Clip || !Mesh || !Clip->GetDataModel())return Animated;
    const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();const int32 FaceRoot=Ref.FindBoneIndex(TEXT("FaceRoot"));
    for(const FName Name:GetAnimationBoneNames(Clip))
    {
        int32 Bone=Ref.FindBoneIndex(Name);bool bFacial=false;
        while(Bone!=INDEX_NONE){if(Bone==FaceRoot){bFacial=true;break;}Bone=Ref.GetParentIndex(Bone);}
        if(!bFacial)continue;
        TArray<FTransform> Keys;Clip->GetDataModel()->GetBoneTrackTransforms(Name,Keys);
        if(Keys.Num()>1)for(const FTransform& Key:Keys)
        {
            if(FVector::DistSquared(Key.GetLocation(),Keys[0].GetLocation())>1.e-6f || Key.GetRotation().AngularDistance(Keys[0].GetRotation())>1.e-4f)
            {Animated.Add(Name);break;}
        }
    }
#endif
    return Animated;
}

FVector UKKBenchmarkAssets::GetMeshImportedSizeMeters(USkeletalMesh* Mesh)
{
    return Mesh?Mesh->GetBounds().BoxExtent*.02f:FVector::ZeroVector;
}

TMap<FName,FVector2D> UKKBenchmarkAssets::GetAnimationLimbTranslationRatios(UAnimSequence* Clip,USkeletalMesh* Mesh)
{
    TMap<FName,FVector2D> Ratios;
#if WITH_EDITOR
    if(!Clip || !Mesh || !Clip->GetDataModel())return Ratios;
    const FReferenceSkeleton& Ref=Mesh->GetRefSkeleton();
    for(const FName Bone:{FName("Thigh_L"),FName("Thigh_R"),FName("Shin_L"),FName("Shin_R"),FName("UpperArm_L"),FName("UpperArm_R"),FName("LowerArm_L"),FName("LowerArm_R")})
    {
        const int32 Index=Ref.FindBoneIndex(Bone);if(Index==INDEX_NONE)continue;
        const double BindLength=Ref.GetRefBonePose()[Index].GetTranslation().Size();if(BindLength<1.e-6)continue;
        TArray<FTransform> Keys;Clip->GetDataModel()->GetBoneTrackTransforms(Bone,Keys);if(Keys.IsEmpty())continue;
        FVector2D Range(TNumericLimits<double>::Max(),0);
        for(const FTransform& Key:Keys){const double Ratio=Key.GetTranslation().Size()/BindLength;Range.X=FMath::Min(Range.X,Ratio);Range.Y=FMath::Max(Range.Y,Ratio);}
        Ratios.Add(Bone,Range);
    }
#endif
    return Ratios;
}
