#include "GroomCharacterLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"
#include "AssetCompilingManager.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshAttributeVertexBuffer.h"
#include "GroomAsset.h"
#include "GroomBindingAsset.h"
#include "GroomBindingBuilder.h"
#include "HairDescription.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
FString ToJson(const TSharedRef<FJsonObject>& Object)
{
    FString Text;
    FJsonSerializer::Serialize(Object,TJsonWriterFactory<>::Create(&Text));
    return Text;
}
FString Failure(const FString& Message)
{
    auto Result=MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("error"),Message);
    return ToJson(Result);
}
bool ReadMask(const FSkeletalMeshLODRenderData& LOD,FName Name,TArray<float>& Values)
{
    const auto* Attribute=LOD.VertexAttributeBuffers.GetAttributeBuffer(Name);
    if(!Attribute) return false;
    const auto CPU=Attribute->GetCPUData();
    if(!CPU.Data || CPU.PixelFormat!=PF_R32_FLOAT || CPU.Data->GetNumVertices()!=LOD.GetNumVertices()) return false;
    Values.SetNumUninitialized(LOD.GetNumVertices());
    for(int32 Index=0;Index<Values.Num();++Index)
    {
        FMemory::Memcpy(&Values[Index],CPU.Data->GetDataPointer()+Index*CPU.Data->GetStride(),sizeof(float));
        if(Values[Index]!=0.f && Values[Index]!=1.f) return false;
    }
    return true;
}
}

FString UGroomCharacterLibrary::ApplyVerifiedStrandSidecar(UGroomAsset* Groom,
    const TArray<FVector>& PositionsCentimeters,const TArray<int32>& StrandPointCounts,
    const TArray<float>& DiametersCentimeters,const TArray<FVector>& ColorsLinearRgb,
    float PositionToleranceCentimeters)
{
    // The character ABC's independently measured roundtrip differs from the tiny fixture.
    // Require the caller to declare a bounded tolerance, rather than weakening that fixture.
    if(!Groom || !FMath::IsFinite(PositionToleranceCentimeters) || PositionToleranceCentimeters<=0.f || PositionToleranceCentimeters>0.001f)
        return Failure(TEXT("Missing groom or invalid explicit positional tolerance (maximum 10 micrometers)"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    FHairDescription Description=Groom->GetHairDescription();
    if(Description.GetNumVertices()!=PositionsCentimeters.Num() || Description.GetNumVertices()!=DiametersCentimeters.Num() ||
       Description.GetNumVertices()!=ColorsLinearRgb.Num() || Description.GetNumStrands()!=StrandPointCounts.Num())
        return Failure(TEXT("Sidecar count mismatch"));
    const auto ImportedPositions=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Position);
    const auto ImportedCounts=Description.StrandAttributes().GetAttributesRef<int>(HairAttribute::Strand::VertexCount);
    if(!ImportedPositions.IsValid()||!ImportedCounts.IsValid()) return Failure(TEXT("Missing native point topology"));
    double MaximumPositionComponentError=0.;
    for(int32 Curve=0;Curve<StrandPointCounts.Num();++Curve)
        if(ImportedCounts[FStrandID(Curve)]!=StrandPointCounts[Curve]) return Failure(TEXT("Sidecar curve topology/order mismatch"));
    for(int32 Point=0;Point<PositionsCentimeters.Num();++Point)
    {
        const FVector Delta=FVector(ImportedPositions[FVertexID(Point)])-PositionsCentimeters[Point];
        if(Delta.ContainsNaN()||Delta.GetAbsMax()>PositionToleranceCentimeters) return Failure(TEXT("Sidecar position/order/coordinate mismatch"));
        MaximumPositionComponentError=FMath::Max(MaximumPositionComponentError,Delta.GetAbsMax());
        if(!FMath::IsFinite(DiametersCentimeters[Point])||DiametersCentimeters[Point]<=0.f||ColorsLinearRgb[Point].ContainsNaN()||
           ColorsLinearRgb[Point].GetMin()<0. || ColorsLinearRgb[Point].GetMax()>1.) return Failure(TEXT("Invalid sidecar width or linear color"));
    }
    auto Widths=Description.VertexAttributes().GetAttributesRef<float>(HairAttribute::Vertex::Width);
    if(!Widths.IsValid())
    {
        Description.VertexAttributes().RegisterAttribute<float>(HairAttribute::Vertex::Width);
        Widths=Description.VertexAttributes().GetAttributesRef<float>(HairAttribute::Vertex::Width);
    }
    auto Colors=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Color);
    if(!Colors.IsValid())
    {
        Description.VertexAttributes().RegisterAttribute<FVector3f>(HairAttribute::Vertex::Color);
        Colors=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Color);
    }
    for(int32 Point=0;Point<PositionsCentimeters.Num();++Point)
    {
        Widths[FVertexID(Point)]=DiametersCentimeters[Point];
        Colors[FVertexID(Point)]=FVector3f(ColorsLinearRgb[Point]);
    }
    Groom->Modify();
    Groom->CommitHairDescription(MoveTemp(Description),EHairDescriptionType::Source);
    if(!Groom->CacheDerivedDatas()) return Failure(TEXT("Native groom rebuild failed"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    Groom->MarkPackageDirty();
    auto Result=MakeShared<FJsonObject>();
    Result->SetNumberField(TEXT("verifiedPoints"),PositionsCentimeters.Num());
    Result->SetNumberField(TEXT("verifiedCurves"),StrandPointCounts.Num());
    Result->SetNumberField(TEXT("positionToleranceCentimeters"),PositionToleranceCentimeters);
    Result->SetNumberField(TEXT("maximumPositionComponentErrorCentimeters"),MaximumPositionComponentError);
    Result->SetBoolField(TEXT("exactDiameterAndLinearColorApplied"),true);
    Result->SetBoolField(TEXT("abcRootUvNotClaimed"),true);
    Result->SetBoolField(TEXT("rendered"),false);
    return ToJson(Result);
}

FString UGroomCharacterLibrary::EnableAndReadBindingMask(USkeletalMesh* Mesh,FName AttributeName)
{
    if(!Mesh || AttributeName.IsNone()) return Failure(TEXT("Missing mesh or explicit binding attribute"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    FSkeletalMeshLODInfo* LODInfo=Mesh->GetLODInfo(0);
    if(!LODInfo) return Failure(TEXT("No imported LOD0"));
    auto* Attribute=LODInfo->VertexAttributes.FindByPredicate([&](const auto& Item){return Item.Name==AttributeName;});
    if(!Attribute) return Failure(TEXT("Required imported mask missing; refuse all-vertices fallback"));
    Mesh->Modify();
    Attribute->EnabledForRender.Default=true;
    Attribute->DataType=ESkeletalMeshVertexAttributeDataType::Float;
    LODInfo->bAllowCPUAccess=true;
    LODInfo->SkinCacheUsage=ESkinCacheUsage::Enabled;
    Mesh->Build();
    FAssetCompilingManager::Get().FinishAllCompilation();
    Mesh->MarkPackageDirty();
    const auto* RenderData=Mesh->GetResourceForRendering();
    if(!RenderData || RenderData->LODRenderData.IsEmpty()) return Failure(TEXT("No rebuilt render data"));
    const auto& LOD=RenderData->LODRenderData[0];
    TArray<float> Mask;
    if(!ReadMask(LOD,AttributeName,Mask)) return Failure(TEXT("Mask missing/nonbinary/not float32 in actual render buffer"));
    int32 EligibleVertices=0,EligibleTriangles=0;
    for(float Value:Mask) EligibleVertices+=Value>0.f;
    const auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
    if(!Indices) return Failure(TEXT("Missing actual triangle indices"));
    for(const auto& Section:LOD.RenderSections)
        for(uint32 Triangle=0;Triangle<Section.NumTriangles;++Triangle)
        {
            const uint32 Base=Section.BaseIndex+Triangle*3;
            const uint32 A=Indices->Get(Base),B=Indices->Get(Base+1),C=Indices->Get(Base+2);
            if(!Mask.IsValidIndex(A)||!Mask.IsValidIndex(B)||!Mask.IsValidIndex(C)) return Failure(TEXT("Invalid triangle index"));
            EligibleTriangles+=(Mask[A]>0.f || Mask[B]>0.f || Mask[C]>0.f);
        }
    if(EligibleVertices==0 || EligibleVertices==Mask.Num()) return Failure(TEXT("Mask must distinguish skin from other model surfaces"));
    auto Result=MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("asset"),Mesh->GetPathName());
    Result->SetStringField(TEXT("attribute"),AttributeName.ToString());
    Result->SetNumberField(TEXT("renderVertices"),Mask.Num());
    Result->SetNumberField(TEXT("eligibleVertices"),EligibleVertices);
    Result->SetNumberField(TEXT("eligibleTriangles"),EligibleTriangles);
    Result->SetNumberField(TEXT("morphTargets"),Mesh->GetMorphTargets().Num());
    Result->SetBoolField(TEXT("actualFloat32RenderMaskVerified"),true);
    Result->SetBoolField(TEXT("skinCacheRequestedNotRuntimeVerified"),true);
    TArray<TSharedPtr<FJsonValue>> Bones;
    const auto& Ref=Mesh->GetRefSkeleton();
    TArray<FTransform> Globals;
    for(int32 Index=0;Index<Ref.GetNum();++Index)
    {
        auto Bone=MakeShared<FJsonObject>();
        const int32 Parent=Ref.GetParentIndex(Index);
        const FTransform& Local=Ref.GetRefBonePose()[Index];
        Globals.Add(Parent==INDEX_NONE?Local:Local*Globals[Parent]);
        Bone->SetStringField(TEXT("name"),Ref.GetBoneName(Index).ToString());
        Bone->SetStringField(TEXT("parent"),Parent==INDEX_NONE?TEXT(""):Ref.GetBoneName(Parent).ToString());
        TArray<TSharedPtr<FJsonValue>> Matrix;
        const FMatrix M=Globals.Last().ToMatrixWithScale();
        for(int32 Row=0;Row<4;++Row)for(int32 Col=0;Col<4;++Col)Matrix.Add(MakeShared<FJsonValueNumber>(M.M[Row][Col]));
        Bone->SetArrayField(TEXT("componentMatrixUnrealRowMajorCentimeters"),Matrix);
        Bones.Add(MakeShared<FJsonValueObject>(Bone));
    }
    Result->SetArrayField(TEXT("bones"),Bones);
    return ToJson(Result);
}

FString UGroomCharacterLibrary::ReadBindingProjection(UGroomBindingAsset* Binding,FName AttributeName)
{
    if(!Binding || Binding->GetTargetBindingAttribute()!=AttributeName) return Failure(TEXT("Binding does not use the explicit mask"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    const USkeletalMesh* Mesh=Binding->GetTargetSkeletalMesh();
    UGroomAsset* Groom=Binding->GetGroom();
    if(!Mesh || !Groom || !UGroomBindingAsset::IsCompatible(Mesh,Binding,false)) return Failure(TEXT("Binding target incompatibility"));
    const auto* RenderData=Mesh->GetResourceForRendering();
    if(!RenderData || RenderData->LODRenderData.IsEmpty()) return Failure(TEXT("Missing render data"));
    const auto& LOD=RenderData->LODRenderData[0];
    TArray<float> Mask;
    if(!ReadMask(LOD,AttributeName,Mask)) return Failure(TEXT("Explicit render mask missing"));
    const auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
    if(!Indices) return Failure(TEXT("Missing indices"));
    auto Result=MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("binding"),Binding->GetPathName());
    TArray<TSharedPtr<FJsonValue>> Groups;
    int32 GroupIndex=0;
    for(const auto& Group:Binding->GetHairGroupsPlatformData())
    {
        if(Group.RenRootBulkDatas.IsEmpty()) return Failure(TEXT("Missing render-root binding bulk data"));
        FHairStrandsRootData Roots;
        FGroomBindingBuilder::GetRootData(Roots,Group.RenRootBulkDatas[0]);
        FHairStrandsDatas Strands,Guides;
        if(!Groom->GetHairStrandsDatas(GroupIndex,Strands,Guides)||Roots.RootCount!=Strands.GetNumCurves()||Roots.LODIndex!=0)
            return Failure(TEXT("Binding root count/LOD differs from groom"));
        double MaximumDistance=0.,SumDistance=0.;
        for(uint32 Root=0;Root<Roots.RootCount;++Root)
        {
            const uint32 Unique=Roots.RootToUniqueTriangleIndexBuffer[Root];
            if(!Roots.UniqueTriangleIndexBuffer.IsValidIndex(Unique)) return Failure(TEXT("Invalid root triangle mapping"));
            // Installed GroomBindingBuilder/HairStrandsBindingCommon encode section in the high eight bits.
            const uint32 Packed=Roots.UniqueTriangleIndexBuffer[Unique];
            const uint32 SectionIndex=(Packed>>24)&0xff,Triangle=Packed&0xffffff;
            if(!LOD.RenderSections.IsValidIndex(SectionIndex)||Triangle>=LOD.RenderSections[SectionIndex].NumTriangles)
                return Failure(TEXT("Root triangle index is outside the actual target"));
            const uint32 Base=LOD.RenderSections[SectionIndex].BaseIndex+Triangle*3;
            const uint32 A=Indices->Get(Base),B=Indices->Get(Base+1),C=Indices->Get(Base+2);
            if(!Mask.IsValidIndex(A)||!Mask.IsValidIndex(B)||!Mask.IsValidIndex(C)||!(Mask[A]>0.f||Mask[B]>0.f||Mask[C]>0.f))
                return Failure(TEXT("Root projected to an ineligible surface"));
            const uint32 PackedBary=Roots.RootBarycentricBuffer[Root];
            FFloat16 BX,BY;BX.Encoded=PackedBary&0xffff;BY.Encoded=(PackedBary>>16)&0xffff;
            const FVector3f P0=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(A);
            const FVector3f P1=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(B);
            const FVector3f P2=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(C);
            const FVector3f Projected=P0*float(BX)+P1*float(BY)+P2*(1.f-float(BX)-float(BY));
            const FVector3f Authored=Strands.StrandsPoints.PointsPosition[Strands.StrandsCurves.CurvesOffset[Root]];
            const double Distance=(Projected-Authored).Length();
            MaximumDistance=FMath::Max(MaximumDistance,Distance);SumDistance+=Distance;
        }
        auto Item=MakeShared<FJsonObject>();
        Item->SetNumberField(TEXT("groupIndex"),GroupIndex++);
        Item->SetNumberField(TEXT("roots"),Roots.RootCount);
        Item->SetNumberField(TEXT("uniqueTriangles"),Roots.UniqueTriangleIndexBuffer.Num());
        Item->SetNumberField(TEXT("maximumRootProjectionDistanceCentimeters"),MaximumDistance);
        Item->SetNumberField(TEXT("meanRootProjectionDistanceCentimeters"),SumDistance/FMath::Max(1u,Roots.RootCount));
        Item->SetBoolField(TEXT("allProjectedTrianglesEligible"),true);
        Groups.Add(MakeShared<FJsonValueObject>(Item));
    }
    if(Groups.IsEmpty()) return Failure(TEXT("No binding groups"));
    Result->SetArrayField(TEXT("groups"),Groups);
    Result->SetBoolField(TEXT("posedDeformationVerified"),false);
    Result->SetBoolField(TEXT("rendered"),false);
    return ToJson(Result);
}
