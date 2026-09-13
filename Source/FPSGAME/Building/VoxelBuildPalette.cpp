#include "VoxelBuildPalette.h"

const FVoxelBuildMaterial* UVoxelBuildPalette::Find(FName Id) const
{
    return Materials.FindByPredicate([Id](const FVoxelBuildMaterial& Entry){return Entry.Id==Id;});
}
