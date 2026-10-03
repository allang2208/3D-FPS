#include "BlindSupplicantAuthoring.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"

bool UBlindSupplicantAuthoring::ConfigureDistanceLODs(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if (!Mesh || (Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18"))) return false;
    const FSkeletalMeshLODInfo* Base = Mesh->GetLODInfo(0);
    if (!Base || Base->bHasBeenSimplified) return false;
    const FSkeletalMeshBuildSettings BuildSettings = Base->BuildSettings;
    Mesh->Modify();
    while (Mesh->GetLODNum() < 3) Mesh->AddLODInfo();
    for (int32 LOD = 1; LOD < 3; ++LOD)
    {
        FSkeletalMeshLODInfo& Info = *Mesh->GetLODInfo(LOD);
        Info.BuildSettings = BuildSettings;
        Info.ScreenSize.Default = LOD == 1 ? .18f : .065f;
        Info.LODHysteresis = .015f;
        Info.ReductionSettings.BaseLOD = 0;
        Info.ReductionSettings.TerminationCriterion = SMTC_NumOfTriangles;
        Info.ReductionSettings.NumOfTrianglesPercentage = LOD == 1 ? .4f : .15f;
        Info.ReductionSettings.MaxBonesPerVertex = 8;
        Info.ReductionSettings.bRecalcNormals = false;
        Info.ReductionSettings.bEnforceBoneBoundaries = true;
        Info.ReductionSettings.bLockEdges = true;
        Info.ReductionSettings.bLockColorBounaries = true;
        Info.ReductionSettings.bImproveTrianglesForCloth = true;
        Info.bHasBeenSimplified = true;
    }
    Mesh->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
