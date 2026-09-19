#include "ASH12AttachmentAssetTools.h"
#include "Engine/StaticMesh.h"
#include "UObject/UnrealType.h"
#if WITH_EDITOR
#include "StaticMeshCompiler.h"
#include "StaticMeshResources.h"
#include "DistanceFieldAtlas.h"
#endif

bool UASH12AttachmentAssetTools::IsRuntimeFastBuild(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    return Mesh&&CastFieldChecked<FBoolProperty>(UStaticMesh::StaticClass()->FindPropertyByName(TEXT("bDoFastBuild")))->GetPropertyValue_InContainer(Mesh);
#else
    return false;
#endif
}

void UASH12AttachmentAssetTools::DisableRuntimeFastBuild(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh)return;
    Mesh->Modify();
    CastFieldChecked<FBoolProperty>(UStaticMesh::StaticClass()->FindPropertyByName(TEXT("bDoFastBuild")))->SetPropertyValue_InContainer(Mesh,false);
    // The caller applies build settings afterward, which invokes PostEditChange.
#endif
}

bool UASH12AttachmentAssetTools::FinishAndValidateBuild(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||IsRuntimeFastBuild(Mesh))return false;
    UStaticMesh* Meshes[]={Mesh};FStaticMeshCompilingManager::Get().FinishCompilation(Meshes);
    if(GDistanceFieldAsyncQueue)GDistanceFieldAsyncQueue->BlockUntilBuildComplete(Mesh,false);
    const auto* Render=Mesh->GetRenderData();if(!Render||Render->LODResources.IsEmpty())return false;
    const auto Bounds=Mesh->GetBounds(),RB=Render->Bounds;
    if(!RB.Origin.Equals(Bounds.Origin,.02)||!RB.BoxExtent.Equals(Bounds.BoxExtent,.02)||!FMath::IsFinite(RB.SphereRadius)||RB.SphereRadius<=.01)return false;
    if(const auto* DF=Render->LODResources[0].DistanceFieldData)
    {
        const auto B=DF->LocalSpaceMeshBounds.ExpandBy(.001f);
        if(!B.IsValid||B.Min.ContainsNaN()||B.Max.ContainsNaN()||!B.IsInsideOrOn(FVector3f(Bounds.Origin-Bounds.BoxExtent))||!B.IsInsideOrOn(FVector3f(Bounds.Origin+Bounds.BoxExtent)))return false;
    }
    return true;
#else
    return false;
#endif
}
