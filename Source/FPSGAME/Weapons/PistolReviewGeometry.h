#pragma once
#include "PistolReloadSkinProbe.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

// Explicit review exports actual CPU-skinned geometry, not a skeleton sketch.
namespace FPSPistolReviewGeometry
{
inline void Save(const FString& Path,const TArray<USkeletalMeshComponent*>& Meshes,
    const TArray<UStaticMeshComponent*>& Parts,const FTransform& Frame)
{
    FString Text=TEXT("# Actual evaluated world-body geometry in body centimetres\n");int32 Offset=1;
    for(auto* Mesh:Meshes)
    {
        if(!Mesh||!Mesh->GetSkeletalMeshAsset())continue;
        TArray<FVector3f> Vertices;FPistolReloadSkinProbe::Skin(Mesh,Vertices);
        const auto Relative=Mesh->GetComponentTransform().GetRelativeTransform(Frame);
        Text+=TEXT("o ")+Mesh->GetName()+TEXT("\n");
        for(const auto& V:Vertices){const FVector P=Relative.TransformPosition(FVector(V));Text+=FString::Printf(TEXT("v %.5f %.5f %.5f\n"),P.X,P.Y,P.Z);}
        const auto& LOD=Mesh->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        const auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
        for(const auto& Section:LOD.RenderSections)if(Mesh->IsMaterialSectionShown(Section.MaterialIndex,0))
            for(uint32 I=Section.BaseIndex;I<Section.BaseIndex+Section.NumTriangles*3;I+=3)
                Text+=FString::Printf(TEXT("f %d %d %d\n"),Offset+Indices->Get(I),Offset+Indices->Get(I+1),Offset+Indices->Get(I+2));
        Offset+=Vertices.Num();
    }
    for(auto* Part:Parts)
    {
        if(!Part||!Part->GetStaticMesh()||!Part->IsVisible()||Part->bHiddenInGame)continue;
        const auto& LOD=Part->GetStaticMesh()->GetRenderData()->LODResources[0];const auto Relative=Part->GetComponentTransform().GetRelativeTransform(Frame);
        const auto& Vertices=LOD.VertexBuffers.PositionVertexBuffer;Text+=TEXT("o ")+Part->GetName()+TEXT("\n");
        for(uint32 I=0;I<Vertices.GetNumVertices();++I){const auto P=Relative.TransformPosition(FVector(Vertices.VertexPosition(I)));Text+=FString::Printf(TEXT("v %.5f %.5f %.5f\n"),P.X,P.Y,P.Z);}
        for(int32 I=0;I<LOD.IndexBuffer.GetNumIndices();I+=3)
            Text+=FString::Printf(TEXT("f %d %d %d\n"),Offset+LOD.IndexBuffer.GetIndex(I),Offset+LOD.IndexBuffer.GetIndex(I+1),Offset+LOD.IndexBuffer.GetIndex(I+2));
        Offset+=Vertices.GetNumVertices();
    }
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Text,*Path);
}
}
