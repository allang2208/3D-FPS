#include "ColdSteelItemTooltipData.h"
#include "ColdSteelConsumablePresentation.h"
#include "../Building/ForgingQuality.h"
#include "../Building/ForgingSystem.h"
#include "../Building/GunAssemblyQuality.h"
#include "ColdSteelFoodPresentation.h"
#include "../Items/FoodSpoilage.h"
#include "ColdSteelItemRarity.h"
#include "../Building/WoodworkingQuality.h"
#include "../Building/WoodworkingSystem.h"
#include "ColdSteelWeaponText.h"
#include "ColdSteelStaffModificationUI.h"
#include "../Combat/CombatItemFormula.h"
#include "ColdSteelStatusModel.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FullAutoTrigger.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Kukri/KukriEnchantment.h"
#include "../Production/RuneboundHammerTuning.h"
#include "../Production/ThunderHammerTuning.h"
#include "../Production/WarhammerCombat.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/RuneSwordRhythm.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../Weapons/RuneSwordGuardTuning.h"
#include "../Weapons/AzureDragonReach.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionToolEnhance.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/UnrealType.h"

#include "ColdSteelTooltipFormatPrivate.h"

namespace ColdSteelTooltipPrivate
{
TArray<FColdSteelTooltipRow> AppendCraftQuality(const FColdSteelItem& I,UColdSteelStatusModel* Model,const J& O,FColdSteelTooltipContent& Out)
{
    TArray<FColdSteelTooltipRow> ForgeSummary;
    if(const J Forge=Object(O,TEXT("_forgeQuality")))
    {
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("锻造工艺");C.MinimumWidth=300;
        Row(C,ColdSteelWeaponText::ForgeQuality,String(Forge,TEXT("label"),TEXT("—")));
        const double Multiplier=ColdSteelForgeQuality::Multiplier(I);
        const double Percent=(Multiplier-1)*100;
        Row(C,ColdSteelWeaponText::ForgeDamageModifier,Signed(Percent,TEXT("%")),Percent>0?1:Percent<0?-1:0);
        ForgeSummary=C.Rows;
        const bool MaterialRules=Number(Forge,TEXT("version"))>=ColdSteelForgeQuality::Version;
        if(MaterialRules)
        {
            Row(C,TEXT("投入金属"),String(Forge,TEXT("materialName"),TEXT("—")));
            Row(C,TEXT("材质保底"),Signed(Number(Forge,TEXT("materialBonus"))*100,TEXT("%")),1);
            Row(C,TEXT("命中提升"),FString::Printf(TEXT("+%.2f%% / %.0f%%"),
                ColdSteelForgeQuality::HitBonus(int32(Number(Forge,TEXT("hits"))))*100,ColdSteelForgeQuality::MaxHitBonus*100),1);
        }
        const bool FromSmith=Forge->HasField(TEXT("blacksmithPercent"));
        if(!FromSmith)Row(C,TEXT("有效命中"),N(Number(Forge,TEXT("hits")))+TEXT(" / ")+N(Number(Forge,TEXT("total"),20)));
        Row(C,TEXT("工艺倍率"),FString::Printf(TEXT("×%.4f"),Multiplier));
        Note(C,TEXT("作用"),TEXT("乘于基础伤害，已计入武器总伤害"));
        Note(C,TEXT("例外"),TEXT("附加伤害按各自公式结算，不乘此倍率"));
        Note(C,TEXT("说明"),FromSmith?TEXT("铁匠出售的成品，锻造品质介于 -25% 和 +5% 之间"):
            MaterialRules?TEXT("材质保底与命中提升相加，最高 +25%，与强化独立"):
            TEXT("旧版锻造成品，保留原工艺品质与伤害倍率"));
    }
    if(Model)
        if(const auto* ForgeSystem=Model->GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>())
            if(const auto* Metal=ForgeSystem->FindMetal(FName(*I.Definition)))
            {
                auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("金属材质");C.MinimumWidth=300;
                Row(C,TEXT("材质保底"),Signed(Metal->Bonus*100,TEXT("%")),Metal->Bonus>0?1:0);
                Note(C,TEXT("用途"),TEXT("用于铁匠锻造与枪械装配；加工表现另计，最高再加 15%"));
            }
    if(Model&&I.Definition.StartsWith(TEXT("wood_core_")))
        if(const auto* Wood=Model->GetGameInstance()->GetSubsystem<UWoodworkingSystem>())
            if(const auto* Core=Wood->FindCore(FName(*I.Definition)))
            {
                auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("木芯材质");C.MinimumWidth=300;
                Row(C,TEXT("材质保底"),Signed(Core->Bonus*100,TEXT("%")),Core->Bonus>0?1:0);
                ForgeSummary.Append(C.Rows);
                Note(C,TEXT("用途"),TEXT("木工制作每件投入 1 枚；弓提高物理伤害，法杖提高本件魔攻"));
                Note(C,TEXT("加工"),TEXT("合格成品保留材质加成，小游戏额外提供最高 +15%"));
            }
    double WoodScore=0;
    if(ColdSteelWoodQuality::Read(I,WoodScore))
    {
        const double Multiplier=ColdSteelWoodQuality::Multiplier(I,ColdSteelWoodQuality::Channel(I)),Percent=(Multiplier-1)*100;
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("木工工艺");C.MinimumWidth=300;
        Row(C,TEXT("工艺评分"),N(WoodScore)+TEXT(" / 100"));
        Row(C,ColdSteelWoodQuality::StatLabel(I),Signed(Percent,TEXT("%")),Percent>0?1:Percent<0?-1:0);
        ForgeSummary.Append(C.Rows);
        Row(C,TEXT("工艺倍率"),FString::Printf(TEXT("×%.3f"),Multiplier));
        Note(C,TEXT("作用"),ColdSteelWoodQuality::Channel(I)==ColdSteelWoodQuality::EChannel::Physical?
            TEXT("已计入本弓物理伤害；附加魔法伤害不受此修正影响"):
            TEXT("已计入本件法杖魔法攻击，参与法术伤害计算；挥杖物理伤害不受此修正影响"));
        if(ColdSteelWoodQuality::UsesMaterials(I))
        {
            const double Material=ColdSteelWoodQuality::MaterialBonus(I)*100,Skill=ColdSteelWoodQuality::SkillBonus(WoodScore)*100;
            Row(C,TEXT("木芯保底"),Signed(Material,TEXT("%")),Material>0?1:0);
            Row(C,TEXT("加工加成"),Signed(Skill,TEXT("%")),Skill>0?1:0);
            Note(C,TEXT("评分规则"),TEXT("木芯保底与加工加成相加，最高 +25%；加工满分 +15%"));
        }
        else Note(C,TEXT("评分规则"),TEXT("旧版工艺：50 分无修正，100 分 +25%，最低 -25%；保留原数值"));
    }
    if(const J Assembly=Object(O,TEXT("_assemblyQuality")))
    {
        auto& C=Out.Cards.AddDefaulted_GetRef();C.Title=TEXT("枪械装配工艺");C.MinimumWidth=300;
        Row(C,TEXT("装配品质"),String(Assembly,TEXT("label"),TEXT("—")));
        Row(C,TEXT("工艺评分"),N(Number(Assembly,TEXT("score")))+TEXT(" / 100"));
        const double Base=ColdSteelAssemblyQuality::MaterialBonus(I),Multiplier=ColdSteelAssemblyQuality::Multiplier(I);
        Row(C,TEXT("金属材质"),String(Assembly,TEXT("materialName"),TEXT("旧制枪械")));
        Row(C,TEXT("材质保底"),FString::Printf(TEXT("+%.2f%%"),Base*100),Base>0?1:0);
        Row(C,TEXT("装配提升"),FString::Printf(TEXT("+%.2f%%"),(Multiplier-1.-Base)*100),Multiplier>1.+Base?1:0);
        Row(C,TEXT("伤害加成"),FString::Printf(TEXT("+%.2f%%"),(Multiplier-1.)*100),Multiplier>1.?1:0);
        ForgeSummary.Append(C.Rows);
        Row(C,TEXT("工艺倍率"),FString::Printf(TEXT("×%.4f"),Multiplier));
        Note(C,TEXT("作用"),TEXT("与近战锻造相同，乘于基础伤害公式；已计入武器总伤害，附加伤害独立结算"));
        Note(C,TEXT("说明"),Number(Assembly,TEXT("version"))>=ColdSteelAssemblyQuality::Version?
            TEXT("材质最高 +10%，装配最高 +15%，合计最高 +25%；不再修正后坐力和散布"):
            TEXT("旧制枪械按已保存评分折算伤害；没有材质记录时保底为 0%"));
    }
    return ForgeSummary;
}
}
