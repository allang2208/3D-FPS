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
    TArray<FString> SpecialEffects=Option->SpecialEffects;
    auto AddEffect=[&](const FString& Text){SpecialEffects.AddUnique(Text);};
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
                [Paragraph(TEXT("能力增减 · 当前组合实值／相对该栏原厂"),12,GunsmithUI::Muted)];
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
        const auto& B=Option->Bow;
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        auto Ratio=[](double W,double N){return W>.00001?(N/W-1.)*100.:0.;};
        AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage.Total(),Now.Damage.Total(),2,TEXT(""),false,Percent(B.Damage));
        AddValue(ColdSteelWeaponText::DrawTime,Was.Draw,Now.Draw,2,TEXT(" s"),true,Ratio(Was.Draw,Now.Draw));
        AddValue(TEXT("拉弓速度加成"),Was.DrawSpeedBonus*100.,Now.DrawSpeedBonus*100.,1,TEXT("%"));
        AddValue(ColdSteelWeaponText::NockTime,Was.Nock,Now.Nock,2,TEXT(" s"),true,Percent(B.Nock));
        AddValue(ColdSteelWeaponText::ProjectileSpeed,Was.Speed,Now.Speed,1,TEXT(" m/s"),false,Percent(B.Speed));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.Stamina,Now.Stamina,2,TEXT(""),true,Percent(B.Stamina));
        AddValue(ColdSteelWeaponText::HoldTime,Was.Hold,Now.Hold,2,TEXT(" s"),false,Percent(B.Hold));
        AddValue(ColdSteelWeaponText::Sway,Was.Sway,Now.Sway,2,TEXT(""),true,Percent(B.Sway));
        AddValue(ColdSteelWeaponText::HipSpreadAngle,FMath::RadiansToDegrees(FMath::Atan(Was.Spread)),FMath::RadiansToDegrees(FMath::Atan(Now.Spread)),2,TEXT("°"),true,Percent(B.Spread));
        AddValue(ColdSteelWeaponText::ADS,Was.ADS*1000,Now.ADS*1000,0,TEXT(" ms"),true,Percent(B.ADS));
        ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)[Paragraph(ColdSteelWeaponText::BowScope,12,GunsmithUI::Muted)];
    }
    else if(IsToolWorkbench()&&Item)
    {
        // 工具四栏：采集与自卫两条链路读同一份评估，行名与目录 effects 措辞一致。
        const auto Was=ColdSteelTool::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelTool::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const auto& T=Option->Tool;
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        auto Ratio=[](double W,double N){return W>.00001?(N/W-1.)*100.:0.;};
        AddValue(TEXT("采集产出倍率"),Was.HarvestYield,Now.HarvestYield,2,TEXT("×"),false,Percent(T.HarvestYield));
        AddValue(TEXT("采集伤害"),ProductionTreeHealth::StrikeDamage(Was),
            ProductionTreeHealth::StrikeDamage(Now),1,TEXT(" / 挥"),false,Ratio(ProductionTreeHealth::StrikeDamage(Was),ProductionTreeHealth::StrikeDamage(Now)));
        AddValue(TEXT("采集距离"),Was.HarvestReachCM/100,Now.HarvestReachCM/100,2,TEXT(" m"),false,Percent(T.HarvestReach));
        AddValue(TEXT("命中宽容半径"),Was.HarvestRadiusCM,Now.HarvestRadiusCM,0,TEXT(" cm"),false,Ratio(Was.HarvestRadiusCM,Now.HarvestRadiusCM));
        AddValue(TEXT("额外产出几率"),Was.BonusHarvestChance*100,Now.BonusHarvestChance*100,0,TEXT("%"));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.StaminaCost,Now.StaminaCost,2,TEXT(""),true,Percent(T.Stamina));
        AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage.Total(),Now.Damage.Total(),2,TEXT(""),false,Ratio(Was.Damage.Total(),Now.Damage.Total()));
        AddValue(ColdSteelWeaponText::BasePhysical,Was.Damage.BasePhysical,Now.Damage.BasePhysical,2,TEXT(""),false,Percent(T.Damage));
        AddValue(ColdSteelWeaponText::AddedPhysical,Was.Damage.AddedPhysical,Now.Damage.AddedPhysical,2,TEXT(""),false,Ratio(Was.Damage.AddedPhysical,Now.Damage.AddedPhysical));
        AddValue(ColdSteelWeaponText::AddedMagic,Was.Damage.AddedMagic,Now.Damage.AddedMagic,2,TEXT(""),false,Ratio(Was.Damage.AddedMagic,Now.Damage.AddedMagic));
        AddValue(TEXT("暴击率"),Was.CriticalChanceAdd,Now.CriticalChanceAdd,0,TEXT("%"));
        AddValue(TEXT("韧性伤害倍率"),Was.ToughnessDamage,Now.ToughnessDamage,2,TEXT("×"),false,Percent(T.ToughnessDamage));
        AddValue(ColdSteelWeaponText::AttackSpeedMultiplier,Was.Modifiers.AttackSpeed,Now.Modifiers.AttackSpeed,2,TEXT("×"),false,Percent(T.AttackSpeed));
        AddValue(ColdSteelWeaponText::AttackInterval,Was.SwingSeconds*1000,Now.SwingSeconds*1000,0,TEXT(" ms"),true,Ratio(Was.SwingSeconds,Now.SwingSeconds));
        AddValue(TEXT("接触时刻"),Was.ContactSeconds,Now.ContactSeconds,2,TEXT(" s"),true,Ratio(Was.ContactSeconds,Now.ContactSeconds));
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
    AddValue(ColdSteelWeaponText::Capacity,Before.Capacity,After.Capacity,0,TEXT(" 发"),false,Ratio(Before.Capacity,After.Capacity));
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
        const double BeforeRate=60*Before.BurstCount/((Before.BurstCount-1)*BeforeInterval+FMath::Max(BeforeInterval,BeforeDelay));
        const double AfterRate=60*After.BurstCount/((After.BurstCount-1)*AfterInterval+FMath::Max(AfterInterval,AfterDelay));
        AddValue(TEXT("含组间隔理论射速"),BeforeRate,AfterRate,0,TEXT(" /min"),false,Ratio(BeforeRate,AfterRate));
    }
    AddValue(ColdSteelWeaponText::RecoilIndex,Before.Recoil,After.Recoil,1,TEXT(""),true,Ratio(Before.Recoil,After.Recoil));
    AddValue(ColdSteelWeaponText::Stability,Before.Handling.Stability,After.Handling.Stability,1,TEXT(" /100"),false,Ratio(Before.Handling.Stability,After.Handling.Stability));
    if(!FMath::IsNearlyEqual(Option->Shake,1.0))AddValue(TEXT("开火抖动指数"),Before.Shake,After.Shake,1,TEXT(""),true,Ratio(Before.Shake,After.Shake));
    AddValue(ColdSteelWeaponText::HipSpreadMultiplier,Before.Spread,After.Spread,2,TEXT("×"),true,Ratio(Before.Spread,After.Spread));
    AddValue(ColdSteelWeaponText::EffectiveRange,Before.Range,After.Range,0,TEXT(" m"),false,Ratio(Before.Range,After.Range));
    AddValue(ColdSteelWeaponText::ProjectileSpeed,Before.Speed,After.Speed,0,TEXT(" m/s"),false,Ratio(Before.Speed,After.Speed));
    // 脚架类配件的架设机制只有 effects 文案（部署增益与卸下限制不进数值行），
    // 照回退列表同一格式显示：收益绿、代价红、中性灰。
    if(Id.Contains(TEXT("bipod")))
        for(const auto& Effect:Option->Effects)
            ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
                [Paragraph(Effect.Key,14,Effect.Value>0?ColdSteelUI::Success:Effect.Value<0?ColdSteelUI::Danger:GunsmithUI::Secondary)];
    }
    else if(Item)
    {
        const auto Was=ColdSteelMelee::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelMelee::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const bool OverheadFinisher=ColdSteelModularSword::UsesOverheadFinisher(*Item,&Gunsmith->Draft());
        const bool RisingDragon=ColdSteelModularSword::UsesRisingDragonFinisher(*Item,&Gunsmith->Draft());
        const auto& M=Option->Melee;
        // Show direct modifiers only. Combo stages and additional damage amounts
        // are omitted from both selected details and the overview.
        const bool CompactBlade=SelectedCategory==TEXT("blade_1");
        auto Percent=[](double Mult){return (Mult-1.)*100.;};
        auto Ratio=[](double W,double N){return W>.00001?(N/W-1.)*100.:0.;};
        if(CompactBlade&&Id!=TEXT("false")&&Option->SpecialEffects.IsEmpty())
        {
            if(RisingDragon)AddEffect(TEXT("连段变化｜连段收尾变为升龙，准备时间缩短50%；攻速仍按挥砍节奏计算。"));
            else if(OverheadFinisher)AddEffect(TEXT("连段变化｜连段收尾变为冲刺竖劈，使用前方矩形判定。"));
        }
        if(!FMath::IsNearlyEqual(M.PhysicalDamage,1.))
            AddValue(TEXT("物理伤害"),Was.DamageParts.BasePhysical+Was.DamageParts.AddedPhysical,Now.DamageParts.BasePhysical+Now.DamageParts.AddedPhysical,2,TEXT(""),false,Percent(M.PhysicalDamage));
        if(!FMath::IsNearlyEqual(M.Damage,1.))AddValue(ColdSteelWeaponText::BasePhysical,Was.DamageParts.BasePhysical,Now.DamageParts.BasePhysical,2,TEXT(""),false,Percent(M.Damage*M.AllAttackDamage));
        AddValue(TEXT("全部近战攻击伤害倍率"),Was.Modifiers.AllAttackDamage,Now.Modifiers.AllAttackDamage,2,TEXT("×"),false,Percent(M.AllAttackDamage));
        AddValue(TEXT("攻击速度倍率"),Was.AttackRate,Now.AttackRate,2,TEXT("×"),false,Percent(M.AttackSpeed));
        AddValue(ColdSteelWeaponText::AttackDistance,Was.ThrustReach/100,Now.ThrustReach/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.AttackStamina,Now.AttackStamina,2,TEXT(""),true,Percent(M.Stamina));
        if(M.KillStaminaMaxRatio>0.)AddEffect(FString::Printf(TEXT("击杀恢复｜击杀目标后，恢复最大体力的%.0f%%。"),M.KillStaminaMaxRatio*100.));
        AddValue(TEXT("改造暴击率"),Was.Modifiers.CriticalChanceAdd,Now.Modifiers.CriticalChanceAdd,0,TEXT("%"),false,M.CriticalChanceAdd);
        AddValue(ColdSteelWeaponText::BlockStaminaCost,Was.BlockStamina,Now.BlockStamina,2,TEXT(""),true,Percent(M.BlockStamina));
        AddValue(TEXT("格挡伤害减免"),Was.BlockReduction*100,Now.BlockReduction*100,1,TEXT("%"),false,Percent(M.BlockReduction));
        AddValue(TEXT("所受伤害倍率（乘法叠加）"),Was.Modifiers.DamageTaken,Now.Modifiers.DamageTaken,2,TEXT("×"),true,Percent(M.DamageTaken));
        AddValue(TEXT("闪避体力消耗倍率"),Was.Modifiers.DodgeStamina,Now.Modifiers.DodgeStamina,2,TEXT("×"),true,Percent(M.DodgeStamina));
        AddValue(TEXT("奔跑体力消耗倍率"),Was.Modifiers.SprintStamina,Now.Modifiers.SprintStamina,2,TEXT("×"),true,Percent(M.SprintStamina));
        if(M.DragonSeconds>0.)
        {
            AddEffect(FString::Printf(TEXT("玄龙｜成功格挡或完美弹反后，获得%.0f秒强化，冷却%.0f秒。下一次剑刃命中伤害%+.0f%%，额外造成%.0f基础韧性伤害。"),M.DragonSeconds,M.DragonCooldown,Percent(M.DragonDamage),M.DragonToughness));
            AddEffect(TEXT("消耗规则｜最多保留一次；首次命中即消耗，挥空不消耗。快速近战、裂空斩和持续伤害不触发；超时、换武器或死亡清除。"));
        }
        if(M.PhoenixSeconds>0.)
        {
            AddEffect(FString::Printf(TEXT("凤舞｜侧闪或后撤触发，持续%.0f秒，攻速%+.0f%%；冷却%.0f秒。普通奔跑不触发。"),M.PhoenixSeconds,Percent(M.PhoenixSpeed),M.PhoenixCooldown));
            AddEffect(FString::Printf(TEXT("回复规则｜前%.0f次剑刃命中各恢复最大生命的%.0f%%，每次出手只回复一次。快速近战、裂空斩及持续伤害不触发；切换武器清除凤舞，冷却不重置。"),M.PhoenixHealHits,M.PhoenixHealRatio*100.));
        }
        AddValue(TEXT("命中硬直时间倍率"),Was.Modifiers.HitReaction,Now.Modifiers.HitReaction,2,TEXT("×"),false,Percent(M.HitReaction));
        AddValue(ColdSteelWeaponText::ToughnessMultiplier,Was.Modifiers.ToughnessDamage,Now.Modifiers.ToughnessDamage,2,TEXT("×"),false,Percent(M.ToughnessDamage));
        AddValue(TEXT("改造物理防御穿透"),Was.Modifiers.PhysicalArmorPenetration*100,Now.Modifiers.PhysicalArmorPenetration*100,0,TEXT("%"));
        AddValue(TEXT("重击伤害倍率"),Was.HeavyMultiplier,Now.HeavyMultiplier,2,TEXT("×"),false,Ratio(Was.HeavyMultiplier,Now.HeavyMultiplier));
        AddValue(TEXT("重击蓄力速度加成"),Was.HeavyChargeSpeedBonus*100.,Now.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
        if(!FMath::IsNearlyEqual(M.HeavyToughness,1.))AddValue(TEXT("重击韧性伤害倍率"),Was.Modifiers.HeavyToughnessMultiplier(),Now.Modifiers.HeavyToughnessMultiplier(),2,TEXT("×"),false,Percent(M.HeavyToughness));
        AddValue(TEXT("攻击击退距离"),Was.KnockbackCM,Now.KnockbackCM,1,TEXT(" cm"),false,Percent(M.Knockback*M.AllAttackKnockback));
        AddValue(TEXT("全部攻击击退倍率"),Was.Modifiers.AllAttackKnockback,Now.Modifiers.AllAttackKnockback,2,TEXT("×"),false,Percent(M.AllAttackKnockback));
        if(!FMath::IsNearlyZero(M.QuickCombatDamageAdd))AddValue(TEXT("快速近战伤害倍率"),Was.QuickCombat.DamageMultiplier,Now.QuickCombat.DamageMultiplier,2,TEXT("×"),false,Ratio(Was.QuickCombat.DamageMultiplier,Now.QuickCombat.DamageMultiplier));
        AddValue(TEXT("快速近战击退距离"),Was.QuickCombat.KnockbackCM,Now.QuickCombat.KnockbackCM,1,TEXT(" cm"),false,Percent(M.QuickCombatKnockback*M.AllAttackKnockback));
        if(!FMath::IsNearlyEqual(M.QuickCombatToughness,1.))AddValue(TEXT("快速近战韧性伤害倍率"),Was.QuickCombat.ToughnessMultiplier,Now.QuickCombat.ToughnessMultiplier,2,TEXT("×"),false,Percent(M.QuickCombatToughness));
        if(M.QuickCombatBleedChance>0.)AddEffect(FString::Printf(TEXT("出血｜快速近战命中有%.0f%%概率施加1层出血。"),M.QuickCombatBleedChance*100.));
        if(M.QuickCombatTigerRoarSeconds>0.)AddEffect(FString::Printf(TEXT("虎啸｜快速近战命中后，使目标韧性承伤提高%.0f%%，冲击、利器、钝器的韧性抵抗归零，持续%.0f秒。重复命中刷新，不叠加。"),M.QuickCombatTigerRoarToughnessBonus*100.,M.QuickCombatTigerRoarSeconds));
        if(M.QuickCombatPhysicalVulnerabilitySeconds>0.)AddEffect(FString::Printf(TEXT("物理易伤｜快速近战命中后，目标受到的物理伤害提高%.0f%%，持续%.0f秒。重复命中刷新，不叠加。"),M.QuickCombatPhysicalVulnerabilityBonus*100.,M.QuickCombatPhysicalVulnerabilitySeconds));
        if(M.QuickCombatRuneVulnerabilitySeconds>0.)AddEffect(FString::Printf(TEXT("魔法易伤｜快速近战命中后，目标受到的魔法伤害提高%.0f%%，持续%.0f秒。重复命中刷新，不叠加。"),M.QuickCombatRuneVulnerability*100.,M.QuickCombatRuneVulnerabilitySeconds));
        if(M.bQuickCombatAOE)AddEffect(TEXT("范围攻击｜快速近战可命中原判定范围内的多个目标，每个目标每次出手结算一次；判定距离与宽度不变。"));
        if(Was.Modifiers.JingangBonus>0.||Now.Modifiers.JingangBonus>0.)
        {
            AddValue(TEXT("物理防御常驻加成"),Was.Modifiers.JingangBonus*100,Now.Modifiers.JingangBonus*100,0,TEXT("%"));
            AddValue(TEXT("魔法防御常驻加成"),Was.Modifiers.JingangBonus*100,Now.Modifiers.JingangBonus*100,0,TEXT("%"));
        }
        AddValue(TEXT("魔法技能冷却倍率"),Was.Modifiers.MagicCooldown,Now.Modifiers.MagicCooldown,2,TEXT("×"),true,Percent(M.MagicCooldown));
        AddValue(TEXT("魔法值消耗倍率"),Was.Modifiers.MagicCost,Now.Modifiers.MagicCost,2,TEXT("×"),true,Percent(M.MagicCost));
        AddValue(TEXT("魔法伤害倍率"),Was.Modifiers.MagicDamage,Now.Modifiers.MagicDamage,2,TEXT("×"),false,Percent(M.MagicDamage));
        if(M.RuneVulnerabilitySeconds>0.)AddEffect(FString::Printf(TEXT("剑刃易伤｜剑刃攻击命中后，目标受到的魔法伤害提高%.0f%%，持续%.0f秒。重复命中刷新，不叠加。"),M.RuneVulnerability*100.,M.RuneVulnerabilitySeconds));
        AddValue(TEXT("弹反判定时间"),Was.ParrySeconds,Now.ParrySeconds,2,TEXT(" s"),false,Percent(M.ParryWindow));
        if(M.RiposteSeconds>0.)AddEffect(FString::Printf(TEXT("反击激励｜成功弹反后，攻击速度%+.0f%%、攻击体力消耗%+.0f%%，持续%.0f秒。"),Percent(M.RiposteSpeed),Percent(M.RiposteStamina),M.RiposteSeconds));
        if(M.ClovenSeconds>0.)
        {
            AddEffect(FString::Printf(TEXT("弹反重击｜成功弹反后%.0f秒内，下一次普攻直接释放免蓄力重击；该击物理伤害%+.0f%%、韧性伤害%+.0f%%。"),M.ClovenSeconds,Percent(M.ClovenPhysical),Percent(M.ClovenToughness)));
            AddEffect(TEXT("消耗规则｜按重击消耗体力，出手即消耗强化，挥空也消耗；最多保留一次，再次弹反刷新。突刺与技能不消耗强化。"));
        }
        if(!FMath::IsNearlyEqual(M.Range,1.))ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)
            [Paragraph(TEXT("距离加成作用于挥砍、突刺，不影响快速近战。"),12,GunsmithUI::Muted)];
    }
    if(RowCount==0)
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
            [Paragraph(TEXT("无常驻属性增减"),14,GunsmithUI::Muted)];
    // Legacy mechanism-only options retain their explanation. New options declare
    // special_effects explicitly, independent of how many numeric rows they have.
    if(RowCount==0&&SpecialEffects.IsEmpty()&&!IsStaffWorkbench())
        for(const auto& Effect:Option->Effects)AddEffect(Effect.Key);
    if(!SpecialEffects.IsEmpty())
    {
        ModificationList->AddSlot().AutoHeight().Padding(0,12,0,6)
            [Paragraph(TEXT("特效说明"),14,ColdSteelUI::Success,true)];
        for(const FString& Effect:SpecialEffects)
        {
            FString Label,Body;
            if(Effect.Split(TEXT("｜"),&Label,&Body))
            {
                ModificationList->AddSlot().AutoHeight().Padding(0,4,0,3)
                    [Paragraph(Label,13,ColdSteelUI::Success,true)];
            }
            else Body=Effect;
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,7)
                [Paragraph(Body,14,ColdSteelUI::Success)];
        }
    }
    ModificationList->AddSlot().AutoHeight().Padding(0,10,0,6)[Paragraph(TEXT("配件说明"),12,GunsmithUI::Muted)];
    ModificationList->AddSlot().AutoHeight()
        [Paragraph(Option->Description.IsEmpty()?TEXT("暂无额外说明。"):Option->Description,14,GunsmithUI::Secondary)];
    if(IsStaffWorkbench())ModificationList->AddSlot().AutoHeight().Padding(0,10,0,0)
        [Paragraph(TEXT("改造免费；应用并保存后写入当前法杖。杖冠只在匹配杖头专精时激活，不匹配时保留外观。法杖占用主手，可搭配副手手枪。"),12,GunsmithUI::Muted)];
}
