#include "ColdSteelWeaponText.h"
#include "M4GunsmithWidget.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelStaffModificationUI.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionToolEnhance.h"
#include "../Production/ProductionTreeHealth.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

bool UM4GunsmithWidget::IsCategoryAvailable(const FString& SlotKey) const
{
    // 第五栏「强化」不是改造槽：它不在 Weapon->Allowed／Options 里，来源是等级阶梯目录。
    // 只有工具工作台认它，且目录必须有等级条目（0 项＝Rail 隐藏该项）。
    if(SlotKey==TEXT("enhance"))return IsToolWorkbench()&&!ColdSteelToolEnhance::Levels().IsEmpty();
    const auto* Weapon = Model()->ModifiableWeapon(Model()->Definition());
    const auto* Options = Weapon ? Weapon->Options.Find(SlotKey) : nullptr;
    return Weapon && Weapon->Allowed.Contains(SlotKey) && Options &&
        (IsStandaloneWorkbench()?!Options->IsEmpty():Options->ContainsByPredicate([](const FGunsmithOption& Option){return Option.Id != TEXT("false");}));
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
    const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item = Profile->FindItem(Gunsmith->Instance());
    if (!Option)
    {
        // 第五栏「强化」不是改造槽，Option 必然为空：走档位详情，而不是「没有可选改造项目」。
        // 等级阶梯目录缺失（0 项）时明确提示不可用。
        if(SelectedCategory==TEXT("enhance")&&IsToolWorkbench())
        {
            if(ColdSteelToolEnhance::Levels().IsEmpty())
                ModificationList->AddSlot().AutoHeight()[Paragraph(TEXT("强化工具目录不可用"),14,GunsmithUI::Secondary)];
            else
            {
                const int32 Current=Item?ColdSteelToolEnhance::Level(*Item):1;
                int32 Next=0;
                const bool bHasNext=Item&&ColdSteelToolEnhance::CanEnhance(*Item,Next);
                // 未选择档位时展示当前档；选了草稿就展示草稿档。
                AppendEnhanceDetails(Model()->DraftEnhanceLevel()>0?Model()->DraftEnhanceLevel():Current);
                if(!bHasNext)ModificationList->AddSlot().AutoHeight().Padding(0,8,0,0)
                    [Paragraph(TEXT("已达最高强化档位"),14,GunsmithUI::Secondary)];
            }
            return;
        }
        ModificationList->AddSlot().AutoHeight()[Paragraph(TEXT("当前武器没有可选改造项目。"),14,GunsmithUI::Secondary)];
        return;
    }
    FString Installed = Item ? Gunsmith->Installed(*Item).FindRef(SelectedCategory) : FString();
    if (Installed.IsEmpty()) Installed = TEXT("false");
    ModificationList->AddSlot().AutoHeight()[Paragraph(Option->Name,16,GunsmithUI::Text,true)];
    ModificationList->AddSlot().AutoHeight().Padding(0,5,0,12)
        [Paragraph(Installed==Id?(Id==TEXT("false")?TEXT("当前原厂配置"):TEXT("已安装")):TEXT("已选 · 待应用"),12,
            Id==TEXT("false")?GunsmithUI::Muted:ColdSteelUI::Success)];
    if(IsToolWorkbench()||IsBowWorkbench()||IsStaffWorkbench())
    {
        // 数值改造先行：外观归属如实写在目录的 appearance 字段里。
        if(!Option->Appearance.IsEmpty())ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
            [Paragraph(Option->Appearance,12,GunsmithUI::Secondary)];
    }
    else if(Item&&IsMeleeWorkbench())
    {
        const FString Appearance=ColdSteelModularSword::Appearance(*Item,SelectedCategory,Id);
        if(!Appearance.IsEmpty())ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
            [Paragraph(Appearance,12,GunsmithUI::Secondary)];
    }

    auto WithoutPart = Gunsmith->Draft();
    if(Gunsmith->Definition()==TEXT("ue_rsh12")&&SelectedCategory==TEXT("underbarrel")&&Id!=TEXT("false"))
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
            [Paragraph(Item&&Gunsmith->HasUnsupportedForegrip(*Item)
                ?TEXT("当前双持：前握把增益不生效，减益仍生效；保留单手握姿。")
                :TEXT("单持使用前握把支撑；双持时仅保留前握把的减益。"),12,GunsmithUI::Secondary)];
    WithoutPart.Remove(SelectedCategory);
    const auto Before = Item?Gunsmith->CalculateItem(*Item,WithoutPart):Gunsmith->Calculate(Gunsmith->Definition(),WithoutPart);
    const auto After = Item?Gunsmith->CalculateItem(*Item,Gunsmith->Draft()):Gunsmith->Calculate(Gunsmith->Definition(),Gunsmith->Draft());
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
    if(IsStaffWorkbench()&&Item)
    {
        const auto Was=ColdSteelStaff::Resolve(*Item,&WithoutPart),Now=ColdSteelStaff::Resolve(*Item,&Gunsmith->Draft());
        auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        for(const auto& Field:ColdSteelStaffUI::Fields)
        {
            const double BeforeValue=E->CraftEffect(Was,Field.Key)*Field.Scale,AfterValue=E->CraftEffect(Now,Field.Key)*Field.Scale;
            AddValue(Field.Label,BeforeValue,AfterValue,Field.Digits,Field.Unit,
                ColdSteelStaffUI::LowerBetter(Field,BeforeValue,AfterValue));
        }
        if(SelectedCategory==TEXT("crown"))
        {
            const auto Crown=ColdSteelStaffUI::Crown(Gunsmith->Draft());
            if(Crown.bInstalled)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,8)
                [Paragraph(TEXT("杖冠状态：")+Crown.Text,12,Crown.bActive?ColdSteelUI::Success:ColdSteelUI::Warning)];
        }
    }
    else if(IsBowWorkbench()&&Item)
    {
        const auto Was=ColdSteelBow::Evaluate(*Item,Profile,&WithoutPart),Now=ColdSteelBow::Evaluate(*Item,Profile,&Gunsmith->Draft());
        AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage.Total(),Now.Damage.Total(),2,TEXT(""));
        AddValue(ColdSteelWeaponText::DrawTime,Was.Draw,Now.Draw,2,TEXT(" s"),true);
        AddValue(TEXT("拉弓速度加成"),Was.DrawSpeedBonus*100.,Now.DrawSpeedBonus*100.,1,TEXT("%"));
        AddValue(ColdSteelWeaponText::NockTime,Was.Nock,Now.Nock,2,TEXT(" s"),true);
        AddValue(ColdSteelWeaponText::ProjectileSpeed,Was.Speed,Now.Speed,1,TEXT(" m/s"));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.Stamina,Now.Stamina,2,TEXT(""),true);
        AddValue(ColdSteelWeaponText::HoldTime,Was.Hold,Now.Hold,2,TEXT(" s"));
        AddValue(ColdSteelWeaponText::Sway,Was.Sway,Now.Sway,2,TEXT(""),true);
        AddValue(ColdSteelWeaponText::HipSpreadAngle,FMath::RadiansToDegrees(FMath::Atan(Was.Spread)),FMath::RadiansToDegrees(FMath::Atan(Now.Spread)),2,TEXT("°"),true);
        AddValue(ColdSteelWeaponText::ADS,Was.ADS*1000,Now.ADS*1000,0,TEXT(" ms"),true);
        ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)[Paragraph(ColdSteelWeaponText::BowScope,12,GunsmithUI::Muted)];
    }
    else if(IsToolWorkbench()&&Item)
    {
        // 工具四栏：采集与自卫两条链路读同一份评估，行名与目录 effects 措辞一致。
        const auto Was=ColdSteelTool::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelTool::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const auto& T=Option->Tool;
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        AddValue(TEXT("采集产出倍率"),Was.HarvestYield,Now.HarvestYield,2,TEXT("×"),false,Percent(T.HarvestYield));
        AddValue(TEXT("采集伤害"),ProductionTreeHealth::StrikeDamage(Was),
            ProductionTreeHealth::StrikeDamage(Now),1,TEXT(" / 挥"));
        AddValue(TEXT("采集距离"),Was.HarvestReachCM/100,Now.HarvestReachCM/100,2,TEXT(" m"),false,Percent(T.HarvestReach));
        AddValue(TEXT("命中宽容半径"),Was.HarvestRadiusCM,Now.HarvestRadiusCM,0,TEXT(" cm"));
        AddValue(TEXT("额外产出几率"),Was.BonusHarvestChance*100,Now.BonusHarvestChance*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.StaminaCost,Now.StaminaCost,2,TEXT(""),true,Percent(T.Stamina));
        AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage.Total(),Now.Damage.Total(),2,TEXT(""));
        AddValue(ColdSteelWeaponText::BasePhysical,Was.Damage.BasePhysical,Now.Damage.BasePhysical,2,TEXT(""),false,Percent(T.Damage));
        AddValue(ColdSteelWeaponText::AddedPhysical,Was.Damage.AddedPhysical,Now.Damage.AddedPhysical,2,TEXT(""));
        AddValue(ColdSteelWeaponText::AddedMagic,Was.Damage.AddedMagic,Now.Damage.AddedMagic,2,TEXT(""));
        AddValue(TEXT("暴击率"),Was.CriticalChanceAdd,Now.CriticalChanceAdd,0,TEXT("%"));
        AddValue(TEXT("韧性伤害倍率"),Was.ToughnessDamage,Now.ToughnessDamage,2,TEXT("×"),false,Percent(T.ToughnessDamage));
        AddValue(ColdSteelWeaponText::AttackSpeedMultiplier,Was.Modifiers.AttackSpeed,Now.Modifiers.AttackSpeed,2,TEXT("×"),false,Percent(T.AttackSpeed));
        AddValue(ColdSteelWeaponText::AttackInterval,Was.SwingSeconds*1000,Now.SwingSeconds*1000,0,TEXT(" ms"),true);
        AddValue(TEXT("接触时刻"),Was.ContactSeconds,Now.ContactSeconds,2,TEXT(" s"),true);
        AddValue(ColdSteelWeaponText::AttackDistance,Was.CombatReachCM/100,Now.CombatReachCM/100,2,TEXT(" m"),false,Percent(T.CombatReach));
        ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("战斗与采集使用各自的数值行。树木与岩块均按采集伤害扣减生命值，归零后采尽；楔紧件提高采集伤害，不固定减少一次命中。"),12,GunsmithUI::Muted)];
    }
    else if(!IsMeleeWorkbench()&&!IsStaffWorkbench())
    {
    // Every row reports its own ratio, so stacked accessories stay truthful; the
    // ADS row reports the catalog's 开镜耗时 percent unchanged.
    auto Ratio=[&](double Was,double Now){return Was>.00001?(Now/Was-1.)*100.:0.;};
    AddValue(ColdSteelWeaponText::ADS,Before.ADS*1000,After.ADS*1000,0,TEXT(" ms"),true,Option->ADS*100.);
    if(!FMath::IsNearlyZero(Before.EquipSpeedBonus)||!FMath::IsNearlyZero(After.EquipSpeedBonus))
        AddValue(ColdSteelWeaponText::EquipSpeedBonus,Before.EquipSpeedBonus*100.,After.EquipSpeedBonus*100.,0,TEXT("%"),false,Option->EquipSpeedBonus*100.);
    AddValue(ColdSteelWeaponText::Capacity,Before.Capacity,After.Capacity,0,TEXT(" 发"));
    // Shared reload stack (敏捷 × 快手 × 附魔 × 配件); the ratio stays the attachment's own effect.
    AddValue(ColdSteelWeaponText::Reload,ColdSteelWeaponStats::Reload(Item,Profile,Before.Reload),ColdSteelWeaponStats::Reload(Item,Profile,After.Reload),2,TEXT(" s"),true,Ratio(Before.Reload,After.Reload));
    AddValue(ColdSteelWeaponText::EmptyReload,ColdSteelWeaponStats::Reload(Item,Profile,Before.EmptyReload),ColdSteelWeaponStats::Reload(Item,Profile,After.EmptyReload),2,TEXT(" s"),true,Ratio(Before.EmptyReload,After.EmptyReload));
    const double BeforeInterval=ColdSteelWeaponStats::Interval(Item,Profile,Before.Interval);
    const double AfterInterval=ColdSteelWeaponStats::Interval(Item,Profile,After.Interval);
    AddValue(After.BurstCount>1?TEXT("组内射击间隔"):TEXT("射击间隔"),BeforeInterval*1000,AfterInterval*1000,0,TEXT(" ms"),true,Ratio(Before.Interval,After.Interval));
    if(After.BurstCount>1)
    {
        const double BeforeDelay=ColdSteelWeaponStats::Interval(Item,Profile,Before.BurstDelay);
        const double AfterDelay=ColdSteelWeaponStats::Interval(Item,Profile,After.BurstDelay);
        AddValue(TEXT("连发组末发后间隔"),BeforeDelay*1000,AfterDelay*1000,0,TEXT(" ms"),true,Ratio(Before.BurstDelay,After.BurstDelay));
        AddValue(TEXT("含组间隔理论射速"),60*Before.BurstCount/((Before.BurstCount-1)*BeforeInterval+FMath::Max(BeforeInterval,BeforeDelay)),60*After.BurstCount/((After.BurstCount-1)*AfterInterval+FMath::Max(AfterInterval,AfterDelay)),0,TEXT(" /min"));
    }
    AddValue(ColdSteelWeaponText::RecoilIndex,Before.Recoil,After.Recoil,1,TEXT(""),true,Ratio(Before.Recoil,After.Recoil));
    AddValue(ColdSteelWeaponText::Stability,Before.Handling.Stability,After.Handling.Stability,1,TEXT(" /100"),false,Ratio(Before.Handling.Stability,After.Handling.Stability));
    if(!FMath::IsNearlyEqual(Option->Shake,1.0))AddValue(TEXT("开火抖动指数"),Before.Shake,After.Shake,1,TEXT(""),true,Ratio(Before.Shake,After.Shake));
    AddValue(ColdSteelWeaponText::HipSpreadMultiplier,Before.Spread,After.Spread,2,TEXT("×"),true,Ratio(Before.Spread,After.Spread));
    AddValue(ColdSteelWeaponText::EffectiveRange,Before.Range,After.Range,0,TEXT(" m"),false,Ratio(Before.Range,After.Range));
    AddValue(ColdSteelWeaponText::ProjectileSpeed,Before.Speed,After.Speed,0,TEXT(" m/s"),false,Ratio(Before.Speed,After.Speed));
    }
    else if(Item)
    {
        const auto Was=ColdSteelMelee::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelMelee::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(*Item,&Gunsmith->Draft());
        const bool RisingDragon=ColdSteelModularSword::UsesRisingDragonFinisher(*Item,&Gunsmith->Draft());
        const auto& M=Option->Melee;
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage,Now.Damage,2,TEXT(""));
        AddValue(ColdSteelWeaponText::BasePhysical,Was.DamageParts.BasePhysical,Now.DamageParts.BasePhysical,2,TEXT(""),false,Percent(M.Damage*M.AllAttackDamage));
        AddValue(TEXT("全部近战攻击伤害倍率"),Was.Modifiers.AllAttackDamage,Now.Modifiers.AllAttackDamage,2,TEXT("×"),false,Percent(M.AllAttackDamage));
        AddValue(ColdSteelWeaponText::AddedPhysical,Was.DamageParts.AddedPhysical,Now.DamageParts.AddedPhysical,2,TEXT(""));
        AddValue(ColdSteelWeaponText::AddedMagic,Was.DamageParts.AddedMagic,Now.DamageParts.AddedMagic,2,TEXT(""));
        AddValue(TEXT("第二段横斩伤害"),Was.ComboSecondDamage,Now.ComboSecondDamage,2,TEXT(""),false,Percent(M.ComboSecond));
        AddValue(RisingDragon?TEXT("第三段升龙伤害"):OverheadFinisher?TEXT("第三段竖劈伤害"):TEXT("第三段突刺伤害"),Was.ComboThirdDamage,Now.ComboThirdDamage,2,TEXT(""),false,Percent(M.ComboThird));
        AddValue(RisingDragon?TEXT("第三段升龙韧性伤害倍率"):OverheadFinisher?TEXT("第三段竖劈韧性伤害倍率"):TEXT("第三段突刺韧性伤害倍率"),Was.Modifiers.ThirdThrustToughnessMultiplier(),Now.Modifiers.ThirdThrustToughnessMultiplier(),2,TEXT("×"),false,Percent(M.ComboThirdToughness));
        AddValue(TEXT("攻击速度倍率"),Was.AttackRate,Now.AttackRate,2,TEXT("×"),false,Percent(M.AttackSpeed));
        AddValue(TEXT("普通攻击耗时"),Was.AttackSeconds,Now.AttackSeconds,2,TEXT(" s"),true);
        AddValue(RisingDragon?TEXT("升龙耗时"):OverheadFinisher?TEXT("竖劈耗时"):TEXT("突刺耗时"),Was.ThrustSeconds,Now.ThrustSeconds,2,TEXT(" s"),true);
        AddValue(TEXT("普通挥砍距离"),Was.SlashReach/100,Now.SlashReach/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(ColdSteelWeaponText::AttackDistance,Was.ThrustReach/100,Now.ThrustReach/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.AttackStamina,Now.AttackStamina,2,TEXT(""),true,Percent(M.Stamina));
        AddValue(TEXT("击杀恢复体力（最大值占比）"),Was.Modifiers.KillStaminaMaxRatio*100,Now.Modifiers.KillStaminaMaxRatio*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::BlockStaminaCost,Was.BlockStamina,Now.BlockStamina,2,TEXT(""),true,Percent(M.BlockStamina));
        AddValue(TEXT("格挡伤害减免"),Was.BlockReduction*100,Now.BlockReduction*100,1,TEXT("%"),false,Percent(M.BlockReduction));
        AddValue(TEXT("所受伤害倍率（乘法叠加）"),Was.Modifiers.DamageTaken,Now.Modifiers.DamageTaken,2,TEXT("×"),true,Percent(M.DamageTaken));
        AddValue(TEXT("闪避体力消耗倍率"),Was.Modifiers.DodgeStamina,Now.Modifiers.DodgeStamina,2,TEXT("×"),true,Percent(M.DodgeStamina));
        AddValue(TEXT("奔跑体力消耗倍率"),Was.Modifiers.SprintStamina,Now.Modifiers.SprintStamina,2,TEXT("×"),true,Percent(M.SprintStamina));
        if(M.DragonSeconds>0||M.PhoenixSeconds>0)
            for(const auto& Effect:Option->Effects)
                ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
                    [Paragraph(Effect.Key,12,Effect.Value>0?ColdSteelUI::Success:GunsmithUI::Secondary)];
        AddValue(TEXT("命中硬直时间倍率"),Was.Modifiers.HitReaction,Now.Modifiers.HitReaction,2,TEXT("×"),false,Percent(M.HitReaction));
        AddValue(ColdSteelWeaponText::ToughnessMultiplier,Was.Modifiers.ToughnessDamage,Now.Modifiers.ToughnessDamage,2,TEXT("×"),false,Percent(M.ToughnessDamage));
        AddValue(TEXT("改造物理防御穿透"),Was.Modifiers.PhysicalArmorPenetration*100,Now.Modifiers.PhysicalArmorPenetration*100,0,TEXT("%"));
        AddValue(TEXT("重击伤害倍率"),Was.HeavyMultiplier,Now.HeavyMultiplier,2,TEXT("×"));
        AddValue(TEXT("重击蓄力速度加成"),Was.HeavyChargeSpeedBonus*100.,Now.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
        AddValue(TEXT("重击蓄力时间"),Was.HeavyChargeSeconds,Now.HeavyChargeSeconds,2,TEXT(" s"),true);
        AddValue(TEXT("重击总伤害"),Was.Damage*Was.HeavyMultiplier,Now.Damage*Now.HeavyMultiplier,2,TEXT(""));
        AddValue(TEXT("重击韧性伤害倍率"),Was.Modifiers.HeavyToughnessMultiplier(),Now.Modifiers.HeavyToughnessMultiplier(),2,TEXT("×"),false,Percent(M.HeavyToughness));
        AddValue(TEXT("攻击击退距离"),Was.KnockbackCM,Now.KnockbackCM,1,TEXT(" cm"),false,Percent(M.Knockback*M.AllAttackKnockback));
        AddValue(TEXT("全部攻击击退倍率"),Was.Modifiers.AllAttackKnockback,Now.Modifiers.AllAttackKnockback,2,TEXT("×"),false,Percent(M.AllAttackKnockback));
        AddValue(TEXT("快速近战伤害倍率"),Was.QuickCombat.DamageMultiplier,Now.QuickCombat.DamageMultiplier,2,TEXT("×"));
        AddValue(TEXT("快速近战伤害"),Was.QuickCombat.Damage,Now.QuickCombat.Damage,2,TEXT(""));
        AddValue(TEXT("快速近战击退距离"),Was.QuickCombat.KnockbackCM,Now.QuickCombat.KnockbackCM,1,TEXT(" cm"),false,Percent(M.QuickCombatKnockback*M.AllAttackKnockback));
        AddValue(TEXT("快速近战韧性伤害倍率"),Was.QuickCombat.ToughnessMultiplier,Now.QuickCombat.ToughnessMultiplier,2,TEXT("×"),false,Percent(M.QuickCombatToughness));
        AddValue(ColdSteelWeaponText::QuickCombatBleed,Was.QuickCombat.BleedChance*100,Now.QuickCombat.BleedChance*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::TigerRoarToughnessTaken,Was.Modifiers.QuickCombatTigerRoarToughnessBonus*100,Now.Modifiers.QuickCombatTigerRoarToughnessBonus*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::TigerRoarDuration,Was.Modifiers.QuickCombatTigerRoarSeconds,Now.Modifiers.QuickCombatTigerRoarSeconds,0,TEXT(" s"));
        if(M.QuickCombatTigerRoarSeconds>0)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("快速近战命中敌人后施加虎啸，使目标冲击、利器、钝器的韧性抵抗归零。重复命中刷新持续时间，效果不叠加。"),12,ColdSteelUI::Success)];
        AddValue(ColdSteelWeaponText::QuickCombatPhysicalVulnerability,Was.Modifiers.QuickCombatPhysicalVulnerabilityBonus*100,Now.Modifiers.QuickCombatPhysicalVulnerabilityBonus*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::PhysicalVulnerabilityDuration,Was.Modifiers.QuickCombatPhysicalVulnerabilitySeconds,Now.Modifiers.QuickCombatPhysicalVulnerabilitySeconds,0,TEXT(" s"));
        if(M.QuickCombatPhysicalVulnerabilitySeconds>0)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("快速近战命中敌人后施加物理易伤，使目标后续受到的物理伤害提高。重复命中刷新持续时间，效果不叠加。"),12,ColdSteelUI::Success)];
        if(M.bQuickCombatAOE)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("快速近战变为范围攻击：原判定范围内的多个目标均可命中，每个目标每次出手结算一次；判定距离与宽度不变。"),12,ColdSteelUI::Success)];
        AddValue(TEXT("魔法技能冷却倍率"),Was.Modifiers.MagicCooldown,Now.Modifiers.MagicCooldown,2,TEXT("×"),true,Percent(M.MagicCooldown));
        AddValue(TEXT("魔法值消耗倍率"),Was.Modifiers.MagicCost,Now.Modifiers.MagicCost,2,TEXT("×"),true,Percent(M.MagicCost));
        AddValue(TEXT("魔法伤害倍率"),Was.Modifiers.MagicDamage,Now.Modifiers.MagicDamage,2,TEXT("×"),false,Percent(M.MagicDamage));
        AddValue(ColdSteelWeaponText::RuneVulnerability,Was.Modifiers.RuneVulnerability*100,Now.Modifiers.RuneVulnerability*100,0,TEXT("%"));
        AddValue(TEXT("剑刃易伤持续时间"),Was.Modifiers.RuneVulnerabilitySeconds,Now.Modifiers.RuneVulnerabilitySeconds,1,TEXT(" s"));
        AddValue(TEXT("弹反判定时间"),Was.ParrySeconds,Now.ParrySeconds,2,TEXT(" s"),false,Percent(M.ParryWindow));
        AddValue(TEXT("反击激励攻速倍率"),Was.Modifiers.RiposteSpeed,Now.Modifiers.RiposteSpeed,2,TEXT("×"),false,Percent(M.RiposteSpeed));
        AddValue(TEXT("反击激励耐力倍率"),Was.Modifiers.RiposteStamina,Now.Modifiers.RiposteStamina,2,TEXT("×"),true,Percent(M.RiposteStamina));
        AddValue(TEXT("反击激励持续时间"),Was.Modifiers.RiposteSeconds,Now.Modifiers.RiposteSeconds,1,TEXT(" s"));
        AddValue(ColdSteelWeaponText::ParryClovenKeep,Was.Modifiers.ClovenSeconds,Now.Modifiers.ClovenSeconds,1,TEXT(" s"));
        AddValue(ColdSteelWeaponText::ClovenPhysicalDamage,Percent(Was.Modifiers.ClovenPhysical),Percent(Now.Modifiers.ClovenPhysical),0,TEXT("%"));
        AddValue(ColdSteelWeaponText::ClovenToughnessDamage,Percent(Was.Modifiers.ClovenToughness),Percent(Now.Modifiers.ClovenToughness),0,TEXT("%"));
        if(M.ClovenSeconds>0)ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("成功弹反后，下一次普攻直接释放重击，无需蓄力。按重击消耗体力，发起即消耗强化，挥空也消耗；最多保留一次，再次弹反刷新时间。突刺与技能不消耗强化。"),12,GunsmithUI::Muted)];
        if(!FMath::IsNearlyEqual(M.Range,1.))ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("范围改造影响挥砍与突刺；快速近战使用技能自身的判定范围。"),12,GunsmithUI::Muted)];
    }
    if (RowCount == 0)
    {
        if (IsStaffWorkbench())
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("当前组合无额外数值修正；条件效果以实际激活状态为准。"),14,GunsmithUI::Secondary)];
        else if (Option->Effects.IsEmpty())
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("无额外数值修正"),14,GunsmithUI::Secondary)];
        else for (const auto& Effect : Option->Effects)
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,6)
                [Paragraph(Effect.Key,14,Effect.Value>0?ColdSteelUI::Success:Effect.Value<0?ColdSteelUI::Danger:GunsmithUI::Secondary)];
    }
    ModificationList->AddSlot().AutoHeight().Padding(0,10,0,6)[Paragraph(TEXT("配件说明"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight()
        [Paragraph(Option->Description.IsEmpty()?TEXT("暂无额外说明。"):Option->Description,14,GunsmithUI::Secondary)];
    if(IsStaffWorkbench())ModificationList->AddSlot().AutoHeight().Padding(0,10,0,0)
        [Paragraph(TEXT("改造免费；应用并保存后写入当前法杖。杖冠只在匹配杖头专精时激活，不匹配时保留外观。法杖占用主手，可搭配副手手枪。"),12,GunsmithUI::Muted)];
}
