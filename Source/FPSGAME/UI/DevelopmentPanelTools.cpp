// F6 开发面板「基本调参」页的开发功能卡片：生成物品、提升等级、提升技能等级。
// 布局与背包装备同一抽屉规格，控件只调用档案事务，不自行扣除或保存。
#include "DevelopmentPanelWidget.h"
#include "DevelopmentItemPicker.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../Tasks/CarpenterApprenticeship.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "ColdSteelUIStyle.h"
#include "Engine/World.h"
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

namespace
{
struct FDevelopmentQuestLine
{
    const TCHAR* Id;
    const TCHAR* Teacher;
    const TCHAR* Name;
    bool (*Reset)(FColdSteelProfile&);
};

constexpr FDevelopmentQuestLine ResettableQuests[] = {
    {BlacksmithApprenticeship::TaskId, TEXT("铁匠"), TEXT("采矿、冶炼与打铁"), BlacksmithApprenticeship::Reset},
    {CarpenterApprenticeship::TaskId, TEXT("木匠"), TEXT("木工修炼"), CarpenterApprenticeship::Reset}
};
}

void UDevelopmentPanelWidget::BuildFeatureRows(UVerticalBox* Page)
{
    const float Scale = ColdSteelUI::PixelScale(this);
    Page->AddChildToVerticalBox(CreatePanelText(TEXT("开发功能"), 16, ColdSteelUI::TextPrimary))
        ->SetPadding(FMargin(0, 14.f / Scale, 0, 8.f / Scale));
    FeatureStatus = CreatePanelText(TEXT("物品、等级与技能等级按原规则保存；快进时间只推世界时钟。"), 12, ColdSteelUI::TextSecondary);
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

    // 生成物品：独立类别／子类标题与分隔线，只有实际物品行可以选择。
    {
        FCardParts Parts = NewCard(TEXT("生成物品"),
            TEXT("物品直接进入背包；武器可装备，弹药按对应口径使用。"));
        ItemChoice = WidgetTree->ConstructWidget<UDevelopmentItemPicker>();
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

    {
        TArray<FColdSteelCatalogEntry> Options;
        TArray<FString> Names;
        for (const auto& Quest : ResettableQuests)
        {
            auto& Entry = Options.AddDefaulted_GetRef();
            Entry.Definition = Quest.Id;
            Entry.Group = Quest.Teacher;
            Entry.Name = Quest.Name;
            Names.Add(Entry.Name);
        }
        const FString Help = FString::Printf(TEXT("共 %d 条任务线，可重置 %d 条：%s。%s\n地牢探险（全队共享） · 进度随本局地牢单独记录。"),
            Options.Num() + 1, Options.Num(), *FString::Join(Names, TEXT("、")), GetWorld() && GetWorld()->GetNetMode() == NM_Client
                ? TEXT("重置仅对房主自己的角色开放。") : TEXT("重置后可找对应 NPC 重新领取。"));
        FCardParts Parts = NewCard(TEXT("重置任务线"), *Help);
        QuestChoice = WidgetTree->ConstructWidget<UDevelopmentItemPicker>();
        SelectedQuestId = Options[0].Definition;
        QuestChoice->SetOptions(Options, SelectedQuestId);
        QuestChoice->OnSelectionChanged.AddDynamic(this, &ThisClass::QuestSelected);
        AddFlex(Parts, QuestChoice, 200.f);
        ResetQuestButton = MakeButton(TEXT("重置"), TEXT("DevelopmentResetQuestLine"));
        ResetQuestButton->OnClicked.AddDynamic(this, &ThisClass::ResetQuestClicked);
        AddFixed(Parts, ResetQuestButton, 96.f);
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

    // 专精重置（2026-11-15）：重置代价留待后续开发，现阶段只在开发面板返还专精点。
    {
        FCardParts Parts = NewCard(TEXT("专精重置"),
            TEXT("返还上方所选技能（或全部技能）已投入的专精点；技能等级与修炼值不变，结果写入角色档案。"));
        ResetSpecButton = MakeButton(TEXT("重置该技能专精"), TEXT("DevelopmentSpecReset"));
        ResetSpecButton->OnClicked.AddDynamic(this, &ThisClass::ResetSkillSpecClicked);
        AddFixed(Parts, ResetSpecButton, 150.f);
        ResetAllSpecsButton = MakeButton(TEXT("重置全部专精"), TEXT("DevelopmentSpecResetAll"));
        ResetAllSpecsButton->OnClicked.AddDynamic(this, &ThisClass::ResetAllSpecsClicked);
        AddFixed(Parts, ResetAllSpecsButton, 140.f);
        FeatureRows.Add(Parts.Row);
    }

    // 快进时间：世界时钟整体前推 1 小时，用来快速走到黄昏/夜晚核对点火、光照与天气。
    {
        FCardParts Parts = NewCard(TEXT("快进时间"),
            TEXT("把世界时钟整体前推 1 小时，可反复点击；到达黄昏/夜晚看火把自动点火。"));
        TimeHelp = Parts.Help;
        AdvanceHourButton = MakeButton(TEXT("快进 1 小时"), TEXT("DevelopmentAdvanceHour"));
        AdvanceHourButton->OnClicked.AddDynamic(this, &ThisClass::AdvanceHourClicked);
        AddFixed(Parts, AdvanceHourButton, 130.f);
        FeatureRows.Add(Parts.Row);
    }

    {
        FCardParts Parts = NewCard(TEXT("村庄建设"), GetWorld() && GetWorld()->GetNetMode() == NM_Client
            ? TEXT("当前丘陵世界的村庄升级由房主重置。")
            : TEXT("将当前丘陵世界的围墙和所有已修复的建筑恢复为破败形态，并保存建设进度。"));
        VillageResetHelp = Parts.Help;
        ResetVillageButton = MakeButton(TEXT("重置村庄升级"), TEXT("DevelopmentResetVillageUpgrades"));
        ResetVillageButton->OnClicked.AddDynamic(this, &ThisClass::ResetVillageUpgradesClicked);
        AddFixed(Parts, ResetVillageButton, 150.f);
        FeatureRows.Add(Parts.Row);
    }
}

void UDevelopmentPanelWidget::QuestSelected(const FString& Definition)
{
    SelectedQuestId = Definition;
}

void UDevelopmentPanelWidget::ResetQuestClicked()
{
    auto* Model = ResolveModel();
    const auto* Player = GetOwningPlayer();
    if (!Model || !Player || !Player->HasAuthority() || !Player->IsLocalController() ||
        !Model->RuntimePawn() || Model->RuntimePawn() != Player->GetPawn() || Model->IsStagingNetworkContainer())
    {
        SetFeatureMessage(TEXT("请在单机或房主角色档案就绪后重置任务。"), ColdSteelUI::Warning);
        return;
    }

    for (const auto& Quest : ResettableQuests)
    {
        if (SelectedQuestId != Quest.Id) continue;
        Model->SyncRuntime();
        auto Next = Model->Snapshot();
        if (!Quest.Reset(Next))
        {
            SetFeatureMessage(FString::Printf(TEXT("「%s」尚未领取，可直接找%s接取。"), Quest.Name, Quest.Teacher), ColdSteelUI::TextSecondary);
            return;
        }
        if (Model->CommitCampfireState(MoveTemp(Next), SelectedQuestId + TEXT(".reset")))
            SetFeatureMessage(FString::Printf(TEXT("已重置「%s」，可找%s重新领取。"), Quest.Name, Quest.Teacher), ColdSteelUI::Success);
        else
            SetFeatureMessage(FString::Printf(TEXT("任务重置保存失败：%s"), *Model->ResultMessage()), ColdSteelUI::Warning);
        return;
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
