#include "M4GunsmithWidget.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "Engine/GameInstance.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

bool UM4GunsmithWidget::IsCategoryAvailable(const FString& SlotKey) const
{
    const auto* Weapon = Model()->Weapon(Model()->Definition());
    const auto* Options = Weapon ? Weapon->Options.Find(SlotKey) : nullptr;
    return Weapon && Weapon->Allowed.Contains(SlotKey) && Options &&
        Options->ContainsByPredicate([](const FGunsmithOption& Option){return Option.Id != TEXT("false");});
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

    auto WithoutPart = Gunsmith->Draft();
    WithoutPart.Remove(SelectedCategory);
    const auto Before = Gunsmith->Calculate(Gunsmith->Definition(),WithoutPart);
    const auto After = Gunsmith->Calculate(Gunsmith->Definition(),Gunsmith->Draft());
    int32 RowCount = 0;
    auto AddValue = [&](const TCHAR* Name,double Base,double Final,int32 Digits,const TCHAR* Unit,bool Lower=false)
    {
        const double Delta = Final-Base;
        if (FMath::Abs(Delta) < .00001) return;
        if (RowCount++ == 0)
            ModificationList->AddSlot().AutoHeight().Padding(0,0,0,8)
                [Paragraph(TEXT("当前组合实值 · 差值相对该栏原厂配置"),12,GunsmithUI::Muted)];
        const auto Color = ((Delta>0)!=Lower) ? ColdSteelUI::Success : ColdSteelUI::Danger;
        const FString PercentText=FMath::IsNearlyZero(Percent,.01)?FString():FString::Printf(TEXT("（%+.0f%%）"),Percent);
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
