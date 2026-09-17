// F6 开发面板「基本调参」页的开发功能卡片：生成物品、提升等级、提升技能等级。
// 布局与背包装备同一抽屉规格，控件只调用档案事务，不自行扣除或保存。
#include "DevelopmentPanelWidget.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/GridPanel.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/SpinBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"

void UDevelopmentPanelWidget::BuildFeatureRows(UVerticalBox* Page)
{
    const float Scale = ColdSteelUI::PixelScale(this);
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("开发功能"), 16, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0, 14.f / Scale, 0, 8.f / Scale));
    FeatureStatus = CreatePanelText(TEXT("生成物品、提升等级与技能等级立即走存档事务。"), 12, ColdSteelUI::TextSecondary);
    Page->AddChildToVerticalBox(FeatureStatus)->SetPadding(FMargin(0, 0, 0, 8.f / Scale));

    struct FCardParts
    {
        FFeatureRow Row;
        UHorizontalBox* Control = nullptr;
        UTextBlock* Help = nullptr;
    };
    const auto NewCard = [this, Page, Scale](const TCHAR* Title, const TCHAR* Help) -> FCardParts
    {
        FCardParts Parts;
        auto* Card = WidgetTree->ConstructWidget<UBorder>(); Parts.Row.Card = Card;
        Page->AddChildToVerticalBox(Card)->SetPadding(FMargin(0, 0, 0, 8.f / Scale));
        auto* Grid = WidgetTree->ConstructWidget<UGridPanel>(); Parts.Row.Grid = Grid;
        Grid->SetColumnFill(0, 1.f); Card->SetContent(Grid);
        auto* Copy = WidgetTree->ConstructWidget<UVerticalBox>(); Parts.Row.Copy = Copy;
        Copy->AddChildToVerticalBox(CreatePanelText(Title, 16, ColdSteelUI::TextPrimary))->SetPadding(FMargin(0, 0, 0, 6.f / Scale));
        Parts.Help = CreatePanelText(Help, 12, ColdSteelUI::TextSecondary);
        Copy->AddChildToVerticalBox(Parts.Help);
        Grid->AddChildToGrid(Copy, 0, 0);
        Parts.Control = WidgetTree->ConstructWidget<UHorizontalBox>(); Parts.Row.Control = Parts.Control;
        Grid->AddChildToGrid(Parts.Control, 0, 1);
        return Parts;
    };
    const auto AddFixed = [this](FCardParts& Parts, UWidget* Widget, float Pixels)
    {
        auto* Size = WidgetTree->ConstructWidget<USizeBox>(); Size->SetContent(Widget);
        Parts.Row.FixedBoxes.Emplace(TWeakObjectPtr<USizeBox>(Size), Pixels);
        Parts.Control->AddChildToHorizontalBox(Size);
    };
    const auto AddFlex = [this](FCardParts& Parts, UWidget* Widget, float Pixels)
    {
        auto* Size = WidgetTree->ConstructWidget<USizeBox>(); Size->SetContent(Widget);
        Parts.Row.FlexBox = Size; Parts.Row.FlexPixels = Pixels;
        Parts.Control->AddChildToHorizontalBox(Size);
    };
    const auto MakeButton = [this](const TCHAR* Caption, const TCHAR* Name)
    {
        auto* Button = CreatePanelButton(Caption, FName(Name));
        if (auto* Label = Cast<UTextBlock>(Button->GetContent()))
        {
            Label->SetAutoWrapText(false);
            if (auto* LabelSlot = Cast<UButtonSlot>(Label->Slot))
            { LabelSlot->SetHorizontalAlignment(HAlign_Center); LabelSlot->SetVerticalAlignment(VAlign_Center); }
        }
        return Button;
    };

    // 生成物品：一个下拉包含全部物品定义，按类别归纳排列；数量与生成按钮在右侧。
    {
        FCardParts Parts = NewCard(TEXT("生成物品"),
            TEXT("下拉包含全部物品定义，按类别归纳排列；生成的物品直接进入背包。"));
        ItemChoice = WidgetTree->ConstructWidget<UComboBoxString>();
        ItemChoice->OnGenerateWidgetEvent.BindDynamic(this, &ThisClass::GenerateListOption);
        ItemChoice->OnSelectionChanged.AddDynamic(this, &ThisClass::ItemSelected);
        AddFlex(Parts, ItemChoice, 320.f);
        ItemCountBox = WidgetTree->ConstructWidget<USpinBox>();
        ItemCountBox->SetMinValue(1); ItemCountBox->SetMaxValue(9999);
        ItemCountBox->SetMinSliderValue(1); ItemCountBox->SetMaxSliderValue(200);
        ItemCountBox->SetDelta(1); ItemCountBox->SetMinFractionalDigits(0); ItemCountBox->SetMaxFractionalDigits(0);
        ItemCountBox->SetValue(1);
        AddFixed(Parts, ItemCountBox, 96.f);
        GenerateItemButton = MakeButton(TEXT("生成"), TEXT("DevelopmentItemGenerate"));
        GenerateItemButton->OnClicked.AddDynamic(this, &ThisClass::GenerateItemClicked);
        AddFixed(Parts, GenerateItemButton, 96.f);
        FeatureRows.Add(Parts.Row);
    }

    // 提升等级：按正常升级发放属性点，说明行显示当前等级与属性点。
    {
        FCardParts Parts = NewCard(TEXT("提升等级"),
            TEXT("按正常升级结算：每级 +3 属性点，经验夹到当前等级门槛以下。"));
        LevelHelp = Parts.Help;
        GrantLevelButton = MakeButton(TEXT("等级 +1"), TEXT("DevelopmentLevelUp"));
        GrantLevelButton->OnClicked.AddDynamic(this, &ThisClass::GrantLevelClicked);
        AddFixed(Parts, GrantLevelButton, 120.f);
        FeatureRows.Add(Parts.Row);
    }

    // 提升技能等级：下拉选择技能，旁边是 +1 级与直接满级。
    {
        FCardParts Parts = NewCard(TEXT("提升技能等级"),
            TEXT("下拉为存档中的全部技能；满级清零修炼值，收益按该技能现有公式生效。"));
        SkillHelp = Parts.Help;
        SkillChoice = WidgetTree->ConstructWidget<UComboBoxString>();
        SkillChoice->OnGenerateWidgetEvent.BindDynamic(this, &ThisClass::GenerateListOption);
        SkillChoice->OnSelectionChanged.AddDynamic(this, &ThisClass::SkillSelected);
        AddFlex(Parts, SkillChoice, 240.f);
        RaiseSkillButton = MakeButton(TEXT("技能 +1"), TEXT("DevelopmentSkillRaise"));
        RaiseSkillButton->OnClicked.AddDynamic(this, &ThisClass::RaiseSkillClicked);
        AddFixed(Parts, RaiseSkillButton, 110.f);
        MaxSkillButton = MakeButton(TEXT("提升至满级"), TEXT("DevelopmentSkillMax"));
        MaxSkillButton->OnClicked.AddDynamic(this, &ThisClass::MaxSkillClicked);
        AddFixed(Parts, MaxSkillButton, 120.f);
        FeatureRows.Add(Parts.Row);
    }
}

void UDevelopmentPanelWidget::UpdateFeatureLayout(float ContentWidth, float Scale)
{
    const bool bStack = ContentWidth < 620.f;
    const float Gap = 8.f / Scale;
    for (auto& Row : FeatureRows)
    {
        if (auto* Card = Row.Card.Get())
        {
            Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius / Scale));
            Card->SetPadding(FMargin(12.f / Scale));
            if (auto* CardSlot = Cast<UVerticalBoxSlot>(Card->Slot)) CardSlot->SetPadding(FMargin(0, 0, 0, 8.f / Scale));
        }
        if (auto* Copy = Row.Copy.Get())
            if (auto* CopySlot = Cast<UGridSlot>(Copy->Slot))
            {
                CopySlot->SetColumnSpan(bStack ? 2 : 1);
                CopySlot->SetPadding(FMargin(0, 0, bStack ? 0 : 12.f / Scale, 0));
            }
        if (auto* Control = Cast<UHorizontalBox>(Row.Control.Get()))
        {
            if (auto* ControlSlot = Cast<UGridSlot>(Control->Slot))
            {
                ControlSlot->SetRow(bStack ? 1 : 0); ControlSlot->SetColumn(bStack ? 0 : 1);
                ControlSlot->SetColumnSpan(bStack ? 2 : 1);
                ControlSlot->SetHorizontalAlignment(bStack ? HAlign_Fill : HAlign_Right);
                ControlSlot->SetVerticalAlignment(VAlign_Center);
                ControlSlot->SetPadding(FMargin(0, bStack ? 10.f / Scale : 0, 0, 0));
            }
            const int32 Children = Control->GetChildrenCount();
            for (int32 N = 0; N < Children; ++N)
                if (auto* ChildSlot = Cast<UHorizontalBoxSlot>(Control->GetChildAt(N)->Slot))
                {
                    ChildSlot->SetVerticalAlignment(VAlign_Center);
                    ChildSlot->SetPadding(FMargin(0, 0, N < Children - 1 ? Gap : 0.f, 0));
                }
            float FixedTotal = 0.f;
            for (const auto& Pair : Row.FixedBoxes) FixedTotal += Pair.Value;
            if (auto* Flex = Row.FlexBox.Get())
            {
                const float Width = bStack
                    ? FMath::Max(160.f, ContentWidth - 24.f - FixedTotal - 8.f * FMath::Max(0, Children - 1))
                    : Row.FlexPixels;
                Flex->SetWidthOverride(Width / Scale);
                Flex->SetHeightOverride(ColdSteelUI::ActionHeight / Scale);
            }
            for (const auto& Pair : Row.FixedBoxes)
                if (auto* Size = Pair.Key.Get())
                {
                    Size->SetWidthOverride(Pair.Value / Scale);
                    Size->SetHeightOverride(ColdSteelUI::ActionHeight / Scale);
                }
        }
    }
}
