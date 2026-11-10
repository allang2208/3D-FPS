#include "ColdSteelEnhancementWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelWeaponText.h"
#include "GunsmithUIStyle.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Production/ProductionToolStats.h"
#include "Engine/GameInstance.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

void UColdSteelEnhancementWidget::BuildStatComparison(const FColdSteelItem& Before,const FColdSteelItem& After)
{
    using namespace ColdSteelInventory;
    auto* P=Profile();auto* E=System();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    auto Comparison=Before;
    if(bCompareBase)
    {
        // Compare the same assembly, crafting quality and character, removing processing only.
        TSharedPtr<FJsonObject> Data;
        if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Comparison.Data),Data))
        {
            Data->SetNumberField(TEXT("enhanceLevel"),0);
            Data->RemoveField(TEXT("_enchantEffects"));
            FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Comparison.Data));
        }
    }
    auto Row=[&](const FString& Name,double Old,double Final,int32 Digits=2,bool LowerBetter=false,const TCHAR* Unit=TEXT(""))
    {
        const double Delta=Final-Old;
        const int32 Benefit=FMath::Abs(Delta)<.0001?0:((Delta>0)!=LowerBetter?1:-1);
        Inspector->AddSlot().AutoHeight().Padding(0,0,0,1)[TableRow(Name,
            FString::Printf(TEXT("%.*f%s"),Digits,Old,Unit),
            FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit),
            Benefit?FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit):TEXT("—"),Benefit)];
    };
    auto Note=[&](const FString& Text,FLinearColor Tone=ColdSteelUI::TextTertiary)
    {
        Inspector->AddSlot().AutoHeight().Padding(4,7)[SNew(STextBlock)
            .Text(FText::FromString(Text)).Font(GunsmithUI::TextFont(12))
            .ColorAndOpacity(Tone).AutoWrapText(true)];
    };
    auto Gain=[&](const TCHAR* Name,double Old,double Final)
    {
        const double Delta=Final-Old;
        if(FMath::Abs(Delta)<.0001)return;
        const FString Percent=FMath::Abs(Old)>.0001?
            FString::Printf(TEXT("（%+.2f%%）"),Delta/FMath::Abs(Old)*100.):FString();
        Note(FString::Printf(TEXT("%s %+.2f%s"),Name,Delta,*Percent),
            Delta>0?ColdSteelUI::Success:ColdSteelUI::Danger);
    };
    auto DamageRows=[&](const FWeaponDamageParts& Old,const FWeaponDamageParts& Final)
    {
        Gain(TEXT("武器总伤害"),Old.Total(),Final.Total());
        Row(ColdSteelWeaponText::TotalDamage,Old.Total(),Final.Total());
        Row(ColdSteelWeaponText::BasePhysical,Old.BasePhysical,Final.BasePhysical);
        if(Old.BaseMagic!=0||Final.BaseMagic!=0)Row(TEXT("基础魔法伤害"),Old.BaseMagic,Final.BaseMagic);
        if(Old.AddedPhysical!=0||Final.AddedPhysical!=0)Row(ColdSteelWeaponText::AddedPhysical,Old.AddedPhysical,Final.AddedPhysical);
        if(Old.AddedMagic!=0||Final.AddedMagic!=0)Row(ColdSteelWeaponText::AddedMagic,Old.AddedMagic,Final.AddedMagic);
    };
    Row(TEXT("强化等级"),Number(Comparison,TEXT("enhanceLevel")),Number(After,TEXT("enhanceLevel")),0);
    const bool Magic=Before.Definition==TEXT("ue_alchemy_spellbook")||Text(Before,TEXT("weaponType"))==TEXT("staff");
    const bool Tool=ColdSteelTool::Supports(Before);
    const bool Bow=IsBow(Before);
    const bool Melee=IsMeleeWeapon(Before)&&!Tool&&!Magic;
    if(Magic)
    {
        const double Old=P->ItemMagicAttack(Comparison),Final=P->ItemMagicAttack(After);
        Gain(ColdSteelWeaponText::EquipmentMagicAttack,Old,Final);
        Row(ColdSteelWeaponText::EquipmentMagicAttack,Old,Final);
        Note(TEXT("显示本件装备提供的魔攻，保留当前配件、品质和角色属性；不把某个法术的伤害当作装备魔攻。"));
    }
    else if(Tool)
    {
        const auto Old=ColdSteelTool::Evaluate(Comparison,P),Final=ColdSteelTool::Evaluate(After,P);
        DamageRows(Old.Damage,Final.Damage);
        Row(ColdSteelWeaponText::AttackInterval,Old.SwingSeconds,Final.SwingSeconds,2,true,TEXT("s"));
        Row(ColdSteelWeaponText::StaminaCost,Old.StaminaCost,Final.StaminaCost);
        Row(ColdSteelWeaponText::AttackDistance,Old.CombatReachCM/100.,Final.CombatReachCM/100.,2,false,TEXT("m"));
        if(IsTwoHandedBlunt(Before))
            Row(TEXT("重击蓄力时间"),Old.HeavyChargeSeconds,Final.HeavyChargeSeconds,2,true,TEXT("s"));
        Note(IsTwoHandedBlunt(Before)?TEXT("按当前角色与锤类普通攻击计算，未计暴击、重击倍率和目标防御。"):
            TEXT("按本件工具的实际伤害与挥击节奏计算，保留当前改造与采集属性。"));
    }
    else if(Melee)
    {
        const auto Old=ColdSteelMelee::Evaluate(Comparison,P),Final=ColdSteelMelee::Evaluate(After,P);
        DamageRows(Old.DamageParts,Final.DamageParts);
        Row(ColdSteelWeaponText::AttackInterval,Old.AttackSeconds,Final.AttackSeconds,2,true,TEXT("s"));
        Row(ColdSteelWeaponText::StaminaCost,Old.AttackStamina,Final.AttackStamina);
        Row(ColdSteelWeaponText::AttackDistance,Old.SlashReach/100.,Final.SlashReach/100.,2,false,TEXT("m"));
        Row(TEXT("重击蓄力时间"),Old.HeavyChargeSeconds,Final.HeavyChargeSeconds,2,true,TEXT("s"));
        Note(TEXT("按当前角色、配件与普通攻击计算；未计连段、重击、暴击和目标防御。"));
    }
    else if(Bow)
    {
        const auto Old=ColdSteelBow::Evaluate(Comparison,P),Final=ColdSteelBow::Evaluate(After,P);
        DamageRows(Old.Damage,Final.Damage);
        Row(ColdSteelWeaponText::DrawTime,Old.Draw,Final.Draw,2,true,TEXT("s"));
        Row(ColdSteelWeaponText::NockTime,Old.Nock,Final.Nock,2,true,TEXT("s"));
        Row(ColdSteelWeaponText::StaminaCost,Old.Stamina,Final.Stamina);
        Row(ColdSteelWeaponText::EffectiveRange,Old.Range,Final.Range,1,false,TEXT("m"));
        Note(TEXT("按当前角色与改造后的满弓单箭计算，已含满弓倍率；未计箭种、穿心箭、暴击和目标防御。"));
    }
    else if(G->Weapon(Before.Definition))
    {
        const auto Old=G->CalculateItem(Comparison,G->Installed(Comparison));
        const auto Final=G->CalculateItem(After,G->Installed(After));
        DamageRows(ColdSteelWeaponStats::DamageParts(Comparison,P,Old.Damage),
            ColdSteelWeaponStats::DamageParts(After,P,Final.Damage));
        Row(ColdSteelWeaponText::AttackInterval,ColdSteelWeaponStats::Interval(&Comparison,P,Old.Interval)*1000.,
            ColdSteelWeaponStats::Interval(&After,P,Final.Interval)*1000.,0,true,TEXT("ms"));
        Row(ColdSteelWeaponText::Reload,ColdSteelWeaponStats::Reload(&Comparison,P,Old.Reload),
            ColdSteelWeaponStats::Reload(&After,P,Final.Reload),2,true,TEXT("s"));
        Row(ColdSteelWeaponText::EmptyReload,ColdSteelWeaponStats::Reload(&Comparison,P,Old.EmptyReload),
            ColdSteelWeaponStats::Reload(&After,P,Final.EmptyReload),2,true,TEXT("s"));
        Row(ColdSteelWeaponText::Capacity,Old.Capacity,Final.Capacity,0);
        Note(TEXT("按当前角色与枪械配件计算，未计弹药倍率、暴击、距离衰减和目标防御。"));
    }
    else
    {
        const double Old=E->Defense(Comparison),Final=E->Defense(After);
        Gain(TEXT("物理防御"),Old,Final);
        Row(TEXT("物理防御"),Old,Final,0);
        const double OldMagic=E->MagicDefense(Comparison),FinalMagic=E->MagicDefense(After);
        if(OldMagic!=0||FinalMagic!=0)Row(TEXT("魔法防御"),OldMagic,FinalMagic,0);
    }
    // Only relevant affix effects occupy rows. An enhancement-only preview no longer
    // starts with a wall of unrelated zero-valued enchantment statistics.
    auto Affix=[&](const TCHAR* Name,const TCHAR* Key,double Scale=1.,int32 Digits=0,const TCHAR* Unit=TEXT(""))
    {
        const double Old=E->Effect(Comparison,Key)*Scale,Final=E->Effect(After,Key)*Scale;
        if(Old!=0||Final!=0)Row(Name,Old,Final,Digits,false,Unit);
    };
    Affix(TEXT("附魔伤害"),TEXT("damagePercent"),100.,1,TEXT("%"));
    Affix(TEXT("附魔物理伤害"),TEXT("bloodWolfPhysicalBonus"),100.,1,TEXT("%"));
    const double OldCrit=E->Effect(Comparison,TEXT("critRate"))*100.+E->Effect(Comparison,TEXT("frostHawkCriticalChanceAdd"));
    const double FinalCrit=E->Effect(After,TEXT("critRate"))*100.+E->Effect(After,TEXT("frostHawkCriticalChanceAdd"));
    if(OldCrit!=0||FinalCrit!=0)Row(TEXT("附魔暴击率"),OldCrit,FinalCrit,1,false,TEXT("%"));
    Affix(TEXT("附魔力量"),TEXT("str"));
    Affix(TEXT("附魔精神"),TEXT("wis"));
    Affix(TEXT("拉弓速度加成"),TEXT("bowDrawSpeedBonus"),100.,1,TEXT("%"));
    Affix(TEXT("重击蓄力加成"),TEXT("heavyChargeSpeedBonus"),100.,1,TEXT("%"));
    Affix(TEXT("额外穿透目标"),TEXT("piercingBonus"));
    Affix(TEXT("命中叠毒层数"),TEXT("poisonStacks"));
}
