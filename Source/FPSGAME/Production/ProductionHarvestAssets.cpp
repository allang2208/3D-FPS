#include "ProductionHarvestAssets.h"

namespace ProductionHarvestAssets
{
bool IsMaterial(const FString& Definition)
{
    return Definition==TEXT("wood")||Definition==TEXT("stone")||Definition==TEXT("iron_ore")||
        Definition==TEXT("copper_ore")||Definition==TEXT("silver_ore")||Definition==TEXT("gold_ore")||
        Definition==TEXT("ironIngot")||Definition==TEXT("copperIngot")||   // 锭类也走生产材料拾取链
        Definition==TEXT("silverIngot")||Definition==TEXT("goldIngot");    //  （落地物理＋稀有度光柱）
}
/** 冶炼家族定义的后缀判定：*_ore＝四种矿石，*Ingot＝四种金属锭。 */
static bool IsSmeltingOre(const FString& D){return D==TEXT("iron_ore")||D==TEXT("copper_ore")||D==TEXT("silver_ore")||D==TEXT("gold_ore");}
static bool IsSmeltingIngot(const FString& D){return D==TEXT("ironIngot")||D==TEXT("copperIngot")||D==TEXT("silverIngot")||D==TEXT("goldIngot");}
FSoftObjectPath PickupMesh(const FString& Definition,int32 Variant)
{
    if(Definition==TEXT("wood"))
    {
        (void)Variant;
        return FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A.SM_PoplarLog_Solid_A"));
    }
    if(IsSmeltingOre(Definition))   // 矿石借用强化石晶体网格（用户 2026-09-24 定案），材质按矿种覆写
        return FSoftObjectPath(TEXT("/Game/Items/EnhancementMaterials/enhancement_stone/SM_enhancement_stone.SM_enhancement_stone"));
    if(IsSmeltingIngot(Definition)) // 金属锭＝Blender 铸造块（SM_Ingot 由 Tools/Smelting 管线产出）
        return FSoftObjectPath(TEXT("/Game/Items/Smelting/Ingot/SM_Ingot.SM_Ingot"));
    return FSoftObjectPath(TEXT("/Game/RuralAustralia/StaticMeshes/Rocks/Rock_S_02/SM_Rock_S_02.SM_Rock_S_02"));
}
FSoftObjectPath PickupMaterial(const FString& Definition)
{
    if(IsSmeltingIngot(Definition))
        return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/Smelting/Ingot/MI_%s.MI_%s"),*Definition,*Definition));
    if(IsSmeltingOre(Definition))
        return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/Smelting/Ore/MI_%s.MI_%s"),*Definition,*Definition));
    return FSoftObjectPath();
}
bool IsIconSubject(const FString& Definition)
{
    // 木材已有离线渲染的 1x2 竖幅目录图，不进捕获通道；其余生产材料都是 1x1 方格，
    // 捕获画布按同一规则推成 320x320，与格子比例一致。
    return IsMaterial(Definition)&&Definition!=TEXT("wood");
}
int32 TreeVariant(const FSoftObjectPath& Tree)
{
    for(int32 Index=0;Index<4;++Index)
        if(Tree.GetAssetName()==FString::Printf(TEXT("SK_BlackPoplarPCG_%c"),TEXT('A')+Index))return Index;
    return INDEX_NONE;
}
FSoftObjectPath Stump(int32 Variant)
{
    const TCHAR Letter=TEXT('A')+FMath::Clamp(Variant,0,3);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/HarvestTimber/SM_CutStump_%c.SM_CutStump_%c"),Letter,Letter));
}
FSoftObjectPath FallingMesh(int32 Variant)
{
    const TCHAR Letter=TEXT('A')+FMath::Clamp(Variant,0,3);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/HarvestTimber/SK_CutUpper_%c.SK_CutUpper_%c"),Letter,Letter));
}
FSoftObjectPath CutProfile(int32 Variant)
{
    const TCHAR Letter=TEXT('A')+FMath::Clamp(Variant,0,3);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/HarvestTimber/DA_TreeCut_%c.DA_TreeCut_%c"),Letter,Letter));
}
FSoftObjectPath CutCap(int32 Variant)
{
    // 2026-09-26 用户反馈"倒下的树断面中空"：封盖网格由
    // Tools/Production/build_tree_cut_caps.py 从 SM_CutUpper_* 按切口材质提取（单槽 M_FallingCutEnd，
    // 顶点在树本地坐标、切面 Z=42），贴在倒树断口上闭合。
    const TCHAR Letter=TEXT('A')+FMath::Clamp(Variant,0,3);
    return FSoftObjectPath(FString::Printf(TEXT("/Game/Items/HarvestTimber/SM_CutCap_%c.SM_CutCap_%c"),Letter,Letter));
}
FSoftObjectPath FallingMaterial(int32 Slot)
{
    // 2026-09-26 三角碎片修复后的默认口径：倒树上半段用原树网格，切口靠 material-space 遮罩，
    // 因此槽 0/1 指向上一代那套带 `step(H,P.z)` 的 M_FallingPoplar 实例（使用标志齐全）。
    // 槽 2 仍是重制路径的断面材质，供 fps.Harvest.TreeFallUseSourceMesh 0 时对照使用。
    if(Slot==2)return FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/M_FallingCutEnd.M_FallingCutEnd"));
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
    if(Wood)
    {
        Paths.Append({FallingMaterial(0),FallingMaterial(1),FallingMaterial(2),TreeSound(false),TreeSound(true)});
        // 重制路径（fps.Harvest.TreeFallUseSourceMesh 0）对照用：它用网格自带的槽材质。
        Paths.Append({FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/MI_CutUpper_Bark.MI_CutUpper_Bark")),
            FSoftObjectPath(TEXT("/Game/Items/HarvestTimber/MI_CutUpper_Foliage.MI_CutUpper_Foliage"))});
        for(int32 Variant=0;Variant<4;++Variant)Paths.Append({Stump(Variant),CutProfile(Variant),CutCap(Variant)});
    }
    return Paths;
}
}
