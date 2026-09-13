#include "ProductionHarvestAssets.h"

namespace ProductionHarvestAssets
{
bool IsMaterial(const FString& Definition)
{
    return Definition==TEXT("wood")||Definition==TEXT("stone")||Definition==TEXT("iron_ore")||
        Definition==TEXT("copper_ore")||Definition==TEXT("silver_ore")||Definition==TEXT("gold_ore");
}
FSoftObjectPath PickupMesh(const FString& Definition)
{
    return FSoftObjectPath(Definition==TEXT("wood")?
        TEXT("/Game/RuralAustralia/StaticMeshes/Vegetation/Log_S_01/SM_Log_S_01.SM_Log_S_01"):
        TEXT("/Game/RuralAustralia/StaticMeshes/Rocks/Rock_S_02/SM_Rock_S_02.SM_Rock_S_02"));
}
FSoftObjectPath Destruction(bool Wood)
{
    return FSoftObjectPath(Wood?
        TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Wood.P_Destruction_Wood"):
        TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Destruction/P_Destruction_Concrete.P_Destruction_Concrete"));
}
FSoftObjectPath Leaves(){return FSoftObjectPath(TEXT("/Game/RuralAustralia/Effects/FallingLeaves/FX_FallingLeaves.FX_FallingLeaves"));}
FSoftObjectPath Debris(){return FSoftObjectPath(TEXT("/Game/Realistic_Starter_VFX_Pack_Vol2/Mesh/SM_Derbis_B.SM_Derbis_B"));}
TArray<FSoftObjectPath> LoadSet(bool Wood)
{
    return {PickupMesh(Wood?TEXT("wood"):TEXT("stone")),Destruction(Wood),Wood?Leaves():Debris(),
        FSoftObjectPath(TEXT("/Game/Items/LootFX/M_LootBeam.M_LootBeam")),
        FSoftObjectPath(TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter")),
        FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane"))};
}
}
