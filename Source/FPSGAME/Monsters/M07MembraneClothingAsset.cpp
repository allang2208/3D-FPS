#include "M07MembraneClothingAsset.h"
#if WITH_EDITOR
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include <queue>
#include <vector>
#include <functional>

namespace
{
// Authoring only. The V35 body-owned fold strips and the gill material must
// share a capture fade; section boundaries are not anatomical attachments.
void JoinMembraneCapture(FSkeletalMeshLODModel& Lod,const FGuid& Guid)
{
    TMap<FIntVector,int32> Weld;
    TArray<FVector3f> Points;
    TArray<uint16> Skin;
    TArray<TArray<int32>> Nodes;Nodes.SetNum(Lod.Sections.Num());
    for (int32 S=0;S<Lod.Sections.Num();++S)
    {
        auto& Section=Lod.Sections[S];
        if (Section.ClothingData.AssetGuid!=Guid || Section.ClothMappingDataLODs.IsEmpty()) continue;
        const auto& Capture=Section.ClothMappingDataLODs[0];
        if (Capture.Num()!=Section.SoftVertices.Num()) continue;
        for (int32 V=0;V<Capture.Num();++V)
        {
            const auto P=Section.SoftVertices[V].Position;
            const FIntVector Key(FMath::RoundToInt(P.X*1000),FMath::RoundToInt(P.Y*1000),FMath::RoundToInt(P.Z*1000));
            int32* Existing=Weld.Find(Key);
            const int32 Node=Existing?*Existing:Points.Num();
            if (!Existing) {Weld.Add(Key,Node);Points.Add(P);Skin.Add(0);}
            Nodes[S].Add(Node);
            Skin[Node]=FMath::Max(Skin[Node],Capture[V].SourceMeshVertIndices[3]);
        }
    }
    TArray<TArray<TPair<int32,float>>> Edges;Edges.SetNum(Points.Num());
    for (int32 S=0;S<Lod.Sections.Num();++S)
    {
        const auto& Section=Lod.Sections[S];
        if (Nodes[S].IsEmpty()) continue;
        for (uint32 T=0;T<Section.NumTriangles;++T) for (int32 C=0;C<3;++C)
        {
            const int32 A=Lod.IndexBuffer[Section.BaseIndex+T*3+C]-Section.BaseVertexIndex;
            const int32 B=Lod.IndexBuffer[Section.BaseIndex+T*3+(C+1)%3]-Section.BaseVertexIndex;
            const int32 U=Nodes[S][A],V=Nodes[S][B];if(U==V)continue;
            const float Length=(Points[U]-Points[V]).Size();
            Edges[U].Emplace(V,Length);Edges[V].Emplace(U,Length);
        }
    }
    using Step=std::pair<float,int32>;
    std::priority_queue<Step,std::vector<Step>,std::greater<Step>> Queue;
    TArray<float> Distance;Distance.Init(TNumericLimits<float>::Max(),Points.Num());
    for(int32 N=0;N<Points.Num();++N) if(Skin[N]==0xffff){Distance[N]=0;Queue.emplace(0,N);}
    constexpr float FadeCm=12.f;
    while(!Queue.empty())
    {
        const auto Current=Queue.top();Queue.pop();
        if(Current.first!=Distance[Current.second]||Current.first>=FadeCm)continue;
        for(const auto& Edge:Edges[Current.second])
        {
            const float Next=Current.first+Edge.Value;
            if(Next<Distance[Edge.Key]&&Next<FadeCm){Distance[Edge.Key]=Next;Queue.emplace(Next,Edge.Key);}
        }
    }
    int32 Dynamic=0;
    for(int32 S=0;S<Lod.Sections.Num();++S)
    {
        if(Nodes[S].IsEmpty())continue;
        auto& Capture=Lod.Sections[S].ClothMappingDataLODs[0];
        for(int32 V=0;V<Capture.Num();++V)
        {
            const int32 N=Nodes[S][V];
            const float T=FMath::Clamp(Distance[N]/FadeCm,0.f,1.f);
            const uint16 Fade=uint16(FMath::RoundToInt((1-T*T*(3-2*T))*65535));
            Capture[V].SourceMeshVertIndices[3]=FMath::Max(Skin[N],Fade);
            Dynamic+=Capture[V].SourceMeshVertIndices[3]<0xffff;
        }
    }
    UE_LOG(LogTemp,Display,TEXT("M07_V36_CAPTURE dynamic_display_vertices=%d welded_nodes=%d"),Dynamic,Points.Num());
}
}

bool UM07MembraneClothingAsset::BindToSkeletalMesh(USkeletalMesh* Mesh,int32 MeshLod,int32 SectionIndex,int32 AssetLod)
{
    if(!Mesh||MeshLod!=0||AssetLod!=0||!Mesh->GetImportedModel()||Mesh->GetImportedModel()->LODModels.IsEmpty())return false;
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    // One simulation owns both visible materials. The common binder assumes
    // one section, so temporarily clear only its LOD registration, as in M07's
    // existing multi-section cloth adapter. Keep the full physical mesh.
    const auto PreviousMap=LodMap;LodMap.Reset();
    const bool Bound=Super::BindToSkeletalMesh(Mesh,MeshLod,SectionIndex,AssetLod);
    LodMap=PreviousMap;
    if(!Bound)return false;
    while(LodMap.Num()<=MeshLod)LodMap.Add(INDEX_NONE);
    LodMap[MeshLod]=AssetLod;
    auto& Lod=Mesh->GetImportedModel()->LODModels[MeshLod];
    auto& Section=Lod.Sections[SectionIndex];
    auto& Capture=Section.ClothMappingDataLODs[0];
    if(Capture.Num()!=Section.SoftVertices.Num())return false;
    for(int32 V=0;V<Capture.Num();++V)
    {
        const uint16 AuthoredSkin=65535-uint16(Section.SoftVertices[V].Color.A)*257;
        Capture[V].SourceMeshVertIndices[3]=FMath::Max(Capture[V].SourceMeshVertIndices[3],AuthoredSkin);
    }
    JoinMembraneCapture(Lod,GetAssetGuid());
    return true;
}
#endif
