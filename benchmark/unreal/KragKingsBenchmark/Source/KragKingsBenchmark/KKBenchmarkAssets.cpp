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
TArray<FName> UKKBenchmarkAssets::GetAnimationBoneNames(UAnimSequence* Clip)
{
    TArray<FName> Names;
#if WITH_EDITOR
    if(Clip && Clip->GetDataModel())Clip->GetDataModel()->GetBoneTrackNames(Names);
#endif
    return Names;
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
