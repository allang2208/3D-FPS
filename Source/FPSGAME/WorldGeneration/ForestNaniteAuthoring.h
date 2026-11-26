#pragma once
#include "CoreMinimal.h"

#if WITH_EDITOR
class UStaticMesh;
namespace ForestNaniteAuthoring
{
inline constexpr TCHAR PackedMaterial[]=TEXT("/Game/ForestPathStudy/VillageRegion/Reference/Terrain/MI_ForestTilePacked.MI_ForestTilePacked");
void Configure(UStaticMesh& Mesh,bool bTerrain);
}
#endif
