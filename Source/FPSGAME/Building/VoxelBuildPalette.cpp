#include "VoxelBuildPalette.h"

FVoxelPhysicalMaterial UVoxelBuildPalette::Physical(FName Id) const
{
    const auto* Definition=Find(Id);
    if(Definition&&Definition->bOverridePhysics)return Definition->Physics;
    FVoxelPhysicalMaterial Result;
    if(Id==TEXT("stone"))
    {
        Result.DensityKgM3=2600;Result.CompressionPa=3000000;Result.TensionPa=12000;
        Result.ShearPa=40000;Result.Durability=500;Result.JoulesPerDamage=15;
    }
    return Result;
}

const FVoxelBuildMaterial* UVoxelBuildPalette::Find(FName Id) const
{
    return Materials.FindByPredicate([Id](const FVoxelBuildMaterial& Entry){return Entry.Id==Id;});
}
