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
    TArray<TSharedPtr<FJsonValue>> Points,WidthValues,StrandCounts,StrandWidthValues,Groups;
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
    Result->SetArrayField(TEXT("strandPointCounts"),StrandCounts);
    Result->SetArrayField(TEXT("strandWidthsCentimeters"),StrandWidthValues);
    Result->SetArrayField(TEXT("groupIds"),Groups);
    FResourceSizeEx Resource(EResourceSizeMode::Exclusive);
    Asset->GetResourceSizeEx(Resource);
    Result->SetNumberField(TEXT("resourceSizeBytesReported"),double(Resource.GetTotalMemoryBytes()));
    Result->SetBoolField(TEXT("runtimeMemoryMeasured"),false);
    FString Json;
    FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    return Json;
}
