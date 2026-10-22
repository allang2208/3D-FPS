#include "LeatherBootsAuditLibrary.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

bool ULeatherBootsAuditLibrary::ExportRenderWeights(USkeletalMesh* Mesh,int32 LOD,const FString& File)
{
    if(!Mesh||!Mesh->GetPathName().StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/LeatherBootsUpgrade20261022/TailoredV2/")))return false;
    const auto* Render=Mesh->GetResourceForRendering();if(!Render||!Render->LODRenderData.IsValidIndex(LOD))return false;
    const auto& Data=Render->LODRenderData[LOD];const auto* Skin=Data.GetSkinWeightVertexBuffer();if(!Skin||!Skin->GetNeedsCPUAccess())return false;
    TArray<TSharedPtr<FJsonValue>> Rows;Rows.SetNum(Data.GetNumVertices());const auto& Ref=Mesh->GetRefSkeleton();
    for(const auto& Section:Data.RenderSections)for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
    {
        auto Row=MakeShared<FJsonObject>(),Weights=MakeShared<FJsonObject>();double Sum=0;
        for(uint32 K=0;K<Skin->GetMaxBoneInfluences();++K)Sum+=Skin->GetBoneWeight(V,K);
        if(Sum<=0)return false;
        for(uint32 K=0;K<Skin->GetMaxBoneInfluences();++K)if(const uint16 W=Skin->GetBoneWeight(V,K))
        {
            const int32 Local=Skin->GetBoneIndex(V,K);if(!Section.BoneMap.IsValidIndex(Local))return false;
            const int32 Bone=Section.BoneMap[Local];if(Bone>=Ref.GetNum())return false;
            Weights->SetNumberField(Ref.GetBoneName(Bone).ToString(),W/Sum);
        }
        const auto P=Data.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V);
        Row->SetArrayField(TEXT("p"),{MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)});
        Row->SetObjectField(TEXT("weights"),Weights);Rows[V]=MakeShared<FJsonValueObject>(Row);
    }
    for(const auto& Row:Rows)if(!Row)return false;
    auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("asset"),Mesh->GetPathName());Root->SetNumberField(TEXT("lod"),LOD);Root->SetArrayField(TEXT("vertices"),Rows);
    FString Json;return FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json))&&FFileHelper::SaveStringToFile(Json,*File);
}
