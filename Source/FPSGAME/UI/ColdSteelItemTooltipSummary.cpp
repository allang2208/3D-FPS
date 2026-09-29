#include "ColdSteelWeaponText.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelEnhancementSystem.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../Movement/FPSStaminaTuning.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FMetric {FName Key;FString Label,Unit;double Value=0;int32 Digits=0;bool Lower=false,Core=true;};
FString Format(double Value,int32 Digits)
{
    FString Result=FString::Printf(TEXT("%.*f"),Digits,Value);
    if(Digits>0){while(Result.EndsWith(TEXT("0")))Result.LeftChopInline(1);if(Result.EndsWith(TEXT(".")))Result.LeftChopInline(1);}
    return Result==TEXT("-0")?TEXT("0"):Result;
}
TArray<FMetric> Metrics(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* G)
{
    TArray<FMetric> Result;
    auto Add=[&](const TCHAR* Key,const TCHAR* Label,double Value,const TCHAR* Unit,int32 Digits=0,bool Lower=false,bool Core=true)
        {Result.Add({FName(Key),Label,Unit,Value,Digits,Lower,Core});};
    if(G&&G->Weapon(Item.Definition))
    {
        auto S=G->Calculate(Item.Definition,G->Installed(Item));
        const auto Damage=ColdSteelWeaponStats::DamageParts(Item,Model,S.Damage);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,Damage.Total(),TEXT(""),2);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,Damage.BasePhysical,TEXT(""),2,false,false);
        if(Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,Damage.AddedPhysical,TEXT(""),2,false,false);
        if(Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,Damage.AddedMagic,TEXT(""),2,false,false);
        Add(S.BurstCount>1?TEXT("burst_interval"):TEXT("attack_interval"),S.BurstCount>1?TEXT("组内射击间隔"):ColdSteelWeaponText::AttackInterval,ColdSteelWeaponStats::Interval(&Item,Model,S.Interval)*1000,TEXT(" ms"),0,true);
        Add(TEXT("reload"),ColdSteelWeaponText::Reload,ColdSteelWeaponStats::Reload(&Item,Model,S.Reload),TEXT(" s"),2,true);
        Add(TEXT("capacity"),ColdSteelWeaponText::Capacity,S.Capacity,TEXT(" 发"));
        Add(TEXT("ads"),ColdSteelWeaponText::ADS,S.ADS*1000,TEXT(" ms"),0,true,false);
        Add(TEXT("empty_reload"),ColdSteelWeaponText::EmptyReload,ColdSteelWeaponStats::Reload(&Item,Model,S.EmptyReload),TEXT(" s"),2,true);
        Add(TEXT("recoil"),TEXT("后坐力指数"),S.Recoil,TEXT(""),1,true,false);
        Add(TEXT("stability"),TEXT("枪械稳定性"),S.Handling.Stability,TEXT(" 分"),1,false,false);
        Add(TEXT("effective_range"),ColdSteelWeaponText::EffectiveRange,S.Range,TEXT(" m"),2);
    }
    else if(ColdSteelInventory::IsBow(Item))
    {
        const auto Bow=ColdSteelBow::Evaluate(Item,Model);const auto& Damage=Bow.Damage;
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,Damage.Total(),TEXT(""),2);
        Add(TEXT("draw_seconds"),ColdSteelWeaponText::DrawTime,Bow.Draw,TEXT(" s"),2,true);
        Add(TEXT("nock_seconds"),ColdSteelWeaponText::NockTime,Bow.Nock,TEXT(" s"),2,true);
        Add(TEXT("flight_limit"),ColdSteelWeaponText::FlightLimit,ColdSteelInventory::Number(Item,TEXT("range_cm"),3200)/100,TEXT(" m"),2);
        Add(TEXT("projectile_speed"),ColdSteelWeaponText::ProjectileSpeed,Bow.Speed,TEXT(" m/s"),2,false,false);
        Add(TEXT("bow_stamina"),ColdSteelWeaponText::StaminaCost,Bow.Stamina,TEXT(""),2,true,false);
        Add(TEXT("bow_hold"),ColdSteelWeaponText::HoldTime,Bow.Hold,TEXT(" s"),2,false,false);
        Add(TEXT("bow_sway"),ColdSteelWeaponText::Sway,Bow.Sway,TEXT(""),2,true,false);
        Add(TEXT("ads"),ColdSteelWeaponText::ADS,Bow.ADS*1000,TEXT(" ms"),0,true,false);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,Damage.BasePhysical,TEXT(""),2,false,false);
        if(Damage.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,Damage.AddedPhysical,TEXT(""),2,false,false);
        if(Damage.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,Damage.AddedMagic,TEXT(""),2,false,false);
    }
    else if(ColdSteelInventory::IsTwoHandedSword(Item))
    {
        const auto S=ColdSteelMelee::Evaluate(Item,Model);
        Add(TEXT("damage"),ColdSteelWeaponText::TotalDamage,S.Damage,TEXT(""),2);
        Add(TEXT("combo_second_damage"),TEXT("三连击第二段伤害"),S.ComboSecondDamage,TEXT(""),2,false,false);
        Add(TEXT("base_physical_damage"),ColdSteelWeaponText::BasePhysical,S.DamageParts.BasePhysical,TEXT(""),2,false,false);
        if(S.DamageParts.AddedPhysical>0)Add(TEXT("added_physical_damage"),ColdSteelWeaponText::AddedPhysical,S.DamageParts.AddedPhysical,TEXT(""),2,false,false);
        if(S.DamageParts.AddedMagic>0)Add(TEXT("added_magic_damage"),ColdSteelWeaponText::AddedMagic,S.DamageParts.AddedMagic,TEXT(""),2,false,false);
        if(S.Modifiers.MagicCooldown!=1)Add(TEXT("rune_magic_cooldown"),TEXT("魔法技能冷却倍率"),S.Modifiers.MagicCooldown,TEXT("×"),2,true,false);
        if(S.Modifiers.MagicDamage!=1)Add(TEXT("rune_magic_mult"),TEXT("魔法伤害倍率"),S.Modifiers.MagicDamage,TEXT("×"),2,false,false);
        if(S.Modifiers.MagicCost!=1)Add(TEXT("rune_magic_cost"),TEXT("魔法值消耗倍率"),S.Modifiers.MagicCost,TEXT("×"),2,true,false);
        Add(TEXT("ballast_heavy_mult"),TEXT("重击伤害倍率"),S.HeavyMultiplier,TEXT("×"),2,false,false);
        if(S.KnockbackCM>0)Add(TEXT("melee_knockback"),TEXT("攻击击退距离"),S.KnockbackCM,TEXT(" cm"),1,false,false);
        Add(TEXT("quick_combat_damage_mult"),TEXT("快速近战伤害倍率"),S.QuickCombat.DamageMultiplier,TEXT("×"),2,false,false);
        Add(TEXT("quick_combat_damage"),TEXT("快速近战伤害"),S.QuickCombat.Damage,TEXT(""),2,false,false);
        Add(TEXT("quick_combat_knockback"),TEXT("快速近战击退距离"),S.QuickCombat.KnockbackCM,TEXT(" cm"),1,false,false);
        Add(TEXT("parry_seconds"),TEXT("弹反判定时间"),S.ParrySeconds,TEXT(" s"),2,false,false);
        Add(TEXT("cloven_seconds"),TEXT("承锋·瞬重斩保留时间"),S.Modifiers.ClovenSeconds,TEXT(" s"),1,false,false);
        Add(TEXT("cloven_physical"),TEXT("承锋重击物理伤害加成"),(S.Modifiers.ClovenPhysical-1)*100,TEXT("%"),0,false,false);
        Add(TEXT("cloven_toughness"),TEXT("承锋重击韧性伤害加成"),(S.Modifiers.ClovenToughness-1)*100,TEXT("%"),0,false,false);
        Add(TEXT("combo_third_damage"),TEXT("三连击第三段伤害"),S.ComboThirdDamage,TEXT(""),2,false,false);
        Add(TEXT("attack_interval"),ColdSteelWeaponText::AttackInterval,S.AttackSeconds*1000,TEXT(" ms"),0,true);
        Add(TEXT("melee_stamina"),ColdSteelWeaponText::StaminaCost,S.AttackStamina,TEXT(""),2,true);
        Add(TEXT("block_stamina"),ColdSteelWeaponText::BlockStaminaCost,S.BlockStamina,TEXT(""),2,true,false);
        Add(TEXT("melee_reach"),ColdSteelWeaponText::AttackDistance,S.ThrustReach/100,TEXT(" m"),2);
        Add(TEXT("block_reduction"),TEXT("格挡伤害减免"),S.BlockReduction*100,TEXT("%"),2);
        Add(TEXT("hit_reaction"),TEXT("命中硬直时间倍率"),S.Modifiers.HitReaction,TEXT("×"),2,false,false);
        Add(TEXT("toughness_damage"),TEXT("韧性伤害倍率"),S.Modifiers.ToughnessDamage,TEXT("×"),2,false,false);
        Add(TEXT("melee_armor_penetration"),TEXT("改造物理防御穿透"),S.Modifiers.PhysicalArmorPenetration*100,TEXT("%"),0,false,false);

    }
    if(Model)
    {
        const auto* E=Model->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        if(E&&E->Defense(Item)>0)Add(TEXT("defense"),TEXT("防御力"),E->Defense(Item),TEXT(""),2);
    }
    TSharedPtr<FJsonObject> Data;
    if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)&&Data)
    {
        const TSharedPtr<FJsonObject>* Bonus=nullptr;
        if(Data->TryGetObjectField(TEXT("bonusStats"),Bonus))
        {
            const TPair<const TCHAR*,const TCHAR*> Fields[]={{TEXT("str"),TEXT("力量")},{TEXT("dex"),TEXT("敏捷")},{TEXT("int"),TEXT("智力")},{TEXT("con"),TEXT("体质")},{TEXT("wis"),TEXT("精神")},{TEXT("luck"),TEXT("幸运")},{TEXT("atk"),TEXT("物理攻击")},{TEXT("matk"),TEXT("魔法攻击")},{TEXT("maxHp"),TEXT("最大生命")},{TEXT("maxMp"),TEXT("最大魔法")},{TEXT("crit"),TEXT("暴击率")},{TEXT("reloadSpeed"),TEXT("换弹速度")},{TEXT("bowDrawSpeed"),TEXT("拉弓速度")}};
            for(const auto& Field:Fields)
            {
                double Value=0;if((*Bonus)->TryGetNumberField(Field.Key,Value)&&Value!=0)
                {
                    const bool Percent=FCString::Strcmp(Field.Key,TEXT("crit"))==0||FCString::Strcmp(Field.Key,TEXT("reloadSpeed"))==0||FCString::Strcmp(Field.Key,TEXT("bowDrawSpeed"))==0;
                    Add(*(FString(TEXT("bonus:"))+Field.Key),Field.Value,Value*(Percent&&FCString::Strcmp(Field.Key,TEXT("crit"))!=0?100.:1.),Percent?TEXT("%"):TEXT(""),2);
                }
            }
        }
    }
    return Result;
}
}

void CompleteColdSteelTooltipSummary(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* G,FColdSteelTooltipContent& Out)
{
    using namespace ColdSteelInventory;
    const auto* Weapon=G?G->Weapon(Item.Definition):nullptr;
    Out.bWideIcon=Weapon||ColdSteelInventory::IsBow(Item)||ColdSteelInventory::IsTwoHandedSword(Item)||ColdSteelInventory::IsEquippedProductionTool(Item);
    Out.Location=Item.Place==1?TEXT("已装备"):Item.Place==4?TEXT("仓库"):TEXT("背包");
    if(Item.Place==1&&SlotNames().IsValidIndex(Item.Cell))Out.Location+=TEXT(" · ")+SlotNames()[Item.Cell];
    if(Model&&Model->Equipped()&&Model->Equipped()->InstanceId==Item.InstanceId)Out.Location+=TEXT(" · 当前武器");
    if(Weapon)Out.Location+=TEXT(" · ")+ColdSteelWeaponStats::AmmoName(Weapon->Ammo);
    auto Values=Metrics(Item,Model,G);
    if(Weapon)
    {
        const bool Burst=Values.ContainsByPredicate([](const auto& V){return V.Key==TEXT("burst_interval");});
        for(const TCHAR* Key:{TEXT("damage"),Burst?TEXT("burst_interval"):TEXT("attack_interval"),TEXT("capacity"),TEXT("effective_range"),TEXT("reload"),TEXT("empty_reload")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsBow(Item))
    {
        for(const TCHAR* Key:{TEXT("damage"),TEXT("draw_seconds"),TEXT("nock_seconds"),TEXT("flight_limit"),TEXT("bow_stamina"),TEXT("ads")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else if(ColdSteelInventory::IsTwoHandedSword(Item))
    {
        for(const TCHAR* Key:{TEXT("damage"),TEXT("attack_interval"),TEXT("melee_stamina"),TEXT("melee_reach"),TEXT("block_reduction")})
            if(const auto* V=Values.FindByPredicate([&](const auto& Entry){return Entry.Key==Key;}))Out.Summary.Add({V->Label,Format(V->Value,V->Digits)+V->Unit});
    }
    else for(const auto& V:Values)if(V.Core&&Out.Summary.Num()<4)Out.Summary.Add({V.Label,Format(V.Value,V.Digits)+V.Unit});
    if(ColdSteelInventory::IsBow(Item))Out.ValueScope=ColdSteelWeaponText::BowScope;
    else if(ColdSteelInventory::IsTwoHandedSword(Item))Out.ValueScope=TEXT("按当前角色、强化和改造计算，以普通攻击为准；伤害未计暴击、要害和目标防御。体力为单次攻击消耗；最大攻击距离含突刺。");
    else if(ColdSteelInventory::IsEquippedProductionTool(Item))Out.ValueScope=TEXT("按当前角色与改造计算，以单次挥砍为准；伤害未计暴击、要害、目标防御及距离衰减。采集数值独立列出。");
    else if(Weapon)Out.ValueScope=TEXT("按当前角色、强化和改造计算，以单次射击为准；武器总伤害未计弹种倍率、暴击、要害、目标防御及距离衰减。");
    else if(Values.ContainsByPredicate([](const auto& V){return V.Key==TEXT("damage");}))Out.ValueScope=TEXT("按当前角色、强化和改造计算，以普通攻击为准；伤害未计暴击、要害和目标防御。");
    else if(!Values.IsEmpty())Out.ValueScope=TEXT("物品属性；防御包含强化，属性加成按物品标注显示。");
    if(Out.Summary.Num()<4&&!Out.Cards.IsEmpty())
    {
        const TSet<FString> CoreLabels={TEXT("恢复生命"),TEXT("恢复魔法"),TEXT("恢复最大生命"),TEXT("恢复最大魔法"),TEXT("冷却时间"),TEXT("堆叠数量"),TEXT("物理攻击"),TEXT("魔法攻击"),TEXT("最大生命"),TEXT("最大魔法")};
        for(const auto& R:Out.Cards.Last().Rows)if(!R.bSection&&CoreLabels.Contains(R.Label)&&Out.Summary.Num()<4)
            if(!Out.Summary.ContainsByPredicate([&](const auto& Existing){return Existing.Label==R.Label;}))Out.Summary.Add(R);
    }
    if(Out.Summary.IsEmpty())Out.Summary.Add({TEXT("分类"),Out.Type});
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
