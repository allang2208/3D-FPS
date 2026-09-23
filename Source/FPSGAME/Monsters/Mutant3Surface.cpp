#include "Mutant3.h"
#include "Engine/SkeletalMesh.h"
#if WITH_EDITOR
#include "Materials/MaterialInterface.h"
#include "MeshDescription.h"
#include "SkeletalMeshAttributes.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshRenderData.h"
#endif

bool AMutant3::RepairSurfaceBinding(USkeletalMesh* InMesh)
{
#if WITH_EDITOR
    // This is the single-surface body. Do not flatten an unrelated multi-material
    // mesh, and never alter the skeleton, weights, positions or animation assets.
    if (!InMesh || InMesh->GetPathName() != TEXT("/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw.SK_Mutant3_Claw") ||
        InMesh->GetMaterials().Num() != 1 || !InMesh->GetImportedModel()) return false;
    // Preserve the current authored surface during future mesh-only imports.
    // Replacing it with the old base material discards the detail-map setup.
    auto* Surface = InMesh->GetMaterials()[0].MaterialInterface.Get();
    if (!Surface) return false;
    const FName SlotName(TEXT("M_Mutant3_Meshy"));
    auto LogSections = [InMesh](const TCHAR* Stage)
    {
        if (const auto* Render = InMesh->GetResourceForRendering())
            for (int32 LOD = 0; LOD < Render->LODRenderData.Num(); ++LOD)
                for (int32 S = 0; S < Render->LODRenderData[LOD].RenderSections.Num(); ++S)
                    UE_LOG(LogTemp, Display, TEXT("MUTANT3_SURFACE_%s lod=%d section=%d render_material=%d slots=%d"),
                        Stage, LOD, S, Render->LODRenderData[LOD].RenderSections[S].MaterialIndex, InMesh->GetMaterials().Num());
    };
    LogSections(TEXT("BEFORE"));
    // Both the polygon source names and section table participate in rebuilding
    // the mesh. Fixing only Materials[0] leaves the cached section pointing at 1.
    {
        FScopedSkeletalMeshPostEditChange Change(InMesh);
        InMesh->Modify();
        auto& Slot = InMesh->GetMaterials()[0];
        Slot.MaterialInterface = Surface;
        Slot.MaterialSlotName = SlotName;
        Slot.ImportedMaterialSlotName = SlotName;
        for (int32 LOD = 0; LOD < InMesh->GetLODNum(); ++LOD)
        {
            auto* Description = InMesh->GetMeshDescription(LOD);
            if (!Description) return false;
            FSkeletalMeshAttributes Attributes(*Description);
            auto Names = Attributes.GetPolygonGroupMaterialSlotNames();
            for (const FPolygonGroupID Group : Description->PolygonGroups().GetElementIDs()) Names[Group] = SlotName;
            USkeletalMesh::FCommitMeshDescriptionParams Commit;
            Commit.bForceUpdate = true;
            if (!InMesh->CommitMeshDescription(LOD, Commit)) return false;
            for (auto& Section : InMesh->GetImportedModel()->LODModels[LOD].Sections) Section.MaterialIndex = 0;
            if (auto* Info = InMesh->GetLODInfo(LOD)) Info->LODMaterialMap.Reset();
        }
        InMesh->InvalidateDeriveDataCacheGUID();
        InMesh->MarkPackageDirty();
    } // PostEditChange rebuilds and waits for the mesh compilation to complete.
    InMesh->GetMaterials()[0].UVChannelData.bOverrideDensities = false;
    InMesh->UpdateUVChannelData(true);
    InMesh->MarkPackageDirty();
    LogSections(TEXT("REBUILT"));
    const auto* Render = InMesh->GetResourceForRendering();
    if (!Render || Render->LODRenderData.IsEmpty()) return false;
    for (const auto& LOD : Render->LODRenderData)
        for (const auto& Section : LOD.RenderSections)
            if (Section.MaterialIndex != 0) return false;
    return true;
#else
    return false;
#endif
}
