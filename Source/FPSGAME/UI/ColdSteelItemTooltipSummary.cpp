#include "../Weapons/WoodenTorchItem.h"
#include "ColdSteelWeaponText.h"
#include "../Weapons/PojunGrip.h"
#include "ColdSteelConsumablePresentation.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../Movement/FPSStaminaTuning.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"
#include "../Combat/CombatItemFormula.h"

namespace
{
struct FMetric {FName Key;FString Label,Unit;double Value=0;int32 Digits=0;bool Lower=false,Core=true;int32 Tone=0;};

// 套装加成由 ColdSteelFormulaBonuses.cpp 的 SetEffect 提供；
// 这里按该函数的实际口径反过来写成可读行，避免浮窗承诺引擎不结算的效果。
// 2026-10-22 新增：缩略浮窗要显示「锁子甲套装（4/5）」和凑齐后的属性。
// 总件数不写死，按目录里带同一 armorSet 的条目统计。
struct FSetBonusDef
{
    const TCHAR* Key;
    const TCHAR* Label;
    /** 已换成玩家口径的数值：比例项换算成百分数，点数项保持点数。 */
    double Value;
    bool bPercent;
    /** 耗时／消耗类指标变快变省是收益，显示时要带负号，否则会被读成变慢变费。 */
    bool bLowerValue;
};
const FSetBonusDef* SetBonusList(const FString& Set,int32& OutCount)
{
    // 口径与 ColdSteelFormulaBonuses.cpp 的 SetEffect 逐项对应：
    // defense/castRange/magicAttack/critDamage 是比例，crit 是百分点。
    // critDamage 进的是 CriticalDamageBonus（额外伤害比例），全项目统一写作「暴击伤害 +N%」：
    // 与武器浮窗的「暴击伤害加成」、目录 setBonusDesc 文案同口径，只有 1+X 的整体才叫「暴击倍率」。
    static const FSetBonusDef Ranger[]={{TEXT("def"),TEXT("防御力"),5.,true,false},
                                        {TEXT("crit"),TEXT("暴击率"),10.,true,false},
                                        {TEXT("critDamage"),TEXT("暴击伤害"),25.,true,false}};
    static const FSetBonusDef Steel[]={{TEXT("def"),TEXT("防御力"),15.,true,false}};
    static const FSetBonusDef BlueMage[]={{TEXT("castRange"),TEXT("施法距离"),50.,true,false},
                                          {TEXT("magicAttack"),TEXT("魔法攻击力"),10.,true,false}};
    static const FSetBonusDef St6[]={{TEXT("reloadSpeed"),TEXT("换弹速度"),15.,true,false},
                                     {TEXT("adsPercent"),TEXT("ADS 瞄准时间"),10.,true,true},
                                     {TEXT("sprintStaminaCost"),TEXT("奔跑体力消耗"),15.,true,true}};
    static const FSetBonusDef Modern[]={{TEXT("def"),TEXT("防御力"),12.,true,false},
                                        {TEXT("firearmRecoilPercent"),TEXT("枪械后坐力"),8.,true,true},
                                        {TEXT("firearmStabilityPercent"),TEXT("枪械稳定性"),10.,true,false},
                                        {TEXT("adsPercent"),TEXT("ADS 瞄准时间"),5.,true,true}};
    static const FSetBonusDef Workwear[]={{TEXT("actionStaminaCost"),TEXT("所有动作体力消耗"),15.,true,true},
                                          {TEXT("speed"),TEXT("移动速度"),10.,true,false},
                                          {TEXT("survivalConsumption"),TEXT("饥饿／口渴下降速度"),25.,true,true}};
    if(Set==TEXT("ranger_field")){OutCount=UE_ARRAY_COUNT(Ranger);return Ranger;}
    if(Set==TEXT("steel_chainmail")){OutCount=UE_ARRAY_COUNT(Steel);return Steel;}
    if(Set==TEXT("blue_mage")){OutCount=UE_ARRAY_COUNT(BlueMage);return BlueMage;}
    if(Set==TEXT("st6_tactical")){OutCount=UE_ARRAY_COUNT(St6);return St6;}
    if(Set==TEXT("modern_tactical")){OutCount=UE_ARRAY_COUNT(Modern);return Modern;}
    if(Set==TEXT("workwear")){OutCount=UE_ARRAY_COUNT(Workwear);return Workwear;}
    OutCount=0;return nullptr;
}
// 套装显示名：显式列在目录里比按内码猜更可靠，未登记则回退到套装 id。
FString SetDisplayName(const FString& Set)
{
    if(Set==TEXT("ranger_field"))return TEXT("野行套装");
    if(Set==TEXT("steel_chainmail"))return TEXT("锁子甲套装");
    if(Set==TEXT("blue_mage"))return TEXT("法师套装");
    if(Set==TEXT("st6_tactical"))return TEXT("ST6 战术套装");
    if(Set==TEXT("modern_tactical"))return TEXT("现代战术套装");
    if(Set==TEXT("workwear"))return TEXT("户外工作套装");
    return Set;
}

FString Format(double Value,int32 Digits)
{
    FString Result=FString::Printf(TEXT("%.*f"),Digits,Value);
    if(Digits>0){while(Result.EndsWith(TEXT("0")))Result.LeftChopInline(1);if(Result.EndsWith(TEXT(".")))Result.LeftChopInline(1);}
    return Result==TEXT("-0")?TEXT("0"):Result;
}
/**
 * 套装进度与凑齐后的属性。总件数按目录里带同一 armorSet 的定义统计，
 * 已装备件数按护甲五槽实际穿着统计，两者都从同一份数据推出来，
 * 不写死 5 件，也不假设套装只覆盖五个槽。
 */
bool BuildSetInfo(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipSetInfo& Out)
{
    const auto Data=CombatItemFormula::ReadOnly(Item);
    if(!Data)return false;
    FString Set;Data->TryGetStringField(TEXT("armorSet"),Set);
    if(Set.IsEmpty())return false;
    int32 Count=0;
    if(!SetBonusList(Set,Count)||Count==0)return false;
    Out=FColdSteelTooltipSetInfo();
    Out.Name=SetDisplayName(Set);

    // 总件数：目录里声明了同一 armorSet 的定义数。
    // 全表 241 条、每次浮窗都要算一遍，按套装名缓存；目录在运行期不变。
    static TMap<FString,int32> TotalCache;
    int32 Total=0;
    if(const auto* Cached=TotalCache.Find(Set))Total=*Cached;
    else
    {
        if(Model)for(const auto& Def:Model->ItemDefinitions())
        {
            FColdSteelItem Probe;Probe.Definition=Def.Key;Probe.Data=Def.Value;
            const auto Other=CombatItemFormula::ReadOnly(Probe);
            if(!Other)continue;
            FString OtherSet;Other->TryGetStringField(TEXT("armorSet"),OtherSet);
            if(OtherSet==Set)++Total;
        }
        // 目录未加载时不要缓存 0，否则之后会一直报 0 件。
        if(Total>0)TotalCache.Add(Set,Total);
    }
    // 已装备件数：只数真正穿在身上的同套部件，背包里的不算。
    int32 Owned=0;
    if(Model)for(const int32 Slot:{1,3,7,13,15})
    {
        const auto* Worn=Model->Equipped(Slot);
        if(!Worn)continue;
        const auto WornData=CombatItemFormula::ReadOnly(*Worn);
        if(!WornData)continue;
        FString WornSet;WornData->TryGetStringField(TEXT("armorSet"),WornSet);
        if(WornSet==Set)++Owned;
    }
    // 没有模型就没有目录可数：不能显示「（0/0）」这种假进度，整段不渲染。
    // 少数调用点（如探险详情）允许传 nullptr，浮窗应退回不带套装信息的形态。
    if(Total<=0)return false;
    Out.Total=Total;Out.Equipped=FMath::Min(Owned,Total);
    Out.bComplete=Total>0&&Owned>=Total;

    const auto* List=SetBonusList(Set,Count);
    for(int32 Index=0;Index<Count;++Index)
    {
        const auto& B=List[Index];
        // 表里存的是显示量级（正值）；但「耗时／消耗」类指标变快变省本身就是
        // 收益，写成「ADS 瞄准时间 +10%」会读成更慢更费。所以按语义给符号：
        // bLowerValue 的项目显示负号，其余显示正号。
        const TCHAR* Sign=B.bLowerValue?TEXT("-"):TEXT("+");
        Out.Bonuses.Add({B.Label,FString::Printf(TEXT("%s%.*f%s"),Sign,B.bPercent?0:2,B.Value,B.bPercent?TEXT("%"):TEXT(""))});
    }
    return true;
}
TArray<FMetric> Metrics(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* G)
{
    TArray<FMetric> Result;
    if(ColdSteelInventory::IsWoodenTorch(Item))return Result;
    auto Add=[&](const TCHAR* Key,const TCHAR* Label,double Value,const TCHAR* Unit,int32 Digits=0,bool Lower=false,bool Core=true,int32 Tone=0)
        {Result.Add({FName(Key),Label,Unit,Value,Digits,Lower,Core,Tone});};
    if(G&&G->Weapon(Item.Definition))
    {
        auto S=G->CalculateItem(Item,G->Installed(Item));
        ColdSteelWeaponStats::ApplyFirearmEquipmentHandling(S,Model);
        const auto Damage=ColdSteelWeaponStats::DamageParts(Item,Model,S.Damage);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,Damage.Total(),TEXT(""),2);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,Damage.BasePhysical,TEXT(""),2,false,false);
        if(Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,Damage.AddedPhysical,TEXT(""),2,false,false);
        if(Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,Damage.AddedMagic,TEXT(""),2,false,false);
        Add(S.BurstCount>1?TEXT("burst_interval"):TEXT("attack_interval"),S.BurstCount>1?TEXT("组内射击间隔"):ColdSteelWeaponText::AttackInterval,ColdSteelWeaponStats::Interval(&Item,Model,S.Interval)*1000,TEXT(" ms"),0,true);
        Add(TEXT("reload"),ColdSteelWeaponText::Reload,ColdSteelWeaponStats::Reload(&Item,Model,S.Reload),TEXT(" s"),2,true);
        Add(TEXT("capacity"),ColdSteelWeaponText::Capacity,S.Capacity,TEXT(" 发"));
        Add(TEXT("ads"),ColdSteelWeaponText::ADS,S.ADS*1000*(Model?Model->ADSTimeMultiplier():1.),TEXT(" ms"),0,true,false);
        if(Item.Definition==TEXT("ue_rsh12"))Add(TEXT("equip_speed_bonus"),ColdSteelWeaponText::EquipSpeedBonus,S.EquipSpeedBonus*100.,TEXT("%"),0,false,false);
        Add(TEXT("empty_reload"),ColdSteelWeaponText::EmptyReload,ColdSteelWeaponStats::Reload(&Item,Model,S.EmptyReload),TEXT(" s"),2,true);
        Add(TEXT("recoil"),ColdSteelWeaponText::RecoilIndex,S.Recoil,TEXT(""),1,true,false);
        Add(TEXT("stability"),ColdSteelWeaponText::Stability,S.Handling.Stability,TEXT(" /100"),1,false,false);
        Add(TEXT("effective_range"),ColdSteelWeaponText::EffectiveRange,S.Range,TEXT(" m"),2);
        // 自带护甲穿透（innate_armor_penetration）不进核心对比行，作为次要指标展示。
        if(const double InnatePenetration=ColdSteelInventory::Number(Item,TEXT("innate_armor_penetration"));InnatePenetration>0)
            Add(TEXT("armor_penetration"),TEXT("护甲穿透"),InnatePenetration*100,TEXT("%"),0,false,false);
        // 自带要害伤害加成（innate_weakpoint_percent）同样是次要指标。
        if(const double InnateWeakpoint=ColdSteelInventory::Number(Item,TEXT("innate_weakpoint_percent"));InnateWeakpoint>0)
            Add(TEXT("weakpoint_damage"),TEXT("要害伤害"),InnateWeakpoint*100,TEXT("%"),0,false,false);
    }
    else if(ColdSteelInventory::IsBow(Item))
    {
        const auto Bow=ColdSteelBow::Evaluate(Item,Model);const auto& Damage=Bow.Damage;
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,Damage.Total(),TEXT(""),2);
        Add(TEXT("draw_seconds"),ColdSteelWeaponText::DrawTime,Bow.Draw,TEXT(" s"),2,true);
        Add(TEXT("draw_speed_bonus"),TEXT("拉弓速度加成"),Bow.DrawSpeedBonus*100.,TEXT("%"),1,false,false);
        Add(TEXT("rhythm_window"),ColdSteelWeaponText::RhythmWindow,Bow.RhythmWindow,TEXT(" s"),2,false,false);
        Add(TEXT("nock_seconds"),ColdSteelWeaponText::NockTime,Bow.Nock,TEXT(" s"),2,true);
        Add(TEXT("effective_range"),ColdSteelWeaponText::EffectiveRange,Bow.Range,TEXT(" m"),2);
        Add(TEXT("projectile_speed"),ColdSteelWeaponText::ProjectileSpeed,Bow.Speed,TEXT(" m/s"),2,false,false);
        Add(TEXT("bow_stamina"),ColdSteelWeaponText::StaminaCost,Bow.Stamina,TEXT(""),2,true,false);
        Add(TEXT("bow_charge_stamina"),ColdSteelWeaponText::BowChargeStamina,Bow.ChargeStamina,TEXT(" /s"),2,true,false);
        Add(TEXT("bow_sway"),ColdSteelWeaponText::Sway,Bow.Sway,TEXT(""),2,true,false);
        Add(TEXT("ads"),ColdSteelWeaponText::ADS,Bow.ADS*1000*(Model?Model->ADSTimeMultiplier():1.),TEXT(" ms"),0,true,false);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,Damage.BasePhysical,TEXT(""),2,false,false);
        if(Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,Damage.AddedPhysical,TEXT(""),2,false,false);
        if(Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,Damage.AddedMagic,TEXT(""),2,false,false);
    }
    else if(ColdSteelInventory::IsTwoHandedSword(Item)&&!PojunGrip::Installed(Item))
    {
        const auto S=ColdSteelMelee::Evaluate(Item,Model);
        const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(Item);
        const bool RisingDragon=ColdSteelModularSword::UsesRisingDragonFinisher(Item);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,S.Damage,TEXT(""),2);
        Add(TEXT("combo_second_damage"),TEXT("三连击第二段伤害"),S.ComboSecondDamage,TEXT(""),2,false,false);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,S.DamageParts.BasePhysical,TEXT(""),2,false,false);
        if(S.DamageParts.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,S.DamageParts.AddedPhysical,TEXT(""),2,false,false);
        if(S.DamageParts.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,S.DamageParts.AddedMagic,TEXT(""),2,false,false);
        if(S.Modifiers.SkillCooldown!=1)Add(TEXT("rune_skill_cooldown"),TEXT("所有技能冷却倍率"),S.Modifiers.SkillCooldown,TEXT("×"),2,true,false);
        if(S.Modifiers.MartialCooldown!=1)Add(TEXT("martial_cooldown"),TEXT("武技冷却倍率"),S.Modifiers.MartialCooldown,TEXT("×"),2,true,false);
        if(S.Modifiers.MagicCooldown!=1)Add(TEXT("rune_magic_cooldown"),TEXT("魔法技能冷却倍率"),S.Modifiers.MagicCooldown,TEXT("×"),2,true,false);
        if(S.Modifiers.MagicDamage!=1)Add(TEXT("rune_magic_mult"),TEXT("魔法伤害倍率"),S.Modifiers.MagicDamage,TEXT("×"),2,false,false);
        if(S.Modifiers.MagicCost!=1)Add(TEXT("rune_magic_cost"),ColdSteelWeaponText::MagicCostMultiplier,S.Modifiers.MagicCost,TEXT("×"),2,true,false);
        Add(TEXT("ballast_heavy_mult"),TEXT("重击伤害倍率"),S.HeavyMultiplier,TEXT("×"),2,false,false);
        Add(TEXT("heavy_charge_speed_bonus"),TEXT("重击蓄力速度加成"),S.HeavyChargeSpeedBonus*100.,TEXT("%"),0,false,false);
        Add(TEXT("heavy_charge_seconds"),TEXT("重击蓄力时间"),S.HeavyChargeSeconds,TEXT(" s"),2,true,false);
        Add(TEXT("heavy_toughness"),TEXT("重击韧性伤害倍率"),S.Modifiers.HeavyToughnessMultiplier(),TEXT("×"),2,false,false);
        if(S.KnockbackCM>0)Add(TEXT("melee_knockback"),TEXT("攻击击退距离"),S.KnockbackCM,TEXT(" cm"),1,false,false);
        Add(TEXT("quick_combat_damage_mult"),TEXT("快速近战伤害倍率"),S.QuickCombat.DamageMultiplier,TEXT("×"),2,false,false);
        Add(TEXT("quick_combat_damage"),TEXT("快速近战伤害"),S.QuickCombat.Damage,TEXT(""),2,false,false);
        Add(TEXT("quick_combat_knockback"),TEXT("快速近战击退距离"),S.QuickCombat.KnockbackCM,TEXT(" cm"),1,false,false);
        Add(TEXT("quick_combat_toughness"),TEXT("快速近战韧性伤害倍率"),S.QuickCombat.ToughnessMultiplier,TEXT("×"),2,false,false);
        Add(TEXT("quick_combat_bleed"),ColdSteelWeaponText::QuickCombatBleed,S.QuickCombat.BleedChance*100,TEXT("%"),0,false,false);
        Add(TEXT("parry_seconds"),TEXT("弹反判定时间"),S.ParrySeconds,TEXT(" s"),2,false,false);
        Add(TEXT("cloven_seconds"),ColdSteelWeaponText::ParryClovenKeep,S.Modifiers.ClovenSeconds,TEXT(" s"),1,false,false);
        Add(TEXT("cloven_physical"),ColdSteelWeaponText::ClovenPhysicalDamage,(S.Modifiers.ClovenPhysical-1)*100,TEXT("%"),0,false,false);
        Add(TEXT("cloven_toughness"),ColdSteelWeaponText::ClovenToughnessDamage,(S.Modifiers.ClovenToughness-1)*100,TEXT("%"),0,false,false);
        Add(TEXT("combo_third_damage"),TEXT("三连击第三段伤害"),S.ComboThirdDamage,TEXT(""),2,false,false);
        Add(TEXT("combo_third_toughness"),RisingDragon?TEXT("第三段升龙韧性伤害倍率"):OverheadFinisher?TEXT("第三段竖劈韧性伤害倍率"):TEXT("第三段突刺韧性伤害倍率"),S.Modifiers.ThirdThrustToughnessMultiplier(),TEXT("×"),2,false,false);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,S.AttackSeconds*1000,TEXT(" ms"),0,true);
        Add(TEXT("melee_stamina"),ColdSteelWeaponText::StaminaCost,S.AttackStamina,TEXT(""),2,true);
        Add(TEXT("block_stamina"),ColdSteelWeaponText::BlockStaminaCost,S.BlockStamina,TEXT(""),2,true,false);
        Add(TEXT("melee_reach"),ColdSteelWeaponText::AttackDistance,S.ThrustReach/100,TEXT(" m"),2);
        Add(TEXT("block_reduction"),TEXT("格挡伤害减免"),S.BlockReduction*100,TEXT("%"),2);
        Add(TEXT("hit_reaction"),TEXT("命中硬直时间倍率"),S.Modifiers.HitReaction,TEXT("×"),2,false,false);
        Add(TEXT("toughness_damage"),ColdSteelWeaponText::ToughnessMultiplier,S.Modifiers.ToughnessDamage,TEXT("×"),2,false,false);
        Add(TEXT("melee_armor_penetration"),TEXT("改造物理防御穿透"),S.Modifiers.PhysicalArmorPenetration*100,TEXT("%"),0,false,false);
        if(!FMath::IsNearlyZero(S.Modifiers.MeleeCriticalChanceAdd))
            Add(TEXT("melee_critical_chance"),TEXT("近战暴击率加成"),S.Modifiers.MeleeCriticalChanceAdd,TEXT("%"),0,false,false);
        if(!FMath::IsNearlyZero(S.Modifiers.MeleeCriticalDamageBonus))
            Add(TEXT("melee_critical_damage"),TEXT("近战暴击伤害加成"),S.Modifiers.MeleeCriticalDamageBonus*100.,TEXT("%"),0,false,false);
    }
    else if(PojunGrip::UsesHammerMotion(Item))
    {
        const auto S=ColdSteelTool::Evaluate(Item,Model);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,S.Damage.Total(),TEXT(""),2);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,S.SwingSeconds*1000,TEXT(" ms"),0,true);
        Add(TEXT("melee_stamina"),ColdSteelWeaponText::StaminaCost,S.StaminaCost,TEXT(""),2,true);
        if(!FMath::IsNearlyEqual(S.HeavyReleaseStaminaCost,S.StaminaCost))
            Add(TEXT("heavy_release_stamina"),TEXT("重击出手体力消耗"),S.HeavyReleaseStaminaCost,TEXT(""),2,true,false);
        Add(TEXT("melee_reach"),ColdSteelWeaponText::AttackDistance,S.CombatReachCM/100,TEXT(" m"),2);
        Add(TEXT("toughness_damage"),ColdSteelWeaponText::ToughnessMultiplier,S.ToughnessDamage,TEXT("×"),2,false,false);
        if(!FMath::IsNearlyZero(S.HeavyChargeSpeedBonus))Add(TEXT("heavy_charge_speed_bonus"),TEXT("重击蓄力速度加成"),S.HeavyChargeSpeedBonus*100.,TEXT("%"),0,false,false);
        if(G){const auto Rune=G->Calculate(Item.Definition,G->Installed(Item)).Melee;
            if(!FMath::IsNearlyZero(Rune.PhysicalAttackAdd))Add(TEXT("physical_attack_add"),TEXT("改造物理攻击力"),Rune.PhysicalAttackAdd,TEXT(""),0,false,false);
            if(Rune.PhysicalArmorPenetration>0.)Add(TEXT("melee_armor_penetration"),TEXT("改造物理防御穿透"),Rune.PhysicalArmorPenetration*100.,TEXT("%"),0,false,false);
            if(Rune.SkillCooldown!=1)Add(TEXT("rune_skill_cooldown"),TEXT("所有技能冷却倍率"),Rune.SkillCooldown,TEXT("×"),2,true,false);
            if(Rune.MartialCooldown!=1)Add(TEXT("martial_cooldown"),TEXT("武技冷却倍率"),Rune.MartialCooldown,TEXT("×"),2,true,false);}
    }
    else if(ColdSteelInventory::IsOneHandedMelee(Item))
    {
        // 单手刀不逐项补列每个派生值：直接属性读同一份近战评估。
        // 距离取 BaseReach：弯刀组件直接用 BaseReach 做命中范围，不走剑类的
        // ScaledReach（×2）扩展；用 SlashReach 会把 220 cm 报成 440 cm。
        const auto S=ColdSteelMelee::Evaluate(Item,Model);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,S.Damage,TEXT(""),2);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,S.AttackSeconds*1000,TEXT(" ms"),0,true);
        Add(TEXT("melee_stamina"),ColdSteelWeaponText::StaminaCost,S.AttackStamina,TEXT(""),2,true);
        Add(TEXT("melee_reach"),ColdSteelWeaponText::AttackDistance,S.BaseReach/100,TEXT(" m"),2);
    }
    else if(ColdSteelInventory::IsEquippedProductionTool(Item))
    {
        // Same metric keys as the swords so the core grid and equipment comparison read alike;
        // only values that genuinely apply to a single-swing production tool are listed.
        // 改造实值走工具评估入口：摘要、提示栏正文与工作台总览读同一份结果。
        const auto S=ColdSteelTool::Evaluate(Item,Model);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,S.Damage.Total(),TEXT(""),2);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,S.Damage.BasePhysical,TEXT(""),2,false,false);
        if(S.Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,S.Damage.AddedPhysical,TEXT(""),2,false,false);
        if(S.Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,S.Damage.AddedMagic,TEXT(""),2,false,false);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,S.SwingSeconds*1000,TEXT(" ms"),0,true);
        // A tool swing spends the harvest cost whether it hits a tree, rock or enemy.
        Add(TEXT("melee_stamina"),ColdSteelWeaponText::StaminaCost,S.StaminaCost,TEXT(""),2,true);
        Add(TEXT("melee_reach"),ColdSteelWeaponText::AttackDistance,S.CombatReachCM/100,TEXT(" m"),2);
        Add(TEXT("harvest_yield"),ColdSteelWeaponText::HarvestYieldMultiplier,S.HarvestYield,TEXT("×"),2,false,false);
        // Trees and rocks both settle on health (2026-09-30 rocks unified): expose per-swing damage only.
        Add(TEXT("harvest_damage"),ColdSteelInventory::Text(Item,TEXT("tool_kind"))==TEXT("pickaxe")?TEXT("采矿伤害"):TEXT("伐木伤害"),
            ProductionTreeHealth::StrikeDamage(S),TEXT(" / 挥"),2,false,false);
        Add(TEXT("harvest_reach"),ColdSteelWeaponText::HarvestDistance,S.HarvestReachCM/100,TEXT(" m"),2,false,false);
        if(S.HarvestRadiusCM>0)Add(TEXT("harvest_radius"),ColdSteelWeaponText::HarvestRadius,S.HarvestRadiusCM,TEXT(" cm"),0,false,false);
        if(S.BonusHarvestChance>0)Add(TEXT("bonus_harvest"),TEXT("额外产出几率"),S.BonusHarvestChance*100,TEXT("%"),0,false,false);
    }
    else if(Item.Definition==TEXT("ue_alchemy_spellbook"))
    {
        if(Model)Add(TEXT("equipment_magic_attack"),ColdSteelWeaponText::EquipmentMagicAttack,Model->ItemMagicAttack(Item),TEXT(""),2,false,true,1);
    }
    else if(ColdSteelInventory::Text(Item,TEXT("weaponType"))==TEXT("staff"))
    {
        const auto Damage=ColdSteelWeaponStats::DamageParts(Item,Model,3);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,Damage.Total(),TEXT(""),2);
        if(Model)Add(TEXT("equipment_magic_attack"),ColdSteelWeaponText::EquipmentMagicAttack,Model->ItemMagicAttack(Item),TEXT(""),2,false,true,1);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,Damage.BasePhysical,TEXT(""),2,false,false);
        if(Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,Damage.AddedPhysical,TEXT(""),2,false,false);
        if(Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,Damage.AddedMagic,TEXT(""),2,false,false);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,ColdSteelWeaponStats::Interval(&Item,Model,.5)*1000,TEXT(" ms"),0,true);
    }
    if(Model)
    {
        const auto* E=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        if(E&&E->Defense(Item)>0)Add(TEXT("defense"),TEXT("防御力"),E->Defense(Item),TEXT(""),2,false,true,1);
        // 魔法防御只在装备声明了 magicBase/magicPerEnhance 时出现，与主卡同源。
        if(E&&E->MagicDefense(Item)>0)Add(TEXT("magic_defense"),TEXT("魔法防御力"),E->MagicDefense(Item),TEXT(""),2,false,true,1);
    }
    if(const auto Data=CombatItemFormula::ReadOnly(Item))
    {
        const TSharedPtr<FJsonObject>* Bonus=nullptr;
        if(Data->TryGetObjectField(TEXT("bonusStats"),Bonus)&&*Bonus)
        {
            const TSharedPtr<FJsonObject>* PerEnhance=nullptr;
            Data->TryGetObjectField(TEXT("bonusPerEnhance"),PerEnhance);
            const double BonusLevel=CombatItemFormula::EquipmentEnhancementLevel(Data);
            const TPair<const TCHAR*,const TCHAR*> Fields[]={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")},{TEXT("atk"),TEXT("物理攻击")},{TEXT("matk"),TEXT("魔法攻击")},{TEXT("maxHp"),TEXT("最大生命")},{TEXT("maxHpPercent"),TEXT("最大生命")},{TEXT("maxMp"),TEXT("最大魔法")},{TEXT("crit"),TEXT("暴击率")},{TEXT("critDamageBonus"),TEXT("暴击伤害")},{TEXT("critRes"),TEXT("暴击抵抗")},{TEXT("stunResist"),TEXT("眩晕抵抗")},{TEXT("meleeDamagePercent"),TEXT("近战物理攻击")},{TEXT("meleeAttackSpeed"),TEXT("近战攻击速度")},{TEXT("meleeStaminaCost"),TEXT("近战体力消耗")},{TEXT("moveSpeedPercent"),TEXT("移动速度")},{TEXT("reloadSpeed"),TEXT("换弹速度")},{TEXT("firearmRecoilPercent"),TEXT("枪械后坐力")},{TEXT("firearmStabilityPercent"),TEXT("枪械稳定性")},{TEXT("bowNockSpeed"),TEXT("搭箭速度")},{TEXT("bowDrawSpeed"),TEXT("拉弓速度")},{TEXT("adsPercent"),TEXT("ADS 瞄准时间")},{TEXT("sprintStaminaCost"),TEXT("奔跑体力消耗")},{TEXT("magicAttackPercent"),TEXT("魔法攻击力")},{TEXT("castRangePercent"),TEXT("施法距离")},{TEXT("castSpeedPercent"),TEXT("施法速度")},{TEXT("magicCooldownPercent"),TEXT("魔法冷却")},{TEXT("magicCostPercent"),TEXT("魔法消耗")}};
            for(const auto& Field:Fields)
            {
                double Value=0,PerLevel=0;(*Bonus)->TryGetNumberField(Field.Key,Value);
                if(PerEnhance&&*PerEnhance)(*PerEnhance)->TryGetNumberField(Field.Key,PerLevel);
                Value+=PerLevel*BonusLevel;
                if(Value!=0)
                {
                    const bool Percent=FCString::Strcmp(Field.Key,TEXT("firearmRecoilPercent"))==0||FCString::Strcmp(Field.Key,TEXT("firearmStabilityPercent"))==0||FCString::Strcmp(Field.Key,TEXT("crit"))==0||FCString::Strcmp(Field.Key,TEXT("critDamageBonus"))==0||FCString::Strcmp(Field.Key,TEXT("critRes"))==0||FCString::Strcmp(Field.Key,TEXT("stunResist"))==0||FCString::Strcmp(Field.Key,TEXT("meleeAttackSpeed"))==0||FCString::Strcmp(Field.Key,TEXT("meleeStaminaCost"))==0||FCString::Strcmp(Field.Key,TEXT("maxHpPercent"))==0||FCString::Strcmp(Field.Key,TEXT("meleeDamagePercent"))==0||FCString::Strcmp(Field.Key,TEXT("moveSpeedPercent"))==0||FCString::Strcmp(Field.Key,TEXT("reloadSpeed"))==0||FCString::Strcmp(Field.Key,TEXT("bowNockSpeed"))==0||FCString::Strcmp(Field.Key,TEXT("bowDrawSpeed"))==0||FCString::Strcmp(Field.Key,TEXT("adsPercent"))==0||FCString::Strcmp(Field.Key,TEXT("sprintStaminaCost"))==0||FCString::Strcmp(Field.Key,TEXT("magicAttackPercent"))==0||FCString::Strcmp(Field.Key,TEXT("castRangePercent"))==0||FCString::Strcmp(Field.Key,TEXT("castSpeedPercent"))==0||FCString::Strcmp(Field.Key,TEXT("magicCooldownPercent"))==0||FCString::Strcmp(Field.Key,TEXT("magicCostPercent"))==0;
                    const bool PointPercent=FCString::Strcmp(Field.Key,TEXT("crit"))==0||FCString::Strcmp(Field.Key,TEXT("critRes"))==0||FCString::Strcmp(Field.Key,TEXT("stunResist"))==0;
                    const bool LowerBetter=FCString::Strcmp(Field.Key,TEXT("firearmRecoilPercent"))==0||FCString::Strcmp(Field.Key,TEXT("meleeStaminaCost"))==0||FCString::Strcmp(Field.Key,TEXT("adsPercent"))==0||FCString::Strcmp(Field.Key,TEXT("sprintStaminaCost"))==0||FCString::Strcmp(Field.Key,TEXT("magicCooldownPercent"))==0||FCString::Strcmp(Field.Key,TEXT("magicCostPercent"))==0;
                    const int32 Tone=Value<0?(LowerBetter?1:-1):(LowerBetter?-1:1);
                    Add(*(FString(TEXT("bonus:"))+Field.Key),Field.Value,Value*(Percent&&!PointPercent?100.:1.),Percent?TEXT("%"):TEXT(""),2,LowerBetter,true,Tone);
                }
            }
        }
    }
    return Result;
}
}

bool ResolveColdSteelTooltipSet(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipSetInfo& Out)
{
    return BuildSetInfo(Item,Model,Out);
}

void CompleteColdSteelTooltipSummary(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* G,FColdSteelTooltipContent& Out)
{
    using namespace ColdSteelInventory;
    const auto* Weapon=G?G->Weapon(Item.Definition):nullptr;
    // All production tools share the wide presentation, not just axe/pickaxe;
    // the shovel's terrain rules need the same room the harvest tools get.
    Out.bWideIcon=Weapon||ColdSteelInventory::IsBow(Item)||ColdSteelInventory::IsStaff(Item)||ColdSteelInventory::IsMeleeWeapon(Item)||ColdSteelInventory::Text(Item,TEXT("category"))==TEXT("tool");
    if(Out.Location.IsEmpty())
        Out.Location=Item.Place==1?TEXT("已装备"):Item.Place==4?TEXT("仓库"):Item.Place==ColdSteelCompartment::Place?TEXT("夹层"):TEXT("背包");
    if(Item.Place==1&&SlotNames().IsValidIndex(Item.Cell))Out.Location+=TEXT(" · ")+SlotNames()[Item.Cell];
    if(Model&&Model->Equipped()&&Model->Equipped()->InstanceId==Item.InstanceId)Out.Location+=TEXT(" · 当前武器");
    if(Weapon)Out.Location+=TEXT(" · ")+ColdSteelWeaponStats::AmmoName(Weapon->Ammo);
    if(ColdSteelInventory::Text(Item,TEXT("equipSlot"))==TEXT("backpack"))
    {
        // 背包缩略摘要只列容量；复用实际网格口径，旧存档同样读取当前目录。
        auto PreviewBag=Item;PreviewBag.Place=1;PreviewBag.Cell=14;
        const int32 ExtraRows=BagRows({PreviewBag})-BagRows({});
        const FIntPoint Grid=CompartmentGridOf(Item);
        Out.Summary.Reset();
        Out.Summary.Add({TEXT("添加背包格子"),FString::Printf(TEXT("+%d格子（%d行）"),ExtraRows*18,ExtraRows)});
        Out.Summary.Add({TEXT("夹层格子"),FString::Printf(TEXT("%d×%d"),Grid.X,Grid.Y)});
        return;
    }
    // 食物／饮料／药水的简略浮窗与详细浮窗共用同一套标准行序；不走武器指标与对比。
    const auto ConsumableData=CombatItemFormula::ReadOnly(Item);
    if(ConsumableData&&ColdSteelConsumable::IsConsumable(ConsumableData.Get()))
    {
        TArray<ColdSteelConsumable::FRow> Rows;
        ColdSteelConsumable::BuildSummaryRows(Item,Model,ConsumableData.Get(),Rows,4);
        for(const auto& R:Rows)
            if(!R.bSection&&!R.Label.IsEmpty())Out.Summary.Add({R.Label,R.Value,R.Tone});
        if(Out.Summary.IsEmpty())Out.Summary.Add({TEXT("分类"),Out.Type});
        Out.ValueScope=ColdSteelConsumable::ValueScope(Item,ConsumableData.Get());
        return;
    }
    auto Values=Metrics(Item,Model,G);
    if(Weapon)
    {
        const bool Burst=Values.ContainsByPredicate([](const auto& V){return V.Key==TEXT("burst_interval");});
        for(const TCHAR* Key:{TEXT("damage"),Burst?TEXT("burst_interval"):TEXT("attack_interval"),TEXT("capacity"),TEXT("effective_range"),TEXT("reload"),TEXT("empty_reload")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsBow(Item))
    {
        for(const TCHAR* Key:{TEXT("damage"),TEXT("draw_seconds"),TEXT("nock_seconds"),TEXT("effective_range"),TEXT("bow_stamina"),TEXT("ads")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsTwoHandedSword(Item)||ColdSteelInventory::IsTwoHandedBlunt(Item))
    {
        // Shared melee order in hover and pinned views. Blunt weapons omit the
        // sword-only block metric because their evaluator does not provide it.
        for(const TCHAR* Key:{TEXT("damage"),TEXT("attack_interval"),TEXT("melee_stamina"),TEXT("melee_reach"),TEXT("block_reduction")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsOneHandedMelee(Item))
    {
        // 单手刀沿用近战字段顺序，但没有格挡与连段分段：缺机制就不造字段。
        for(const TCHAR* Key:{TEXT("damage"),TEXT("attack_interval"),TEXT("melee_stamina"),TEXT("melee_reach")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsEquippedProductionTool(Item))
    {
        for(const TCHAR* Key:{TEXT("damage"),TEXT("attack_interval"),TEXT("melee_stamina"),TEXT("melee_reach")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else
    {
        const bool bHasTone=Values.ContainsByPredicate([](const auto& V){return V.Core&&V.Tone!=0;});
        const bool bHasNeutralCore=Values.ContainsByPredicate([](const auto& V){return V.Core&&V.Tone==0;});
        if(bHasTone&&!bHasNeutralCore)
        {
            auto Signed=[&](const FMetric& V)
            {
                FString Text=Format(V.Value,V.Digits)+V.Unit;
                if(!Text.StartsWith(TEXT("+"))&&!Text.StartsWith(TEXT("-")))Text=TEXT("+")+Text;
                return Text;
            };
            TArray<FMetric> Buffs,Debuffs;
            for(const auto& V:Values)if(V.Core)(V.Tone>0?Buffs:Debuffs).Add(V);
            if(!Buffs.IsEmpty())
            {
                Out.Summary.Add({TEXT("增益"),FString(),1,true});
                for(const auto& V:Buffs)Out.Summary.Add({V.Label,Signed(V),V.Tone});
            }
            if(!Debuffs.IsEmpty())
            {
                Out.Summary.Add({TEXT("减益"),FString(),-1,true});
                for(const auto& V:Debuffs)Out.Summary.Add({V.Label,Signed(V),V.Tone});
            }
        }
        else for(const auto& V:Values)if(V.Core&&Out.Summary.Num()<4)Out.Summary.Add({V.Label,Format(V.Value,V.Digits)+V.Unit});
    }
    if(Item.Definition==TEXT("ue_alchemy_spellbook"))Out.ValueScope=TEXT("装备魔攻按当前智力、精神与强化等级计算；装备于当前副手时生效。");
    else if(ColdSteelInventory::IsBow(Item))Out.ValueScope=ColdSteelWeaponText::BowScope;
    else if(PojunGrip::Installed(Item))Out.ValueScope=TEXT("按破军长柄的双手锤式普通挥击计算攻击距离和单次攻击体力。");
    else if(ColdSteelInventory::IsTwoHandedSword(Item))Out.ValueScope=TEXT("按当前角色、强化和改造计算，以普通攻击为准；伤害未计暴击、要害和目标防御。体力为单次攻击消耗；最大攻击距离含突刺。");
    else if(ColdSteelInventory::IsTwoHandedBlunt(Item))Out.ValueScope=TEXT("按当前角色、强化和改造计算，以普通钝击为准；伤害未计暴击、要害和目标防御。体力为单次普通攻击消耗；最大攻击距离为普通挥击范围。");
    else if(ColdSteelInventory::IsEquippedProductionTool(Item))Out.ValueScope=TEXT("按当前角色与改造计算，以单次挥砍为准；伤害未计暴击、要害、目标防御及距离衰减。采集数值独立列出。");
    else if(Weapon)Out.ValueScope=TEXT("按当前角色、强化和改造计算，以单次射击为准；武器总伤害未计弹种倍率、暴击、要害、目标防御及距离衰减。后坐力指数越低越好，枪械稳定性越高越好。");
    else if(Values.ContainsByPredicate([](const auto& V){return V.Key==TEXT("damage");}))Out.ValueScope=TEXT("按当前角色、强化和改造计算，以普通攻击为准；伤害未计暴击、要害和目标防御。");
    else if(!Values.IsEmpty())Out.ValueScope=TEXT("物品属性；防御包含强化，属性加成按物品标注显示。");
    if(Out.Summary.Num()<4&&!Out.Summary.ContainsByPredicate([](const auto& R){return R.bSection&&(R.Label==TEXT("增益")||R.Label==TEXT("减益"));})&&!Out.Cards.IsEmpty())
    {
        // 祭品／材料这类没有 Weapons 评估的物品，其增益与代价都在目录 stats 里，
        // 数值自带正负号。旧逻辑只按固定白名单取前四行，会把「移动速度 +2%」丢掉、
        // 只剩代价，或只留半边；这里按符号分「增益 / 减益」两块，与 2.23 摘要规则一致。
        // 整行仍是目录原文，不重新计算，也不截断行数。
        const auto& Rows=Out.Cards.Last().Rows;
        auto ToneOf=[](const FString& Value)
        {
            if(Value.StartsWith(TEXT("-")))return -1;
            if(Value.StartsWith(TEXT("+")))return 1;
            return 0;
        };
        const bool bSigned=Rows.ContainsByPredicate([&](const auto& R)
            {return !R.bSection&&!R.Label.IsEmpty()&&ToneOf(R.Value)!=0;});
        if(bSigned)
        {
            TArray<FColdSteelTooltipRow> Buffs,Debuffs,Neutral;
            for(const auto& R:Rows)
            {
                if(R.bSection||R.Label.IsEmpty())continue;
                const int32 Tone=R.Tone!=0?R.Tone:ToneOf(R.Value);
                // 没有正负号的行不是数值修正，而是该物品独有的具名机制
                // （金刚不坏、月影、点石成金、血藤寄生……）。这些不能因为
                // 分组就被丢掉，单独排在增益块最前面、保留原文。
                // Tone 记 1：渲染层按 Tone>0 取金色、否则取墨黑（＝减益色），
                // 留 0 会让机制行看起来像代价。
                if(Tone==0)Neutral.Add({R.Label,R.Value,1});
                else (Tone>0?Buffs:Debuffs).Add({R.Label,R.Value,Tone});
            }
            TArray<FColdSteelTooltipRow> Ordered;
            Ordered.Append(Neutral);
            Ordered.Append(Buffs);
            if(!Ordered.IsEmpty())
            {
                Out.Summary.Add({TEXT("增益"),FString(),1,true});
                Out.Summary.Append(Ordered);
            }
            if(!Debuffs.IsEmpty())
            {
                Out.Summary.Add({TEXT("减益"),FString(),-1,true});
                Out.Summary.Append(Debuffs);
            }
        }
        else
        {
            const TSet<FString> CoreLabels={TEXT("恢复生命"),TEXT("恢复魔法"),TEXT("恢复最大生命"),TEXT("恢复最大魔法"),TEXT("冷却时间"),TEXT("堆叠数量"),TEXT("物理攻击"),TEXT("魔法攻击"),TEXT("最大生命"),TEXT("最大魔法")};
            for(const auto& R:Rows)if(!R.bSection&&CoreLabels.Contains(R.Label)&&Out.Summary.Num()<4)
                if(!Out.Summary.ContainsByPredicate([&](const auto& Existing){return Existing.Label==R.Label;}))Out.Summary.Add(R);
        }
    }
    if(Out.Summary.IsEmpty())Out.Summary.Add({TEXT("分类"),Out.Type});
    // 套装信息排在数值下方、对比之前：先看这件穿上有多少，再看凑齐能给什么。
    // 主卡构建时已算过并写进 Out.Set／bHasSet；没算过才补算，
    // 避免同一个物品把装备五槽数两遍。
    if(!Out.bHasSet)Out.bHasSet=BuildSetInfo(Item,Model,Out.Set);
    if(!Model)return;
    int32 CompareSlot=INDEX_NONE;
    if(Item.Place==1)CompareSlot=Item.Cell;
    else
    {
        const int32 Active=Model->Snapshot().ActiveWeaponSlot;
        if(CanEquip(Item,Active))CompareSlot=Active;
        else if(CanEquip(Item,Active+2))CompareSlot=Active+2;
        else for(int32 Index=0;Index<SlotNames().Num();++Index)if(CanEquip(Item,Index)){CompareSlot=Index;break;}
    }
    if(CompareSlot==INDEX_NONE)return;
    const auto* Other=Model->Equipped(CompareSlot);
    if(!Other){Out.ComparisonTitle=SlotNames()[CompareSlot]+TEXT("为空");return;}
    if(Other->InstanceId==Item.InstanceId){Out.ComparisonTitle=TEXT("当前已装备此物品");return;}
    Out.ComparisonTitle=TEXT("对比 ")+SlotNames()[CompareSlot]+TEXT(" · ")+Text(*Other,TEXT("name"));
    if(ColdSteelInventory::IsBow(Item)||ColdSteelInventory::IsBow(*Other))Out.ComparisonTitle+=TEXT(" · 弓按满弓伤害比较");
    if(ColdSteelInventory::IsTwoHandedSword(Item)&&ColdSteelInventory::IsTwoHandedSword(*Other))
    {
        const bool AreaBefore=ColdSteelMelee::Evaluate(*Other,Model).QuickCombat.bAreaHit;
        const bool AreaAfter=ColdSteelMelee::Evaluate(Item,Model).QuickCombat.bAreaHit;
        if(AreaBefore!=AreaAfter)
            Out.Comparison.Add({TEXT("快速近战命中方式"),AreaAfter?TEXT("单目标 → 范围多目标（范围不变）"):TEXT("范围多目标 → 单目标"),AreaAfter?1:-1});
    }
    const auto Before=Metrics(*Other,Model,G);
    for(const auto& B:Before)if(B.Key.ToString().StartsWith(TEXT("bonus:"))&&!Values.ContainsByPredicate([&](const auto& V){return V.Key==B.Key;}))
    {auto Missing=B;Missing.Value=0;Values.Add(Missing);}
    for(const auto& V:Values)
    {
        const auto* B=Before.FindByPredicate([&](const auto& Entry){return Entry.Key==V.Key;});
        if(!B&&!V.Key.ToString().StartsWith(TEXT("bonus:")))continue;
        const double Base=B?B->Value:0,Delta=V.Value-Base;
        const int32 Tone=Format(Delta,V.Digits)==TEXT("0")?0:((Delta>0)!=V.Lower?1:-1);
        const FString Difference=(Tone!=0&&Delta>0?TEXT("+"):TEXT(""))+Format(Delta,V.Digits)+V.Unit;
        Out.Comparison.Add({V.Label,Difference+TEXT("  (")+Format(Base,V.Digits)+TEXT(" → ")+Format(V.Value,V.Digits)+TEXT(")"),Tone,false,false,Difference});
    }
}
