#include "M4GunsmithWidget.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

bool UM4GunsmithWidget::IsCategoryAvailable(const FString& SlotKey) const
{
    const auto* Weapon = Model()->ModifiableWeapon(Model()->Definition());
    const auto* Options = Weapon ? Weapon->Options.Find(SlotKey) : nullptr;
    return Weapon && Weapon->Allowed.Contains(SlotKey) && Options &&
        (IsMeleeWorkbench()?!Options->IsEmpty():Options->ContainsByPredicate([](const FGunsmithOption& Option){return Option.Id != TEXT("false");}));
}

float UM4GunsmithWidget::SelectedDetailsWidth() const
{
    const float Actual = InspectorScroll ? InspectorScroll->GetCachedGeometry().GetLocalSize().X : 0.f;
    return FMath::Max(120.f,(Actual > 100.f ? Actual : InspectorWidth - 28.f) - 12.f);
}

float UM4GunsmithWidget::OverviewSectionHeight() const
{
    const float Available = InspectorScroll ? InspectorScroll->GetCachedGeometry().GetLocalSize().Y : 0.f;
    const float Details = ModificationList ? FMath::Max(280.f,float(ModificationList->GetDesiredSize().Y)) : 280.f;
    // Give the complete weapon table its natural height, including the title,
    // comparison buttons, column header and legend. The outer inspector scrolls.
    const float Table = OverviewList ? float(OverviewList->GetDesiredSize().Y) : 0.f;
    return FMath::Max3(540.f,Table+144.f,(Available > 100.f ? Available : 820.f)-Details-56.f);
}

void UM4GunsmithWidget::RefreshSelectedOption()
{
    if (!ModificationList) return;
    auto* Gunsmith = Model();
    FString Id = Gunsmith->Draft().FindRef(SelectedCategory);
    if (Id.IsEmpty()) Id = TEXT("false");
    const auto* Option = Gunsmith->Option(Gunsmith->Definition(),SelectedCategory,Id);
    const FString Key = Gunsmith->Definition() + TEXT("|") + SelectedCategory + TEXT("|") + Id;
    if (InspectedOptionKey != Key)
    {
        InspectedOptionKey = Key;
        if (InspectorScroll) InspectorScroll->ScrollToStart();
    }
    ModificationList->ClearChildren();
    auto Paragraph = [this](const FString& Caption,int32 Pixels,FLinearColor Color,bool Medium=false)
    {
        return SNew(STextBlock).Text(FText::FromString(Caption)).Font(GunsmithUI::TextFont(Pixels,Medium))
            .ColorAndOpacity(Color).WrapTextAt_Lambda([this](){return SelectedDetailsWidth();});
    };
    if (!Option)
    {
        ModificationList->AddSlot().AutoHeight()[Paragraph(TEXT("当前武器没有可选改造项目。"),14,GunsmithUI::Secondary)];
        return;
    }
    const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item = Profile->FindItem(Gunsmith->Instance());
    FString Installed = Item ? Gunsmith->Installed(*Item).FindRef(SelectedCategory) : FString();
    if (Installed.IsEmpty()) Installed = TEXT("false");
    ModificationList->AddSlot().AutoHeight()[Paragraph(Option->Name,16,GunsmithUI::Text,true)];
    ModificationList->AddSlot().AutoHeight().Padding(0,5,0,12)
        [Paragraph(Installed==Id?(Id==TEXT("false")?TEXT("当前原厂配置"):TEXT("已安装")):TEXT("已选 · 待应用"),12,
            Id==TEXT("false")?GunsmithUI::Muted:ColdSteelUI::Success)];
    if(Item&&IsMeleeWorkbench())
    {
        const FString Appearance=ColdSteelModularSword::Appearance(*Item,SelectedCategory,Id);
        if(!Appearance.IsEmpty())ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
            [Paragraph(Appearance,12,GunsmithUI::Secondary)];
    }

    auto WithoutPart = Gunsmith->Draft();
    WithoutPart.Remove(SelectedCategory);
    const auto Before = Gunsmith->Calculate(Gunsmith->Definition(),WithoutPart);
    const auto After = Gunsmith->Calculate(Gunsmith->Definition(),Gunsmith->Draft());
    int32 RowCount = 0;
    // The card keeps only the basic description, so every numeric change belongs
    // here and is derived from the catalog multipliers - never hand written.
    // The percent reads exactly like the catalog field: minus is faster (green),
    // plus is slower (red), and the value equals ads_percent.
    auto AddValue = [&](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false,double Percent=0.)
    {
        const double Delta = Final-Base;
        if (FMath::Abs(Delta) < .00001) return;
        const FString PercentText=FMath::IsNearlyZero(Percent,.01)?FString():FString::Printf(TEXT("（%+.0f%%）"),Percent);
        if (RowCount++ == 0)
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("当前组合实值 · 差值相对该栏原厂配置"),12,GunsmithUI::Muted)];
        const auto Color = ((Delta>0)!=Lower) ? ColdSteelUI::Success : ColdSteelUI::Danger;
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,4)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(8,6)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(0,0,10,0)
                    [SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(Name)).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(GunsmithUI::Secondary)
                            .WrapTextAt_Lambda([this](){return (SelectedDetailsWidth()-26.f)*.5f;})]
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4,0,0,0)
                        [SNew(STextBlock).Text(FText::FromString(PercentText)).Font(GunsmithUI::NumberFont(13)).ColorAndOpacity(Color)]]
                    +SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit)))
                            .Font(GunsmithUI::NumberFont(14)).ColorAndOpacity(GunsmithUI::Text).Justification(ETextJustify::Right)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)
                        [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit)))
                            .Font(GunsmithUI::NumberFont(12)).ColorAndOpacity(Color).Justification(ETextJustify::Right)]]]];
    };
    if(!IsMeleeWorkbench())
    {
    // Every row reports its own ratio, so stacked accessories stay truthful; the
    // ADS row reports the catalog's 开镜耗时 percent unchanged.
    auto Ratio=[&](double Was,double Now){return Was>.00001?(Now/Was-1.)*100.:0.;};
    AddValue(TEXT("开镜耗时"),Before.ADS*1000,After.ADS*1000,0,TEXT(" ms"),true,Option->ADS*100.);
    AddValue(TEXT("弹匣容量"),Before.Capacity,After.Capacity,0,TEXT(" 发"));
    // Shared reload stack (敏捷 × 快手 × 附魔 × 配件); the ratio stays the attachment's own effect.
    AddValue(TEXT("普通换弹"),ColdSteelWeaponStats::Reload(Item,Profile,Before.Reload),ColdSteelWeaponStats::Reload(Item,Profile,After.Reload),2,TEXT(" s"),true,Ratio(Before.Reload,After.Reload));
    AddValue(TEXT("空仓换弹"),ColdSteelWeaponStats::Reload(Item,Profile,Before.EmptyReload),ColdSteelWeaponStats::Reload(Item,Profile,After.EmptyReload),2,TEXT(" s"),true,Ratio(Before.EmptyReload,After.EmptyReload));
    // Catalog interval, undivided by the character's melee attack rate.
    AddValue(TEXT("射击间隔"),Before.Interval*1000,After.Interval*1000,0,TEXT(" ms"),true,Ratio(Before.Interval,After.Interval));
    AddValue(TEXT("后坐力指数"),Before.Recoil,After.Recoil,1,TEXT(""),true,Ratio(Before.Recoil,After.Recoil));
    AddValue(TEXT("枪械稳定性"),Before.Handling.Stability,After.Handling.Stability,1,TEXT(" 分"),false,Ratio(Before.Handling.Stability,After.Handling.Stability));
    if(!FMath::IsNearlyEqual(Option->Shake,1.0))AddValue(TEXT("开火抖动指数"),Before.Shake,After.Shake,1,TEXT(""),true,Ratio(Before.Shake,After.Shake));
    AddValue(TEXT("腰射散布系数"),Before.Spread,After.Spread,2,TEXT("×"),true,Ratio(Before.Spread,After.Spread));
    AddValue(TEXT("有效射程"),Before.Range,After.Range,0,TEXT(" m"),false,Ratio(Before.Range,After.Range));
    AddValue(TEXT("子弹速度"),Before.Speed,After.Speed,0,TEXT(" m/s"),false,Ratio(Before.Speed,After.Speed));
    }
    else if(Item)
    {
        const auto Was=ColdSteelMelee::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelMelee::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const auto& M=Option->Melee;
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        AddValue(TEXT("普通攻击总伤害"),Was.Damage,Now.Damage,2,TEXT(""));
        AddValue(TEXT("基础物理伤害"),Was.DamageParts.BasePhysical,Now.DamageParts.BasePhysical,2,TEXT(""),false,Percent(M.Damage));
        AddValue(TEXT("附加物理伤害"),Was.DamageParts.AddedPhysical,Now.DamageParts.AddedPhysical,2,TEXT(""));
        AddValue(TEXT("附加魔法伤害"),Was.DamageParts.AddedMagic,Now.DamageParts.AddedMagic,2,TEXT(""));
        AddValue(TEXT("第二段横斩伤害"),Was.ComboSecondDamage,Now.ComboSecondDamage,2,TEXT(""),false,Percent(M.ComboSecond));
        AddValue(TEXT("第三段突刺伤害"),Was.ComboThirdDamage,Now.ComboThirdDamage,2,TEXT(""),false,Percent(M.ComboThird));
        AddValue(TEXT("攻击速度倍率"),Was.AttackRate,Now.AttackRate,2,TEXT("×"),false,Percent(M.AttackSpeed));
        AddValue(TEXT("普通攻击耗时"),Was.AttackSeconds,Now.AttackSeconds,2,TEXT(" s"),true);
        AddValue(TEXT("突刺耗时"),Was.ThrustSeconds,Now.ThrustSeconds,2,TEXT(" s"),true);
        AddValue(TEXT("普通挥砍距离"),Was.SlashReach/100,Now.SlashReach/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(TEXT("最大攻击距离（含突刺）"),Was.ThrustReach/100,Now.ThrustReach/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(TEXT("攻击耐力消耗（含重击）"),Was.AttackStamina,Now.AttackStamina,2,TEXT(""),true,Percent(M.Stamina));
        AddValue(TEXT("防御受击耐力消耗"),Was.BlockStamina,Now.BlockStamina,2,TEXT(""),true,Percent(M.BlockStamina));
        AddValue(TEXT("格挡伤害减免"),Was.BlockReduction*100,Now.BlockReduction*100,1,TEXT("%"),false,Percent(M.BlockReduction));
        AddValue(TEXT("命中硬直时间倍率"),Was.Modifiers.HitReaction,Now.Modifiers.HitReaction,2,TEXT("×"),false,Percent(M.HitReaction));
        AddValue(TEXT("韧性伤害倍率"),Was.Modifiers.ToughnessDamage,Now.Modifiers.ToughnessDamage,2,TEXT("×"),false,Percent(M.ToughnessDamage));
        AddValue(TEXT("改造物理防御穿透"),Was.Modifiers.PhysicalArmorPenetration*100,Now.Modifiers.PhysicalArmorPenetration*100,0,TEXT("%"));
        AddValue(TEXT("重击伤害倍率"),Was.HeavyMultiplier,Now.HeavyMultiplier,2,TEXT("×"));
        AddValue(TEXT("重击总伤害"),Was.Damage*Was.HeavyMultiplier,Now.Damage*Now.HeavyMultiplier,2,TEXT(""));
        AddValue(TEXT("攻击击退距离"),Was.KnockbackCM,Now.KnockbackCM,1,TEXT(" cm"),false,Percent(M.Knockback));
        AddValue(TEXT("快速近战伤害倍率"),Was.QuickCombat.DamageMultiplier,Now.QuickCombat.DamageMultiplier,2,TEXT("×"));
        AddValue(TEXT("快速近战伤害"),Was.QuickCombat.Damage,Now.QuickCombat.Damage,2,TEXT(""));
        AddValue(TEXT("快速近战击退距离"),Was.QuickCombat.KnockbackCM,Now.QuickCombat.KnockbackCM,1,TEXT(" cm"),false,Percent(M.QuickCombatKnockback));
        AddValue(TEXT("魔法技能冷却倍率"),Was.Modifiers.MagicCooldown,Now.Modifiers.MagicCooldown,2,TEXT("×"),true,Percent(M.MagicCooldown));
        AddValue(TEXT("魔法值消耗倍率"),Was.Modifiers.MagicCost,Now.Modifiers.MagicCost,2,TEXT("×"),true,Percent(M.MagicCost));
        AddValue(TEXT("魔法伤害倍率"),Was.Modifiers.MagicDamage,Now.Modifiers.MagicDamage,2,TEXT("×"),false,Percent(M.MagicDamage));
        AddValue(TEXT("命中施加魔法易伤"),Was.Modifiers.RuneVulnerability*100,Now.Modifiers.RuneVulnerability*100,0,TEXT("%"));
        AddValue(TEXT("魔法易伤持续时间"),Was.Modifiers.RuneVulnerabilitySeconds,Now.Modifiers.RuneVulnerabilitySeconds,1,TEXT(" s"));
        AddValue(TEXT("弹反判定时间"),Was.ParrySeconds,Now.ParrySeconds,2,TEXT(" s"),false,Percent(M.ParryWindow));
        AddValue(TEXT("反击激励攻速倍率"),Was.Modifiers.RiposteSpeed,Now.Modifiers.RiposteSpeed,2,TEXT("×"),false,Percent(M.RiposteSpeed));
        AddValue(TEXT("反击激励耐力倍率"),Was.Modifiers.RiposteStamina,Now.Modifiers.RiposteStamina,2,TEXT("×"),true,Percent(M.RiposteStamina));
        AddValue(TEXT("反击激励持续时间"),Was.Modifiers.RiposteSeconds,Now.Modifiers.RiposteSeconds,1,TEXT(" s"));
        AddValue(TEXT("承锋·瞬重斩保留时间"),Was.Modifiers.ClovenSeconds,Now.Modifiers.ClovenSeconds,1,TEXT(" s"));
        AddValue(TEXT("承锋重击物理伤害加成"),Percent(Was.Modifiers.ClovenPhysical),Percent(Now.Modifiers.ClovenPhysical),0,TEXT("%"));
        AddValue(TEXT("承锋重击韧性伤害加成"),Percent(Was.Modifiers.ClovenToughness),Percent(Now.Modifiers.ClovenToughness),0,TEXT("%"));
        if(M.ClovenSeconds>0)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("成功弹反后，下一次普攻直接释放重击，无需蓄力。按重击消耗体力，发起即消耗强化，挥空也消耗；最多保留一次，再次弹反刷新时间。突刺与技能不消耗强化。"),12,GunsmithUI::Muted)];
        if(!FMath::IsNearlyEqual(M.Range,1.))ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("范围改造影响挥砍与突刺；快速近战使用技能自身的判定范围。"),12,GunsmithUI::Muted)];
    }
    if (RowCount == 0)
    {
        if (Option->Effects.IsEmpty())
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("无额外数值修正"),14,GunsmithUI::Secondary)];
        else for (const auto& Effect : Option->Effects)
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,6)
                [Paragraph(Effect.Key,14,Effect.Value>0?ColdSteelUI::Success:Effect.Value<0?ColdSteelUI::Danger:GunsmithUI::Secondary)];
    }
    ModificationList->AddSlot().AutoHeight().Padding(0,10,0,6)[Paragraph(TEXT("配件说明"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight()
        [Paragraph(Option->Description.IsEmpty()?TEXT("暂无额外说明。"):Option->Description,14,GunsmithUI::Secondary)];
}
