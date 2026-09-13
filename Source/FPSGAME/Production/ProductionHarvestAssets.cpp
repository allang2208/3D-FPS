#include "ProductionHarvestAssets.h"

namespace ProductionHarvestAssets
{
bool IsMaterial(const FString& Definition)
{
    return Definition==TEXT("wood")||Definition==TEXT("stone")||Definition==TEXT("iron_ore")||
        Definition==TEXT("copper_ore")||Definition==TEXT("silver_ore")||Definition==TEXT("gold_ore");
}
FSoftObjectPath PickupMesh(const FString& Definition,int32 Variant)
{
    if(Definition==TEXT("wood"))
    {
        const TCHAR Letter=TEXT('A')+FMath::Clamp(Variant,0,2);
        return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/HarvestTimber/SM_PoplarLog_%c.SM_PoplarLog_%c"),Letter,Letter));
    }
    return FSoftObjectPath(TEXT("/Game/RuralAustralia/StaticMeshes/Rocks/Rock_S_02/SM_Rock_S_02.SM_Rock_S_02"));
}
FSoftObjectPath Stump(){return FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/SM_PoplarStump.SM_PoplarStump"));}
FSoftObjectPath CutCap(){return FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/SM_PoplarCutCap.SM_PoplarCutCap"));}
FSoftObjectPath FallingMaterial(int32 Slot)
{
    return FSoftObjectPath(Slot==0?TEXT("/Game/Items/HarvestTimber/MI_FallingPoplar_Bark.MI_FallingPoplar_Bark"):
        TEXT("/Game/Items/HarvestTimber/MI_FallingPoplar_Foliage.MI_FallingPoplar_Foliage"));
}
FSoftObjectPath TreeSound(bool Landing)
{
    return FSoftObjectPath(Landing?TEXT("/Game/Items/HarvestTimber/S_TreeLanding.S_TreeLanding"):
        TEXT("/Game/Items/HarvestTimber/S_TreeCrack.S_TreeCrack"));
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
    TArray<FSoftObjectPath> Paths={PickupMesh(Wood?TEXT("wood"):TEXT("stone")),Destruction(Wood),Wood?Leaves():Debris(),
        FSoftObjectPath(TEXT("/Game/Items/LootFX/M_LootBeam.M_LootBeam")),
        FSoftObjectPath(TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter")),
        FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane"))};
    if(Wood)Paths.Append({PickupMesh(TEXT("wood"),1),PickupMesh(TEXT("wood"),2),Stump(),CutCap(),FallingMaterial(0),FallingMaterial(1),TreeSound(false),TreeSound(true)});
    return Paths;
}
}
