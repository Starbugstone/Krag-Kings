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
        double MaximumDistance=0.,SumDistance=0.,MaximumClosestResidual=0.,MaximumEncodingDisplacement=0.;
        double MaximumHalfRoundingBound=0.;
        TSharedPtr<FJsonObject> WorstDecodedRoot,WorstSurfaceRoot;
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
            const FVector Closest=FMath::ClosestPointOnTriangleToPoint(FVector(Authored),FVector(P0),FVector(P1),FVector(P2));
            const double ClosestResidual=(Closest-FVector(Authored)).Length();
            const double EncodingDisplacement=(Closest-FVector(Projected)).Length();
            // Each original barycentric lies in [0,1]. Half nearest-rounding error is at most
            // 2^-12 per stored coordinate. P2 uses 1-bx-by, hence the two edge lengths.
            const double HalfBound=(FVector(P0-P2).Length()+FVector(P1-P2).Length())/4096.;
            if(!WorstDecodedRoot.IsValid() || Distance>MaximumDistance || ClosestResidual>MaximumClosestResidual)
            {
                auto Diagnostic=MakeShared<FJsonObject>();
                Diagnostic->SetNumberField(TEXT("rootIndex"),Root);
                Diagnostic->SetNumberField(TEXT("sectionIndex"),SectionIndex);
                Diagnostic->SetNumberField(TEXT("triangleIndex"),Triangle);
                Diagnostic->SetNumberField(TEXT("decodedDistanceCentimeters"),Distance);
                Diagnostic->SetNumberField(TEXT("closestSurfaceResidualCentimeters"),ClosestResidual);
                Diagnostic->SetNumberField(TEXT("decodedVersusClosestDisplacementCentimeters"),EncodingDisplacement);
                Diagnostic->SetNumberField(TEXT("conservativeHalfRoundingBoundCentimeters"),HalfBound);
                const auto VectorValue=[](const FVector& Value)
                {
                    return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
                        MakeShared<FJsonValueNumber>(Value.X),MakeShared<FJsonValueNumber>(Value.Y),MakeShared<FJsonValueNumber>(Value.Z)});
                };
                Diagnostic->SetField(TEXT("authoredRootCentimeters"),VectorValue(FVector(Authored)));
                Diagnostic->SetField(TEXT("decodedProjectedCentimeters"),VectorValue(FVector(Projected)));
                Diagnostic->SetField(TEXT("closestTrianglePointCentimeters"),VectorValue(Closest));
                Diagnostic->SetArrayField(TEXT("triangleCentimeters"),{VectorValue(FVector(P0)),VectorValue(FVector(P1)),VectorValue(FVector(P2))});
                Diagnostic->SetField(TEXT("decodedBarycentrics"),VectorValue(FVector(float(BX),float(BY),1.f-float(BX)-float(BY))));
                if(!WorstDecodedRoot.IsValid()||Distance>MaximumDistance)WorstDecodedRoot=Diagnostic;
                if(!WorstSurfaceRoot.IsValid()||ClosestResidual>MaximumClosestResidual)WorstSurfaceRoot=Diagnostic;
            }
            MaximumClosestResidual=FMath::Max(MaximumClosestResidual,ClosestResidual);
            MaximumEncodingDisplacement=FMath::Max(MaximumEncodingDisplacement,EncodingDisplacement);
            MaximumHalfRoundingBound=FMath::Max(MaximumHalfRoundingBound,HalfBound);
            MaximumDistance=FMath::Max(MaximumDistance,Distance);SumDistance+=Distance;
        }
        auto Item=MakeShared<FJsonObject>();
        Item->SetNumberField(TEXT("groupIndex"),GroupIndex++);
        Item->SetNumberField(TEXT("roots"),Roots.RootCount);
        Item->SetNumberField(TEXT("uniqueTriangles"),Roots.UniqueTriangleIndexBuffer.Num());
        Item->SetNumberField(TEXT("maximumRootProjectionDistanceCentimeters"),MaximumDistance);
        Item->SetNumberField(TEXT("meanRootProjectionDistanceCentimeters"),SumDistance/FMath::Max(1u,Roots.RootCount));
        Item->SetNumberField(TEXT("maximumClosestSurfaceResidualCentimeters"),MaximumClosestResidual);
        Item->SetNumberField(TEXT("maximumDecodedVersusClosestDisplacementCentimeters"),MaximumEncodingDisplacement);
        Item->SetNumberField(TEXT("maximumConservativeHalfRoundingBoundCentimeters"),MaximumHalfRoundingBound);
        if(WorstDecodedRoot.IsValid())Item->SetObjectField(TEXT("worstDecodedRoot"),WorstDecodedRoot);
        if(WorstSurfaceRoot.IsValid())Item->SetObjectField(TEXT("worstSurfaceRoot"),WorstSurfaceRoot);
        Item->SetBoolField(TEXT("allProjectedTrianglesEligible"),true);
        Groups.Add(MakeShared<FJsonValueObject>(Item));
    }
    if(Groups.IsEmpty()) return Failure(TEXT("No binding groups"));
    Result->SetArrayField(TEXT("groups"),Groups);
    Result->SetBoolField(TEXT("posedDeformationVerified"),false);
    Result->SetBoolField(TEXT("rendered"),false);
    return ToJson(Result);
}

FString UGroomCharacterLibrary::BuildMaskedBinding(UGroomBindingAsset* Binding,UGroomAsset* Groom,
    USkeletalMesh* Mesh,FName AttributeName)
{
    if(!Binding||!Groom||!Mesh||AttributeName.IsNone()) return Failure(TEXT("Missing explicit binding inputs"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto* RenderData=Mesh->GetResourceForRendering();
    TArray<float> Mask;
    if(!RenderData||RenderData->LODRenderData.IsEmpty()||!ReadMask(RenderData->LODRenderData[0],AttributeName,Mask))
        return Failure(TEXT("Refuse binding without the verified float32 target mask"));
    Groom->Modify();
    auto Interpolation=Groom->GetHairGroupsInterpolation();
    for(auto& Group:Interpolation)
    {
        Group.DecimationSettings.CurveDecimation=1.f;
        Group.DecimationSettings.VertexDecimation=1.f;
    }
    Groom->SetHairGroupsInterpolation(Interpolation);
    auto LODGroups=Groom->GetHairGroupsLOD();
    if(LODGroups.IsEmpty()) return Failure(TEXT("Imported groom has no LOD group"));
    for(auto& Group:LODGroups)
    {
        Group.LODs.SetNum(1);
        auto& LOD=Group.LODs[0];
        LOD.CurveDecimation=1.f;LOD.VertexDecimation=1.f;LOD.ThicknessScale=1.f;
        LOD.bVisible=true;LOD.GeometryType=EGroomGeometryType::Strands;
        LOD.BindingType=EGroomBindingType::Skinning;
        LOD.Simulation=EGroomOverrideType::Disable;
        LOD.GlobalInterpolation=EGroomOverrideType::Disable;
    }
    Groom->SetHairGroupsLOD(LODGroups);
    Groom->SetEnableGlobalInterpolation(false);
    auto Physics=Groom->GetHairGroupsPhysics();
    for(auto& Group:Physics)
    {
        Group.SolverSettings.EnableSimulation=false;
        Group.SolverSettings.bEnableDeformation=false;
    }
    Groom->SetHairGroupsPhysics(Physics);
    if(!Groom->CacheDerivedDatas()) return Failure(TEXT("Strand settings rebuild failed"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    Binding->Modify();
    Binding->SetGroomBindingType(EGroomBindingMeshType::SkeletalMesh);
    Binding->SetGroom(Groom);
    Binding->SetSourceSkeletalMesh(nullptr);
    Binding->SetTargetSkeletalMesh(Mesh);
    Binding->SetTargetBindingAttribute(AttributeName);
    Binding->SetNumInterpolationPoints(100);
    Binding->SetMatchingSection(0); // Not used as a root-projection exclusion rule.
    Binding->Build();
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!Binding->IsValid()) return Failure(TEXT("Native masked binding build is invalid"));
    Groom->MarkPackageDirty();Binding->MarkPackageDirty();
    return ReadBindingProjection(Binding,AttributeName);
}
