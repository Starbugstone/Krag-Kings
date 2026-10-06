#include "GroomProbeLibrary.h"
#include "GroomAsset.h"
#include "HairDescription.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_MODULE(FDefaultModuleImpl,GroomProbe)

FString UGroomProbeLibrary::ReadDescription(UGroomAsset* Asset)
{
    if(!Asset) return TEXT("{\"error\":\"Missing groom asset\"}");
    FAssetCompilingManager::Get().FinishAllCompilation();
    const FHairDescription Description=Asset->GetHairDescription();
    const auto Positions=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Position);
    const auto Widths=Description.VertexAttributes().GetAttributesRef<float>(HairAttribute::Vertex::Width);
    const auto Colors=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Color);
    const auto Counts=Description.StrandAttributes().GetAttributesRef<int>(HairAttribute::Strand::VertexCount);
    const auto StrandWidths=Description.StrandAttributes().GetAttributesRef<float>(HairAttribute::Strand::Width);
    const auto GroupIds=Description.StrandAttributes().GetAttributesRef<int>(HairAttribute::Strand::GroupID);
    TSharedRef<FJsonObject> Result=MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("asset"),Asset->GetPathName());
    Result->SetBoolField(TEXT("valid"),Description.IsValid());
    Result->SetNumberField(TEXT("pointCount"),Description.GetNumVertices());
    Result->SetNumberField(TEXT("curveCount"),Description.GetNumStrands());
    Result->SetBoolField(TEXT("hasPointWidths"),Widths.IsValid());
    Result->SetBoolField(TEXT("hasStrandWidths"),StrandWidths.IsValid());
    Result->SetBoolField(TEXT("hasRootUV"),Description.HasAttribute(EHairAttribute::RootUV));
    Result->SetBoolField(TEXT("hasColor"),Description.HasAttribute(EHairAttribute::Color));
    Result->SetBoolField(TEXT("hasGroupIds"),GroupIds.IsValid());
    TArray<TSharedPtr<FJsonValue>> Points,WidthValues,ColorValues,StrandCounts,StrandWidthValues,Groups;
    for(int32 Index=0;Index<Description.GetNumVertices();++Index)
    {
        const FVertexID Id(Index);
        if(Positions.IsValid())
        {
            const FVector3f P=Positions[Id];
            TArray<TSharedPtr<FJsonValue>> XYZ={MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)};
            Points.Add(MakeShared<FJsonValueArray>(XYZ));
        }
        if(Widths.IsValid()) WidthValues.Add(MakeShared<FJsonValueNumber>(Widths[Id]));
        if(Colors.IsValid())
        {
            const FVector3f C=Colors[Id];
            ColorValues.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
                MakeShared<FJsonValueNumber>(C.X),MakeShared<FJsonValueNumber>(C.Y),MakeShared<FJsonValueNumber>(C.Z)}));
        }
    }
    for(int32 Index=0;Index<Description.GetNumStrands();++Index)
    {
        const FStrandID Id(Index);
        if(Counts.IsValid()) StrandCounts.Add(MakeShared<FJsonValueNumber>(Counts[Id]));
        if(StrandWidths.IsValid()) StrandWidthValues.Add(MakeShared<FJsonValueNumber>(StrandWidths[Id]));
        if(GroupIds.IsValid()) Groups.Add(MakeShared<FJsonValueNumber>(GroupIds[Id]));
    }
    Result->SetArrayField(TEXT("positionsCentimeters"),Points);
    Result->SetArrayField(TEXT("pointWidthsCentimeters"),WidthValues);
    if(Colors.IsValid()) Result->SetArrayField(TEXT("pointColorsLinearRgb"),ColorValues);
    Result->SetArrayField(TEXT("strandPointCounts"),StrandCounts);
    Result->SetArrayField(TEXT("strandWidthsCentimeters"),StrandWidthValues);
    Result->SetArrayField(TEXT("groupIds"),Groups);
    FHairStrandsDatas BuiltStrands,BuiltGuides;
    const bool bBuilt=Asset->GetHairStrandsDatas(0,BuiltStrands,BuiltGuides);
    Result->SetBoolField(TEXT("builtStrandsAvailable"),bBuilt);
    if(bBuilt && !BuiltStrands.StrandsPoints.PointsRadius.IsEmpty())
    {
        float MinRadius=MAX_flt,MaxRadius=0.f;
        for(float Radius:BuiltStrands.StrandsPoints.PointsRadius)
        {
            MinRadius=FMath::Min(MinRadius,Radius);
            MaxRadius=FMath::Max(MaxRadius,Radius);
        }
        Result->SetNumberField(TEXT("builtPointCount"),BuiltStrands.GetNumPoints());
        Result->SetNumberField(TEXT("builtCurveCount"),BuiltStrands.GetNumCurves());
        Result->SetNumberField(TEXT("builtRadiusMinCentimeters"),MinRadius);
        Result->SetNumberField(TEXT("builtRadiusMaxCentimeters"),MaxRadius);
    }
    FResourceSizeEx Resource(EResourceSizeMode::Exclusive);
    Asset->GetResourceSizeEx(Resource);
    Result->SetNumberField(TEXT("resourceSizeBytesReported"),double(Resource.GetTotalMemoryBytes()));
    Result->SetBoolField(TEXT("runtimeMemoryMeasured"),false);
    FString Json;
    FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    return Json;
}

FString UGroomProbeLibrary::RestorePointWidths(UGroomAsset* Asset,const TArray<FVector>& ExpectedPositionsCentimeters,
    const TArray<int32>& ExpectedStrandPointCounts,const TArray<float>& WidthsCentimeters)
{
    if(!Asset) return TEXT("Missing asset");
    FAssetCompilingManager::Get().FinishAllCompilation();
    FHairDescription Description=Asset->GetHairDescription();
    if(Description.GetNumVertices()!=ExpectedPositionsCentimeters.Num() ||
       Description.GetNumVertices()!=WidthsCentimeters.Num() ||
       Description.GetNumStrands()!=ExpectedStrandPointCounts.Num()) return TEXT("Sidecar count mismatch");
    const auto Positions=Description.VertexAttributes().GetAttributesRef<FVector3f>(HairAttribute::Vertex::Position);
    const auto Counts=Description.StrandAttributes().GetAttributesRef<int>(HairAttribute::Strand::VertexCount);
    if(!Positions.IsValid() || !Counts.IsValid()) return TEXT("Missing imported positions/topology");
    for(int32 Index=0;Index<ExpectedStrandPointCounts.Num();++Index)
        if(Counts[FStrandID(Index)]!=ExpectedStrandPointCounts[Index]) return TEXT("Sidecar strand order/topology mismatch");
    for(int32 Index=0;Index<ExpectedPositionsCentimeters.Num();++Index)
    {
        const FVector Actual(Positions[FVertexID(Index)]);
        if(!Actual.Equals(ExpectedPositionsCentimeters[Index],1e-5)) return TEXT("Sidecar point order/space mismatch");
        if(!FMath::IsFinite(WidthsCentimeters[Index]) || WidthsCentimeters[Index]<=0.f)
            return TEXT("Sidecar width is not finite and positive");
    }
    auto Widths=Description.VertexAttributes().GetAttributesRef<float>(HairAttribute::Vertex::Width);
    if(!Widths.IsValid())
    {
        Description.VertexAttributes().RegisterAttribute<float>(HairAttribute::Vertex::Width);
        Widths=Description.VertexAttributes().GetAttributesRef<float>(HairAttribute::Vertex::Width);
    }
    for(int32 Index=0;Index<WidthsCentimeters.Num();++Index) Widths[FVertexID(Index)]=WidthsCentimeters[Index];
    // GroomBuilder explicitly gives vertex widths precedence over strand width.
    Asset->Modify();
    Asset->CommitHairDescription(MoveTemp(Description),EHairDescriptionType::Source);
    if(!Asset->CacheDerivedDatas()) return TEXT("Derived groom rebuild failed");
    FAssetCompilingManager::Get().FinishAllCompilation();
    Asset->MarkPackageDirty();
    return TEXT("");
}
