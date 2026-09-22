#include "WitchRebuiltMonster.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"

bool AWitchRebuiltMonster::ConfigureDistanceLODs(USkeletalMesh* SourceMesh)
{
#if WITH_EDITOR
    if (!SourceMesh || SourceMesh->GetPathName() != TEXT("/Game/Monsters/WitchRebuilt/SK_WitchRebuilt.SK_WitchRebuilt")) return false;
    if (SourceMesh->GetLODNum() != 1 && SourceMesh->GetLODNum() != 3) return false;
    const FSkeletalMeshLODInfo* Base = SourceMesh->GetLODInfo(0);
    // RegenerateLOD must never reduce the approved imported base mesh.
    if (!Base || Base->bHasBeenSimplified) return false;
    const FSkeletalMeshBuildSettings BuildSettings = Base->BuildSettings;
    SourceMesh->Modify();
    while (SourceMesh->GetLODNum() < 3) SourceMesh->AddLODInfo();
    for (int32 LOD = 1; LOD < 3; ++LOD)
    {
        FSkeletalMeshLODInfo& Info = *SourceMesh->GetLODInfo(LOD);
        Info.BuildSettings = BuildSettings;
        Info.ScreenSize.Default = LOD == 1 ? .09f : .035f;
        Info.LODHysteresis = .01f;
        Info.ReductionSettings.BaseLOD = 0;
        Info.ReductionSettings.TerminationCriterion = SMTC_NumOfTriangles;
        Info.ReductionSettings.NumOfTrianglesPercentage = LOD == 1 ? .5f : .2f;
        Info.ReductionSettings.MaxBonesPerVertex = 8;
        Info.ReductionSettings.bRecalcNormals = false;
        Info.ReductionSettings.bEnforceBoneBoundaries = true;
        Info.ReductionSettings.bLockEdges = true;
        Info.ReductionSettings.bLockColorBounaries = true;
        Info.ReductionSettings.bImproveTrianglesForCloth = true;
        Info.bHasBeenSimplified = true;
    }
    SourceMesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
