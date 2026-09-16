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
    FVoxelPhysicalMaterial Result;
    if(Id==TEXT("stone")||Id==TEXT("marble"))
    {
        Result.DensityKgM3=2600;Result.CompressionPa=6000000;Result.TensionPa=900000;
        Result.ShearPa=80000;Result.Durability=500;Result.JoulesPerDamage=15;
    }
    else
    {
        Result.DensityKgM3=600;Result.CompressionPa=700000;Result.TensionPa=260000;
        Result.ShearPa=120000;Result.Durability=180;Result.JoulesPerDamage=6;
    }
    return Result;
}

const FVoxelBuildMaterial* UVoxelBuildPalette::Find(FName Id) const
{
    return Materials.FindByPredicate([Id](const FVoxelBuildMaterial& Entry){return Entry.Id==Id;});
}
