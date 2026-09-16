#include "VoxelBuildPalette.h"

FVoxelPhysicalMaterial UVoxelBuildPalette::Physical(FName Id) const
{
    const auto* Definition=Find(Id);
    if(Definition&&Definition->bOverridePhysics)return Definition->Physics;
    // Balance values, not a material certificate. Tension is what limits unsupported spans.
    // Contract (Docs/Building/voxel-build-workflow.md): every voxel material must guarantee a
    // 2.0 m clear span, with a 100 kg player standing mid-span, and fail before roughly 3-4 m.
    // Re-measure with Tools/Building/voxel_stress_probe.cpp after changing density or tension.
    // 2026-09-16: all three strengths doubled at the user's request, so a 1 m hanging wall section
    // survives its own placement. Re-run Tools/Building/run_voxel_stress_probe.ps1 after any change.
    // 2026-09-16 (third pass, user request): every voxel weighs a quarter of what it did - wood
    // 600 -> 150 kg/m3, stone/marble 2600 -> 650 kg/m3 (1.2 kg and 5.2 kg per 20 cm cube). Same
    // strength limits, so spans grow by roughly the same factor; re-run the probe before publishing
    // the span numbers.
    // 2026-09-16 (second pass): stone/marble shear 80 -> 300 kPa. Measured on the player's saved wall
    // (Docs/Building/voxel-vertical-build-diagnosis-20260916.md): every "cannot build past 1 m"
    // roll-back was governed by shear across a 20x20 cm face, not by weight. Tension/compression are
    // unchanged, so the 2 m clear-span contract still fails in the same 3-4 m band.
    FVoxelPhysicalMaterial Result;
    if(Id==TEXT("stone")||Id==TEXT("marble"))
    {
        Result.DensityKgM3=650;Result.CompressionPa=6000000;Result.TensionPa=900000;
        Result.ShearPa=300000;Result.Durability=500;Result.JoulesPerDamage=15;
    }
    else
    {
        Result.DensityKgM3=150;Result.CompressionPa=700000;Result.TensionPa=260000;
        Result.ShearPa=120000;Result.Durability=180;Result.JoulesPerDamage=6;
    }
    return Result;
}

const FVoxelBuildMaterial* UVoxelBuildPalette::Find(FName Id) const
{
    return Materials.FindByPredicate([Id](const FVoxelBuildMaterial& Entry){return Entry.Id==Id;});
}
