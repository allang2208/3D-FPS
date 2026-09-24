#include "ProductionToolStats.h"
#include "ProductionResource.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/WeaponDamagePanel.h"
#include "../Movement/FPSStaminaTuning.h"
#include "Engine/GameInstance.h"

bool ColdSteelTool::Supports(const FColdSteelItem& Item)
{
    return ColdSteelInventory::IsEquippedProductionTool(Item);
}

FProductionToolStats ColdSteelTool::Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    FProductionToolStats R;
    const auto* GI=Profile?Profile->GetGameInstance():nullptr;
    const auto* Gunsmith=GI?GI->GetSubsystem<UGunsmithSystem>():nullptr;
    const auto* Enhance=GI?GI->GetSubsystem<UColdSteelEnhancementSystem>():nullptr;
    R.bModifiable=Gunsmith&&Gunsmith->IsTool(Item.Definition);
    if(R.bModifiable)R.Modifiers=Gunsmith->Calculate(Item.Definition,Preview?*Preview:Gunsmith->Installed(Item)).Tool;

    // 自卫伤害：工具自己的基础数值 × 改造倍率，再走与剑类相同的附魔／加工后处理。
    // 不借用剑类 Evaluate，避免把连击、格挡与精通口径带进采集工具。
    const double Base=ColdSteelInventory::Number(Item,TEXT("melee_damage"),12);
    const double Attack=Profile?Profile->Derived(TEXT("atk")):0;
    const double Processed=Enhance?Enhance->ProcessedDamage(Item,Base,Attack,R.Modifiers.Damage):Base*R.Modifiers.Damage+Attack;
    R.Damage=ColdSteelWeaponDamage::Evaluate(Item,Profile,Processed);

    R.RateScale=FMath::Clamp(R.Modifiers.AttackSpeed,.25,4.);
    R.SwingSeconds=ColdSteelInventory::Number(Item,TEXT("swing_seconds"),1.1)/R.RateScale;
    R.ContactSeconds=FMath::Min(ColdSteelInventory::Number(Item,TEXT("contact_seconds"),.48)/R.RateScale,R.SwingSeconds*.9);
    R.StaminaCost=(Profile?Profile->StaminaSettings().HarvestCost:FColdSteelStaminaTuning{}.HarvestCost)*R.Modifiers.Stamina;
    R.HarvestReachCM=ColdSteelInventory::Number(Item,TEXT("harvest_reach_cm"),320)*R.Modifiers.HarvestReach;
    // 宽容半径是「倍率后再加绝对值」：矿镐出厂为 0（只认中心射线），改件的加值才给它辅助宽度。
    R.HarvestRadiusCM=ColdSteelInventory::Number(Item,TEXT("harvest_sweep_radius_cm"),0)*R.Modifiers.HarvestReach
        +R.Modifiers.HarvestRadiusAddCM;
    R.CombatReachCM=ColdSteelInventory::Number(Item,TEXT("combat_reach_cm"),180)*R.Modifiers.CombatReach;
    R.CombatRadiusCM=ColdSteelInventory::Number(Item,TEXT("combat_sweep_radius_cm"),0)*R.Modifiers.CombatReach;
    R.HarvestYield=R.Modifiers.HarvestYield;
    R.BonusHarvestChance=R.Modifiers.BonusHarvestChance;
    R.ToughnessDamage=R.Modifiers.ToughnessDamage;
    R.CriticalChanceAdd=R.Modifiers.CriticalChanceAdd;
    R.HarvestHitsAdd=R.Modifiers.HarvestHitsAdd;
    return R;
}

FProductionToolStats ColdSteelTool::EvaluateActive(const UColdSteelStatusModel* Profile,const FGunsmithParts* Preview)
{
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    return Tool?Evaluate(*Tool,Profile,Preview):FProductionToolStats{};
}

int32 ColdSteelTool::HitsNeeded(const FProductionResource& Target,const FProductionToolStats& Stats)
{
    return HitsNeeded(Target.HitsNeeded(),Stats);
}

int32 ColdSteelTool::HitsNeeded(int32 Factory,const FProductionToolStats& Stats)
{
    return FMath::Max(1,Factory+Stats.HarvestHitsAdd);
}

int64 ColdSteelTool::Yield(int64 Factory,const FProductionToolStats& Stats)
{
    if(Factory<=0)return Factory;
    return FMath::Max<int64>(1,FMath::RoundToDouble(double(Factory)*Stats.HarvestYield));
}
