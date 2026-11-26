#include "ColdSteelWeaponText.h"
#include "../Weapons/M249WeaponAssets.h"
#include "M4GunsmithWidget.h"
#include "../Weapons/TacticalDeviceVariants.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelStaffModificationUI.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/PojunGrip.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/RuneboundHammerTuning.h"
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
    // M249 exposes its separated factory modules before common upgrades exist.
    if(Model()->Definition()==M249WeaponAssets::Definition)
        return Weapon&&Weapon->Allowed.Contains(SlotKey)&&Options&&!Options->IsEmpty();
    // Keep an empty surface slot visible on swords awaiting material authoring.
    if(SlotKey==TEXT("blade_material")&&IsMeleeWorkbench())
        return Weapon&&Weapon->Allowed.Contains(SlotKey)&&Options;
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
        ModificationList->AddSlot().AutoHeight()[Paragraph(SelectedCategory==TEXT("blade_material")?
            TEXT("暂无可用材质。"):TEXT("当前武器没有可选改造项目。"),14,GunsmithUI::Secondary)];
        return;
    }
    FString Installed = Item ? Gunsmith->Installed(*Item).FindRef(SelectedCategory) : FString();
    if (Installed.IsEmpty()) Installed = TEXT("false");
    ModificationList->AddSlot().AutoHeight()[Paragraph(Option->Name,16,GunsmithUI::Text,true)];
    ModificationList->AddSlot().AutoHeight().Padding(0,5,0,12)
        [Paragraph(Installed==Id?(Id==TEXT("false")?TEXT("当前原厂配置"):TEXT("已安装")):TEXT("已选 · 待应用"),12,
            Id==TEXT("false")?GunsmithUI::Muted:ColdSteelUI::Success)];
    const bool bHammerDetail=Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item);
    if(bHammerDetail)
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)[Paragraph(Option->Description,14,GunsmithUI::Secondary)];
    else if(IsToolWorkbench()||IsBowWorkbench()||IsStaffWorkbench())
    {
        // 数值改造先行：外观归属如实写在目录的 appearance 字段里。
        if(!Option->Appearance.IsEmpty()&&Option->Appearance!=Option->Description)ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
            [Paragraph(Option->Appearance,12,GunsmithUI::Secondary)];
    }
    else if(Item&&IsMeleeWorkbench())
    {
        const FString Appearance=SelectedCategory==TEXT("blade_material")?Option->Appearance:ColdSteelModularSword::Appearance(*Item,SelectedCategory,Id);
        if(!Appearance.IsEmpty()&&Appearance!=Option->Description)ModificationList->AddSlot().AutoHeight().Padding(0,0,0,10)
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
    auto AddEffect=[&](const FString& Text)
    {
        FString Title,Body;
        // A catalog paragraph owns its mechanism; calculated fallback copy must
        // not repeat it merely because punctuation or wording differs.
        if(Text.Split(TEXT("｜"),&Title,&Body)&&SpecialEffects.ContainsByPredicate([&](const FString& Existing)
            {return Existing.StartsWith(Title+TEXT("｜"));}))return;
        SpecialEffects.AddUnique(Text);
    };
    if(TacticalDeviceVariants::IsSlot(SelectedCategory)&&TacticalDeviceVariants::SupportsSecondary(Gunsmith->Definition()))
    {
        const auto& Parts=Gunsmith->Draft();
        const FString Primary=Parts.FindRef(TacticalDeviceVariants::PrimarySlot),Secondary=Parts.FindRef(TacticalDeviceVariants::SecondarySlot);
        FString Note=TEXT("两侧可独立安装镭射或手电，可同时使用镭射与照明。双镭射均显示各自的光束与光点，属性数值只取最强的一件，不重复叠加；同强度优先战术挂件Ⅰ。");
        if(TacticalDeviceVariants::IsLaser(Primary)&&TacticalDeviceVariants::IsLaser(Secondary))
        {
            const FString Active=TacticalDeviceVariants::ActiveLaserSlot(Primary,Secondary);
            const auto* Effective=Gunsmith->Option(Gunsmith->Definition(),Active,Parts.FindRef(Active));
            if(Effective)Note+=TEXT(" 当前数值生效：")+Gunsmith->CategoryLabel(Gunsmith->Definition(),Active)+TEXT(" · ")+Effective->Name+TEXT("。两件镭射均正常发光。");
        }
        AddEffect(TEXT("双侧战术配件｜")+Note);
    }
    // The card keeps only the basic description, so every numeric change belongs
    // here and is derived from the catalog multipliers - never hand written.
    // The percent reads exactly like the catalog field: minus is faster (green),
    // plus is slower (red), and the value equals ads_percent.
    auto AddValue = [&](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false,double Percent=0.,const TCHAR* UnchangedNote=nullptr)
    {
        const double Delta = Final-Base;
        const bool Unchanged=FMath::Abs(Delta)<.00001;
        if (Unchanged&&!UnchangedNote) return;
        const FString PercentText=FMath::IsNearlyZero(Percent,.01)?FString():FString::Printf(TEXT("%+.0f%%"),Percent);
        if (RowCount++ == 0)
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("能力增减 · 当前组合实值／相对该栏原厂"),12,GunsmithUI::Muted)];
        const auto Color = Unchanged ? GunsmithUI::Muted : (((Delta>0)!=Lower) ? ColdSteelUI::Success : ColdSteelUI::Danger);
        const auto PercentColor = Unchanged ? (((Percent>0)!=Lower) ? ColdSteelUI::Success : ColdSteelUI::Danger) : Color;
        const FString DeltaText=Unchanged?FString::Printf(TEXT("%.*f%s"),Digits,0.,Unit):FString::Printf(TEXT("%+.*f%s"),Digits,Delta,Unit);
        ModificationList->AddSlot().AutoHeight().Padding(0,0,0,4)
            [SNew(SBorder).BorderImage(&RowBrush).Padding(8,6)
                [SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(0,0,10,0)
                    [SNew(SHorizontalBox)
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(Name)).Font(GunsmithUI::TextFont(14)).ColorAndOpacity(GunsmithUI::Secondary)
                            .WrapTextAt_Lambda([this](){return (SelectedDetailsWidth()-26.f)*.5f;})]
                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(PercentText)).Font(GunsmithUI::NumberFont(13)).ColorAndOpacity(PercentColor)]]
                    +SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()
                        [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%.*f%s"),Digits,Final,Unit)))
                            .Font(GunsmithUI::NumberFont(14)).ColorAndOpacity(GunsmithUI::Text).Justification(ETextJustify::Right)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)
                        [SNew(STextBlock).Text(FText::FromString(DeltaText))
                            .Font(GunsmithUI::NumberFont(12)).ColorAndOpacity(Color).Justification(ETextJustify::Right)]]]];
        if(Unchanged&&UnchangedNote)
            ModificationList->AddSlot().AutoHeight().Padding(8,0,8,6)
                [Paragraph(UnchangedNote,12,GunsmithUI::Muted)];
    };
    auto AddAttackSpeed = [&](double Base,double Final,double Multiplier)
    {
        // Keep the catalog modifier visible even when the effective rate is clamped.
        const TCHAR* UnchangedNote=FMath::IsNearlyEqual(Multiplier,1.)?nullptr:TEXT("攻速受限，当前实际变化为 0。");
        AddValue(ColdSteelWeaponText::AttackSpeedMultiplier,Base,Final,2,TEXT("×"),false,(Multiplier-1.)*100.,UnchangedNote);
    };
    if(IsStaffWorkbench()&&Item)
    {
        const auto Was=ColdSteelStaff::Resolve(*Item,&WithoutPart),Now=ColdSteelStaff::Resolve(*Item,&Gunsmith->Draft());
        auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        for(const auto& Field:ColdSteelStaffUI::Fields)
        {
            const double BeforeValue=E->CraftEffect(Was,Field.Key)*Field.Scale,AfterValue=E->CraftEffect(Now,Field.Key)*Field.Scale;
            AddValue(Field.Label,BeforeValue,AfterValue,Field.Digits,Field.Unit,
                ColdSteelStaffUI::LowerBetter(Field,BeforeValue,AfterValue),
                FCString::Strcmp(Field.Unit,TEXT("%"))==0?AfterValue-BeforeValue:0.);
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
        if(!FMath::IsNearlyEqual(B.MagicDamage,1.))
            AddValue(TEXT("玩家魔法伤害"),100.,B.MagicDamage*100.,0,TEXT("%"),false,Percent(B.MagicDamage));
        if(!FMath::IsNearlyEqual(B.ManaCost,1.))
            AddValue(TEXT("玩家魔法消耗"),100.,B.ManaCost*100.,0,TEXT("%"),true,Percent(B.ManaCost));
        if(!FMath::IsNearlyEqual(B.PhysicalDamage,1.))
            AddValue(TEXT("物理伤害"),Was.Damage.BasePhysical+Was.Damage.AddedPhysical,Now.Damage.BasePhysical+Now.Damage.AddedPhysical,2,TEXT(""),false,Percent(B.PhysicalDamage));
        else
            AddValue(ColdSteelWeaponText::TotalDamage,Was.Damage.Total(),Now.Damage.Total(),2,TEXT(""),false,Ratio(Was.Damage.Total(),Now.Damage.Total()));
        AddValue(ColdSteelWeaponText::EffectiveRange,Was.Range,Now.Range,2,TEXT(" m"),false,Percent(B.Range));
        AddValue(ColdSteelWeaponText::CriticalBonus,Was.CriticalDamageBonus*100.,Now.CriticalDamageBonus*100.,0,TEXT("%"));
        if(!FMath::IsNearlyZero(B.DrawSpeedBonus))
            AddValue(TEXT("拉弓速度"),Was.DrawSpeedBonus*100.,Now.DrawSpeedBonus*100.,1,TEXT("%"),false,B.DrawSpeedBonus*100.);
        else
            AddValue(ColdSteelWeaponText::DrawTime,Was.Draw,Now.Draw,2,TEXT(" s"),true,Ratio(Was.Draw,Now.Draw));
        AddValue(ColdSteelWeaponText::RhythmWindow,Was.RhythmWindow,Now.RhythmWindow,2,TEXT(" s"),false,B.RhythmWindowBonus*100.);
        AddValue(ColdSteelWeaponText::NockTime,Was.Nock,Now.Nock,2,TEXT(" s"),true,Percent(B.Nock));
        AddValue(ColdSteelWeaponText::ProjectileSpeed,Was.Speed,Now.Speed,1,TEXT(" m/s"),false,Percent(B.Speed));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.Stamina,Now.Stamina,2,TEXT(""),true,Percent(B.Stamina));
        AddValue(ColdSteelWeaponText::BowChargeStamina,Was.ChargeStamina,Now.ChargeStamina,2,TEXT(" /s"),true,Percent(B.ChargeStamina));
        AddValue(ColdSteelWeaponText::Sway,Was.Sway,Now.Sway,2,TEXT(""),true,Percent(B.Sway));
        AddValue(ColdSteelWeaponText::HipSpreadAngle,FMath::RadiansToDegrees(FMath::Atan(Was.Spread)),FMath::RadiansToDegrees(FMath::Atan(Now.Spread)),2,TEXT("°"),true,Percent(B.Spread));
        AddValue(ColdSteelWeaponText::ADS,Was.ADS*1000,Now.ADS*1000,0,TEXT(" ms"),true,Percent(B.ADS));
        ModificationList->AddSlot().AutoHeight().Padding(0,6,0,0)[Paragraph(ColdSteelWeaponText::BowScope,12,GunsmithUI::Muted)];
    }
    else if(Item&&ColdSteelInventory::IsTwoHandedBlunt(*Item))
    {
        const auto Ratio=[](double W,double N){return W>.00001?(N/W-1.)*100.:0.;};
        const auto Was=ColdSteelTool::Evaluate(*Item,Profile,&WithoutPart);
        const auto Now=ColdSteelTool::Evaluate(*Item,Profile,&Gunsmith->Draft());
        const auto& M=Option->Melee;
        const bool StarOathPart=Item->Definition==RuneboundHammer::Definition&&SelectedCategory==TEXT("hammer_heads")&&Id==RuneboundHammer::StarOathHead;
        if(!StarOathPart&&!FMath::IsNearlyEqual(M.PhysicalDamage,1.))AddValue(TEXT("物理伤害"),Was.Damage.BasePhysical+Was.Damage.AddedPhysical,Now.Damage.BasePhysical+Now.Damage.AddedPhysical,2,TEXT(""),false,(M.PhysicalDamage-1.)*100.);
        if(!FMath::IsNearlyZero(M.PhysicalAttackAdd))AddValue(TEXT("物理攻击力"),Was.PhysicalAttack,Now.PhysicalAttack,0,TEXT(""));
        if(Item->Definition==RuneboundHammer::Definition&&Profile)
        {
            const auto Mult=[](const FGunsmithParts& Parts)
                {return Parts.FindRef(TEXT("rune"))==TEXT("destruction_mana_rune")?RuneboundHammer::DestructionAttributeMultiplier:1.;};
            const auto* Held=Profile->Equipped();
            const auto Power=[](const FGunsmithParts& Parts)
                {return Parts.FindRef(TEXT("hammer_heads"))==RuneboundHammer::StarOathHead?RuneboundHammer::StarOathAttackMultiplier:1.;};
            const auto* Active=Profile->ActiveProductionTool();
            const double InstalledPower=Active?RuneboundHammer::AttackMultiplier(*Active):1.;
            for(FName Stat:{FName(TEXT("atk")),FName(TEXT("matk"))})
                AddValue(Stat==TEXT("atk")?TEXT("物理攻击力"):TEXT("魔法攻击力"),
                    Profile->Derived(Stat)/InstalledPower*Power(WithoutPart),
                    Profile->Derived(Stat)/InstalledPower*Power(Gunsmith->Draft()),2,TEXT(""),false,
                    (Power(Gunsmith->Draft())/Power(WithoutPart)-1.)*100.);
            const double InstalledAttributeMult=Held?RuneboundHammer::AttributeMultiplier(*Held):1.;
            const double From=Mult(WithoutPart),To=Mult(Gunsmith->Draft());
            if(!FMath::IsNearlyEqual(From,To))for(FName Attribute:{FName(TEXT("wis")),FName(TEXT("intt"))})
            {
                const double Base=Profile->Attribute(Attribute)/InstalledAttributeMult;
                AddValue(Attribute==TEXT("wis")?TEXT("精神"):TEXT("智力"),Base*From,Base*To,2,TEXT(""),false,(To/From-1.)*100.);
            }
        }
        AddAttackSpeed(Was.RateScale,Now.RateScale,M.AttackSpeed);
        AddValue(ColdSteelWeaponText::CriticalChance,Before.Melee.MeleeCriticalChanceAdd,After.Melee.MeleeCriticalChanceAdd,0,TEXT("%"),false,M.MeleeCriticalChanceAdd);
        AddValue(TEXT("暴击伤害"),Before.Melee.MeleeCriticalDamageBonus*100.,After.Melee.MeleeCriticalDamageBonus*100.,0,TEXT("%"),false,M.MeleeCriticalDamageBonus*100.);
        if(!FMath::IsNearlyEqual(M.BlockStamina,1.))
            AddValue(ColdSteelWeaponText::BlockStaminaCost,ColdSteelMelee::BlockStamina(Before.Melee,Profile),ColdSteelMelee::BlockStamina(After.Melee,Profile),2,TEXT(""),true,(M.BlockStamina-1.)*100.);
        AddValue(ColdSteelWeaponText::StaminaCost,Was.StaminaCost,Now.StaminaCost,2,TEXT(""),true,(M.Stamina-1.)*100.);
        if(!FMath::IsNearlyEqual(M.HeavyReleaseStamina,1.))
            AddValue(TEXT("重击出手体力消耗"),Was.HeavyReleaseStaminaCost,Now.HeavyReleaseStaminaCost,2,TEXT(""),true,(M.HeavyReleaseStamina-1.)*100.);
        AddValue(TEXT("韧性伤害倍率"),Was.ToughnessDamage,Now.ToughnessDamage,2,TEXT("×"),false,(M.ToughnessDamage-1.)*100.);
        AddValue(TEXT("改造物理防御穿透"),Before.Melee.PhysicalArmorPenetration*100.,After.Melee.PhysicalArmorPenetration*100.,0,TEXT("%"),false,M.PhysicalArmorPenetration*100.);
        AddValue(TEXT("重击伤害倍率"),Was.HeavyDamageMultiplier,Now.HeavyDamageMultiplier,2,TEXT("×"),false,Ratio(Was.HeavyDamageMultiplier,Now.HeavyDamageMultiplier));
        AddValue(TEXT("重击蓄力速度加成"),Was.HeavyChargeSpeedBonus*100.,Now.HeavyChargeSpeedBonus*100.,0,TEXT("%"));
        AddValue(TEXT("所有技能冷却倍率"),Before.Melee.SkillCooldown,After.Melee.SkillCooldown,2,TEXT("×"),true,(M.SkillCooldown-1.)*100.);
        AddValue(TEXT("武技冷却倍率"),Before.Melee.MartialCooldown,After.Melee.MartialCooldown,2,TEXT("×"),true,(M.MartialCooldown-1.)*100.);
        AddValue(TEXT("魔法技能冷却倍率"),Before.Melee.MagicCooldown,After.Melee.MagicCooldown,2,TEXT("×"),true,(M.MagicCooldown-1.)*100.);
        AddValue(TEXT("魔法伤害倍率"),Before.Melee.MagicDamage,After.Melee.MagicDamage,2,TEXT("×"),false,(M.MagicDamage-1.)*100.);
        if(M.RuneIntelligence>0.||M.RuneWisdom>0.)
            AddEffect(FString::Printf(TEXT("侵蚀附伤｜战锤攻击附加智力×%.0f%%＋精神×%.0f%%的魔法伤害，随本次攻击倍率结算。"),M.RuneIntelligence*100.,M.RuneWisdom*100.));
        if(M.RuneVulnerabilitySeconds>0.)
            AddEffect(FString::Printf(TEXT("导魔易伤｜战锤攻击命中后，目标受到的魔法伤害提高%.0f%%，持续%.0f秒；重复命中刷新，不叠加。"),M.RuneVulnerability*100.,M.RuneVulnerabilitySeconds));
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
        AddValue(ColdSteelWeaponText::BasePhysical,Was.Damage.BasePhysical,Now.Damage.BasePhysical,2,TEXT(""),false,Percent(T.Damage));
        AddValue(TEXT("暴击率"),Was.CriticalChanceAdd,Now.CriticalChanceAdd,0,TEXT("%"));
        AddValue(TEXT("韧性伤害倍率"),Was.ToughnessDamage,Now.ToughnessDamage,2,TEXT("×"),false,Percent(T.ToughnessDamage));
        AddValue(ColdSteelWeaponText::AttackSpeedMultiplier,Was.Modifiers.AttackSpeed,Now.Modifiers.AttackSpeed,2,TEXT("×"),false,Percent(T.AttackSpeed));
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
    if(Before.FirearmCriticalDamageBonus!=0.||After.FirearmCriticalDamageBonus!=0.)
        AddValue(ColdSteelWeaponText::CriticalBonus,Before.FirearmCriticalDamageBonus*100.,After.FirearmCriticalDamageBonus*100.,0,TEXT("%"),false,Option->FirearmCriticalDamageBonus*100.);
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
    const double BeforePellet=Gunsmith->PelletSpreadMultiplier(Gunsmith->Definition(),WithoutPart);
    const double AfterPellet=Gunsmith->PelletSpreadMultiplier(Gunsmith->Definition(),Gunsmith->Draft());
    AddValue(ColdSteelWeaponText::PelletSpreadMultiplier,BeforePellet,AfterPellet,2,TEXT("×"),true,Ratio(BeforePellet,AfterPellet));
    AddValue(ColdSteelWeaponText::EffectiveRange,Before.Range,After.Range,0,TEXT(" m"),false,Ratio(Before.Range,After.Range));
    AddValue(ColdSteelWeaponText::ProjectileSpeed,Before.Speed,After.Speed,0,TEXT(" m/s"),false,Ratio(Before.Speed,After.Speed));
    }
    else if(Item&&!ColdSteelInventory::IsTwoHandedBlunt(*Item))
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
        if(!FMath::IsNearlyEqual(M.PhysicalAttackMultiplier,1.f))
            AddValue(TEXT("物理攻击力"),Was.PhysicalAttack,Now.PhysicalAttack,2,TEXT(""),false,Percent(M.PhysicalAttackMultiplier));
        if(!FMath::IsNearlyEqual(M.PhysicalDamage,1.))
            AddValue(TEXT("物理伤害"),Was.DamageParts.BasePhysical+Was.DamageParts.AddedPhysical,Now.DamageParts.BasePhysical+Now.DamageParts.AddedPhysical,2,TEXT(""),false,Percent(M.PhysicalDamage));
        if(!FMath::IsNearlyEqual(M.Damage,1.))AddValue(ColdSteelWeaponText::BasePhysical,Was.DamageParts.BasePhysical,Now.DamageParts.BasePhysical,2,TEXT(""),false,Percent(M.Damage*M.AllAttackDamage));
        AddValue(TEXT("全部近战攻击伤害倍率"),Was.Modifiers.AllAttackDamage,Now.Modifiers.AllAttackDamage,2,TEXT("×"),false,Percent(M.AllAttackDamage));
        AddAttackSpeed(Was.AttackSpeedMultiplier(*Item),Now.AttackSpeedMultiplier(*Item),M.AttackSpeed);
        if(!FMath::IsNearlyEqual(M.AttackSpeed,1.))
            ModificationList->AddSlot().AutoHeight().Padding(8,0,8,6)
                [Paragraph(TEXT("倍率以本武器原厂间隔为基准；1.00×表示无攻速加成。"),12,GunsmithUI::Muted)];
        const bool ShowSwing=Item->Definition==PojunGrip::Weapon&&
            (WithoutPart.FindRef(TEXT("grip"))==PojunGrip::Part||Gunsmith->Draft().FindRef(TEXT("grip"))==PojunGrip::Part);
        AddValue(ShowSwing?TEXT("普通攻击距离"):ColdSteelWeaponText::AttackDistance,
            (ShowSwing?Was.SlashReach:Was.ThrustReach)/100,(ShowSwing?Now.SlashReach:Now.ThrustReach)/100,2,TEXT(" m"),false,Percent(M.Range));
        AddValue(ColdSteelWeaponText::StaminaCost,Was.AttackStamina,Now.AttackStamina,2,TEXT(""),true,Percent(M.Stamina));
        if(M.KillStaminaMaxRatio>0.)AddEffect(FString::Printf(TEXT("击杀恢复｜装备本武器期间，你每击杀一个目标，恢复最大体力的%.0f%%；双持时两把武器分别结算。"),M.KillStaminaMaxRatio*100.));
        AddValue(ColdSteelWeaponText::CriticalChance,Was.Modifiers.CriticalChanceAdd+Was.Modifiers.MeleeCriticalChanceAdd,
            Now.Modifiers.CriticalChanceAdd+Now.Modifiers.MeleeCriticalChanceAdd,0,TEXT("%"),false,M.CriticalChanceAdd+M.MeleeCriticalChanceAdd);
        AddValue(TEXT("暴击伤害"),Was.Modifiers.MeleeCriticalDamageBonus*100.,Now.Modifiers.MeleeCriticalDamageBonus*100.,
            0,TEXT("%"),false,M.MeleeCriticalDamageBonus*100.);
        if(Profile&&!FMath::IsNearlyEqual(M.PhysicalDefenseMultiplier,1.))
        {
            const double BaseDefense=Profile->Derived(TEXT("def"))/ColdSteelMelee::EquippedModifiers(Profile).PhysicalDefenseMultiplier;
            AddValue(TEXT("防御力"),BaseDefense*Was.Modifiers.PhysicalDefenseMultiplier,
                BaseDefense*Now.Modifiers.PhysicalDefenseMultiplier,2,TEXT(""),false,Percent(M.PhysicalDefenseMultiplier));
        }
        AddValue(ColdSteelWeaponText::BlockStaminaCost,Was.BlockStamina,Now.BlockStamina,2,TEXT(""),true,Percent(M.BlockStamina));
        AddValue(TEXT("格挡伤害减免"),Was.BlockReduction*100,Now.BlockReduction*100,1,TEXT("%"),false,Percent(M.BlockReduction));
        AddValue(TEXT("所受伤害倍率（乘法叠加）"),Was.Modifiers.DamageTaken,Now.Modifiers.DamageTaken,2,TEXT("×"),true,Percent(M.DamageTaken));
        AddValue(TEXT("闪避体力消耗倍率"),Was.Modifiers.DodgeStamina,Now.Modifiers.DodgeStamina,2,TEXT("×"),true,Percent(M.DodgeStamina));
        AddValue(TEXT("奔跑体力消耗倍率"),Was.Modifiers.SprintStamina,Now.Modifiers.SprintStamina,2,TEXT("×"),true,Percent(M.SprintStamina));
        if(M.DragonSeconds>0.)
        {
            AddEffect(FString::Printf(TEXT("玄龙｜成功弹反后，获得%.0f秒强化，冷却%.0f秒。下一次剑刃命中伤害%+.0f%%，额外造成%.0f基础韧性伤害。"),M.DragonSeconds,M.DragonCooldown,Percent(M.DragonDamage),M.DragonToughness));
            AddEffect(TEXT("消耗规则｜最多保留一次；首次命中即消耗，挥空不消耗。快速近战、裂空斩和持续伤害不触发；超时、换武器或死亡清除。"));
        }
        if(M.PhoenixSeconds>0.)
        {
            AddEffect(FString::Printf(TEXT("凤舞｜闪避中实际躲过敌方攻击后触发，持续%.0f秒，攻击速度%+.0f%%；冷却%.0f秒。空闪避不触发。"),M.PhoenixSeconds,Percent(M.PhoenixSpeed),M.PhoenixCooldown));
            AddEffect(FString::Printf(TEXT("回复规则｜前%.0f次剑刃命中各恢复最大生命的%.0f%%，每次出手只回复一次。快速近战、裂空斩及持续伤害不触发；切换武器清除凤舞，冷却不重置。"),M.PhoenixHealHits,M.PhoenixHealRatio*100.));
        }
        AddValue(TEXT("命中硬直时间倍率"),Was.Modifiers.HitReaction,Now.Modifiers.HitReaction,2,TEXT("×"),false,Percent(M.HitReaction));
        AddValue(ColdSteelWeaponText::ToughnessMultiplier,Was.Modifiers.ToughnessDamage,Now.Modifiers.ToughnessDamage,2,TEXT("×"),false,Percent(M.ToughnessDamage));
        AddValue(TEXT("改造物理防御穿透"),Was.Modifiers.PhysicalArmorPenetration*100,Now.Modifiers.PhysicalArmorPenetration*100,0,TEXT("%"));
        if(!FMath::IsNearlyEqual(M.HeavyDamage,1.)||!FMath::IsNearlyZero(M.HeavyDamageAdd))
            AddValue(TEXT("重击伤害倍率"),Was.HeavyMultiplier,Now.HeavyMultiplier,2,TEXT("×"),false,Ratio(Was.HeavyMultiplier,Now.HeavyMultiplier));
        AddValue(TEXT("重击蓄力速度加成"),Was.HeavyChargeSpeedBonus*100.,Now.HeavyChargeSpeedBonus*100.,0,TEXT("%"),false,M.HeavyChargeSpeedBonus*100.);
        if(!FMath::IsNearlyEqual(M.HeavyToughness,1.))AddValue(TEXT("重击韧性伤害倍率"),Was.Modifiers.HeavyToughnessMultiplier(),Now.Modifiers.HeavyToughnessMultiplier(),2,TEXT("×"),false,Percent(M.HeavyToughness));
        AddValue(TEXT("攻击击退距离"),Was.KnockbackCM,Now.KnockbackCM,1,TEXT(" cm"),false,Percent(M.Knockback*M.AllAttackKnockback));
        AddValue(TEXT("全部攻击击退倍率"),Was.Modifiers.AllAttackKnockback,Now.Modifiers.AllAttackKnockback,2,TEXT("×"),false,Percent(M.AllAttackKnockback));
        if(!FMath::IsNearlyZero(M.QuickCombatDamageAdd))AddValue(TEXT("快速近战伤害倍率"),Was.QuickCombat.DamageMultiplier,Now.QuickCombat.DamageMultiplier,2,TEXT("×"),false,M.QuickCombatDamageAdd*100.);
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
        AddValue(TEXT("所有技能冷却倍率"),Was.Modifiers.SkillCooldown,Now.Modifiers.SkillCooldown,2,TEXT("×"),true,Percent(M.SkillCooldown));
        if(!FMath::IsNearlyEqual(M.MartialCooldown,1.))AddValue(TEXT("武技冷却倍率"),Was.Modifiers.MartialCooldownMultiplier(),Now.Modifiers.MartialCooldownMultiplier(),2,TEXT("×"),true,Percent(M.MartialCooldown));
        AddValue(TEXT("武技伤害倍率"),Was.Modifiers.MartialDamage,Now.Modifiers.MartialDamage,2,TEXT("×"),false,Percent(M.MartialDamage));
        AddValue(TEXT("武技判定范围倍率"),Was.Modifiers.MartialRange,Now.Modifiers.MartialRange,2,TEXT("×"),false,Percent(M.MartialRange));
        AddValue(TEXT("魔法技能冷却倍率"),Was.Modifiers.MagicCooldown,Now.Modifiers.MagicCooldown,2,TEXT("×"),true,Percent(M.MagicCooldown));
        AddValue(TEXT("G飞剑冷却倍率"),Was.Modifiers.RuneBladeCooldown,Now.Modifiers.RuneBladeCooldown,2,TEXT("×"),true,Percent(M.RuneBladeCooldown));
        AddValue(TEXT("魔法值消耗倍率"),Was.Modifiers.MagicCost,Now.Modifiers.MagicCost,2,TEXT("×"),true,Percent(M.MagicCost));
        AddValue(TEXT("魔法攻击倍率"),Was.Modifiers.MagicAttack,Now.Modifiers.MagicAttack,2,TEXT("×"),false,Percent(M.MagicAttack));
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
    // Mechanics are explicitly authored in special_effects for every catalog.
    // Legacy attribute summaries must not become a second set of numeric cards.
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
    if(!bHammerDetail)
    {
        ModificationList->AddSlot().AutoHeight().Padding(0,10,0,6)[Paragraph(TEXT("配件说明"),12,GunsmithUI::Muted)];
        ModificationList->AddSlot().AutoHeight()
            [Paragraph(Option->Description.IsEmpty()?TEXT("暂无额外说明。"):Option->Description,14,GunsmithUI::Secondary)];
    }
    if(IsStaffWorkbench())ModificationList->AddSlot().AutoHeight().Padding(0,10,0,0)
        [Paragraph(TEXT("改造免费；应用并保存后写入当前法杖。杖冠只在匹配杖头专精时激活，不匹配时保留外观。法杖占用主手，可搭配副手手枪。"),12,GunsmithUI::Muted)];
}
