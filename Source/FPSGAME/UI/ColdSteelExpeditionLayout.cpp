#include "ColdSteelExpeditionWidget.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"

namespace
{
    // Decorative portal engraving, deliberately not presented as a dungeon map or screenshot.
    class SExpeditionPortal : public SLeafWidget
    {
    public:
        SLATE_BEGIN_ARGS(SExpeditionPortal) {} SLATE_END_ARGS()
        void Construct(const FArguments&) { SetVisibility(EVisibility::HitTestInvisible); }
        virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(280, 130); }
        virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
            FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle&, bool) const override
        {
            const FVector2D Size = Geometry.GetLocalSize();
            const float Center = Size.X * .79f, Top = 12.f, Bottom = Size.Y - 12.f;
            const float HalfWidth = FMath::Min(Size.X * .17f, 100.f);
            for (int32 Index = 0; Index < 5; ++Index)
            {
                const float Inset = Index * 8.f;
                TArray<FVector2D> Points = {
                    FVector2D(Center - HalfWidth + Inset, Bottom), FVector2D(Center - HalfWidth + Inset, Top + Inset),
                    FVector2D(Center + HalfWidth - Inset, Top + Inset), FVector2D(Center + HalfWidth - Inset, Bottom)};
                FSlateDrawElement::MakeLines(Elements, Layer, Geometry.ToPaintGeometry(), Points,
                    ESlateDrawEffect::None, ColdSteelUI::Gray(184, 42 - Index * 5), true, 1.f);
            }
            return Layer;
        }
    };
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Label(const FString& Text, int32 Size, FLinearColor Color, bool Numeric) const
{
    return SNew(STextBlock).Text(FText::FromString(Text))
        .Font(Numeric ? ColdSteelUI::NumberFont(Size * .75f) : ColdSteelUI::TextFont(Size * .75f, Size >= 16))
        .ColorAndOpacity(Color).AutoWrapText(true);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Card(TSharedRef<SWidget> Content, float Inset)
{
    return SNew(SBorder).BorderImage(&CardBrush).Padding(Inset)[Content];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::Row(const FString& Name, const FString& Value, bool Numeric) const
{
    return SNew(SHorizontalBox)
        +SHorizontalBox::Slot().FillWidth(.4f).Padding(0, 7, 12, 7)[Label(Name, 12, ColdSteelUI::TextTertiary)]
        +SHorizontalBox::Slot().FillWidth(.6f).Padding(0, 7)[Label(Value, 14, ColdSteelUI::TextPrimary, Numeric)];
}

TSharedRef<SButton> UColdSteelExpeditionWidget::Action(const FString& Text, TFunction<void()> Callback, bool Primary)
{
    return SNew(SButton).ButtonStyle(Primary ? &PrimaryStyle : &NormalStyle)
        .ContentPadding(FMargin(12, 0)).HAlign(HAlign_Fill).VAlign(VAlign_Center)
        .OnClicked_Lambda([Callback]() { Callback(); return FReply::Handled(); })
        [SNew(SBox).MinDesiredHeight(ColdSteelUI::ActionHeight).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(Text)).Font(ColdSteelUI::TextFont(10.5f, true))
                .ColorAndOpacity(Primary ? ColdSteelUI::Gray(22) : ColdSteelUI::TextPrimary).Justification(ETextJustify::Center)]];
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildCatalog()
{
    auto Filters = SNew(SHorizontalBox);
    for (int32 Index = 0; Index < 2; ++Index)
    {
        TSharedPtr<SButton> Button;
        Filters->AddSlot().FillWidth(1).Padding(Index ? 2 : 0, 0, Index ? 0 : 2, 0)
            [SAssignNew(Button, SButton).ButtonStyle(&NormalStyle)
                .ContentPadding(FMargin(8, 0)).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked_Lambda([this, Index]() { bAvailableOnly = Index == 1; RefreshList(); return FReply::Handled(); })
                [SNew(SBox).MinDesiredHeight(36).VAlign(VAlign_Center)[Label(Index ? TEXT("可出征") : TEXT("全部"), 14, ColdSteelUI::TextPrimary)]]];
        FilterButtons.Add(Button);
    }
    return Card(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("目的地"), 16, ColdSteelUI::TextPrimary)]
                +SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text_Lambda([this]() { return FText::AsNumber(VisibleIds.Num()); })
                    .Font(ColdSteelUI::NumberFont(10.5f)).ColorAndOpacity(ColdSteelUI::TextTertiary)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(SBox).MinDesiredHeight(36)
                [SAssignNew(Search, SEditableTextBox).Style(&SearchStyle).Text(FText::FromString(Query))
                    .HintText(FText::FromString(TEXT("搜索目的地 / 类型")))
                    .OnTextChanged_Lambda([this](const FText& Text) { Query = Text.ToString().TrimStartAndEnd(); RefreshList(); })]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[Filters]
        +SVerticalBox::Slot().FillHeight(1)
            [SNew(SScrollBox).ScrollBarThickness(FVector2D(6, 6)).AllowOverscroll(EAllowOverscroll::No)
                +SScrollBox::Slot()[SAssignNew(CatalogRows, SVerticalBox)]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 0)[Label(TEXT("选择目的地以查看详细情报"), 12, ColdSteelUI::TextTertiary)]);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildDetail()
{
    auto Tabs = SNew(SHorizontalBox);
    const TCHAR* Titles[] = { TEXT("概览"), TEXT("奖励"), TEXT("规则") };
    for (int32 Index = 0; Index < 3; ++Index)
    {
        TSharedPtr<SButton> Button;
        Tabs->AddSlot().FillWidth(1).Padding(0, 0, Index < 2 ? 4 : 0, 0)
            [SAssignNew(Button, SButton).ButtonStyle(&NormalStyle)
                .HAlign(HAlign_Center).ContentPadding(FMargin(8, 0)).VAlign(VAlign_Center)
                .OnClicked_Lambda([this, Index]() { DetailTab = Index; RefreshDetail(); if (DetailScroll) DetailScroll->ScrollToStart(); return FReply::Handled(); })
                [SNew(SBox).MinDesiredHeight(36).VAlign(VAlign_Center)[Label(Titles[Index], 14, ColdSteelUI::TextPrimary)]]];
        DetailButtons.Add(Button);
    }
    return Card(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
            [SNew(SBorder).BorderImage(&HeroBrush).Padding(0)
                [SNew(SBox).MinDesiredHeight(132)
                    [SNew(SOverlay)
                        +SOverlay::Slot()[SNew(SExpeditionPortal)]
                        +SOverlay::Slot().Padding(16).VAlign(VAlign_Center)
                            [SNew(SVerticalBox)
                                +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)[Label(TEXT("任务情报"), 12, ColdSteelUI::TextTertiary)]
                                +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock)
                                    .Text_Lambda([this]() { return FText::FromString(Selection() ? Selection()->Name : TEXT("等待选择")); })
                                    .Font(ColdSteelUI::TextFont(15, true)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(true)]
                                +SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)[SNew(STextBlock)
                                    .Text_Lambda([this]() { return FText::FromString(Selection() ? Selection()->Category : TEXT("目的地档案")); })
                                    .Font(ColdSteelUI::TextFont(9)).ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]]]]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 16)[Tabs]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(DetailScroll, SScrollBox).ScrollBarThickness(FVector2D(6, 6))
            .AllowOverscroll(EAllowOverscroll::No)+SScrollBox::Slot()[SAssignNew(DetailRows, SVerticalBox)]]);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::BuildPreparation()
{
    return Card(SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[Label(TEXT("行前准备"), 16, ColdSteelUI::TextPrimary)]
        +SVerticalBox::Slot().FillHeight(1)[SNew(SScrollBox).ScrollBarThickness(FVector2D(6, 6))
            .AllowOverscroll(EAllowOverscroll::No)+SScrollBox::Slot()[SAssignNew(PreparationRows, SVerticalBox)]]);
}

TSharedRef<SWidget> UColdSteelExpeditionWidget::RebuildWidget()
{
    SetIsFocusable(true);
    LayoutMode = -1;
    PanelBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint, ColdSteelUI::PanelRadius);
    FallbackBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback, ColdSteelUI::PanelRadius);
    CardBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::Content, ColdSteelUI::CardRadius);
    HeroBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard, ColdSteelUI::CardRadius);
    NormalStyle = ColdSteelUI::ButtonStyle();
    NormalStyle.SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));
    SelectedStyle = NormalStyle;
    SelectedStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, 6, ColdSteelUI::Accent));
    PrimaryStyle = NormalStyle;
    PrimaryStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent, 6));
    PrimaryStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::TextPrimary, 6));
    PrimaryStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(174), 6));
    PrimaryStyle.SetDisabled(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(100), 6));
    SearchStyle = FEditableTextBoxStyle()
        .SetFont(ColdSteelUI::TextFont(10.5f)).SetForegroundColor(ColdSteelUI::TextPrimary)
        .SetBackgroundImageNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 6))
        .SetBackgroundImageHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, 6))
        .SetBackgroundImageFocused(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 6, ColdSteelUI::Accent))
        .SetBackgroundImageReadOnly(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonDisabled, 6))
        .SetPadding(FMargin(10, 7));

    auto CompactTabs = SNew(SHorizontalBox);
    CompactButtons.Reset();
    const TCHAR* Pages[] = { TEXT("目的地"), TEXT("任务情报"), TEXT("行前准备") };
    for (int32 Index = 0; Index < 3; ++Index)
    {
        TSharedPtr<SButton> Button;
        CompactTabs->AddSlot().FillWidth(1).Padding(0, 0, Index < 2 ? 4 : 0, 0)
            [SAssignNew(Button, SButton).ButtonStyle(&NormalStyle)
                .HAlign(HAlign_Center).ContentPadding(FMargin(4, 0)).VAlign(VAlign_Center)
                .OnClicked_Lambda([this, Index]() { CompactPage = Index; LayoutMode = -1; UpdateLayout(); return FReply::Handled(); })
                [SNew(SBox).MinDesiredHeight(36).VAlign(VAlign_Center)[Label(Pages[Index], 14, ColdSteelUI::TextPrimary)]]];
        CompactButtons.Add(Button);
    }
    auto Confirm = Action(TEXT("确认出征"), [this]() { ConfirmDeparture(); }, true);
    Confirm->SetEnabled(TAttribute<bool>::CreateLambda([this]() { return CanConfirm(); }));
    Confirm->SetToolTipText(TAttribute<FText>::CreateLambda([this]() { return BlockMessage(); }));

    auto Content = SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 16)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[Label(TEXT("出征"), 20, ColdSteelUI::TextPrimary)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 5, 12, 0)[Label(TEXT("选择目的地 · 阅读情报 · 整理行装"), 12, ColdSteelUI::TextSecondary)]]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Action(TEXT("Esc  返回"), [this]() { Close(); })]]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
            [SNew(SBox).Visibility_Lambda([this]() { return LayoutMode == 2 ? EVisibility::Visible : EVisibility::Collapsed; })[CompactTabs]]
        +SVerticalBox::Slot().FillHeight(1)[SAssignNew(BodyHost, SBox).Clipping(EWidgetClipping::ClipToBounds)]
        +SVerticalBox::Slot().AutoHeight().Padding(0, 12, 0, 0)
            [Card(SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 0, 16, 0)
                    [SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock)
                            .Text_Lambda([this]() { return FText::FromString(Selection() ? Selection()->Name : TEXT("尚未选择目的地")); })
                            .Font(ColdSteelUI::TextFont(10.5f, true)).ColorAndOpacity(ColdSteelUI::TextPrimary).AutoWrapText(true)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)[SNew(STextBlock)
                            .Text_Lambda([this]() { return BlockMessage(); }).Font(ColdSteelUI::TextFont(9))
                            .ColorAndOpacity(ColdSteelUI::TextSecondary).AutoWrapText(true)]]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).WidthOverride_Lambda([this]() { return LayoutMode == 2 ? 112.f : 180.f; })[Confirm]], 12)];
    UpdateLayout();
    // Cancel UMG's canvas DPI; thresholds and typography use actual available pixels, as the other workbenches do.
    return SNew(SDPIScaler).DPIScale_Lambda([this]() { return 1.f / ColdSteelUI::PixelScale(this); })
        [SNew(SBorder).BorderBackgroundColor(ColdSteelUI::Gray(10, 225)).Padding(12)
            [SNew(SBackgroundBlur).BlurStrength(5).BlurRadius(13).CornerRadius(FVector4(10, 10, 10, 10))
                .LowQualityFallbackBrush(&FallbackBrush).Padding(0)
                [SNew(SBorder).BorderImage(&PanelBrush).Padding(16)[Content]]]];
}

void UColdSteelExpeditionWidget::UpdateLayout()
{
    if (!BodyHost) return;
    const float Width = BodyHost->GetCachedGeometry().GetLocalSize().X;
    const int32 Mode = Width < 100 ? 0 : Width < 900 ? 2 : Width < 1280 ? 1 : 0;
    if (LayoutMode == Mode) return;
    LayoutMode = Mode;
    BodyHost->SetContent(SNullWidget::NullWidget);
    CatalogRows.Reset(); DetailRows.Reset(); PreparationRows.Reset(); Search.Reset(); DetailScroll.Reset();
    CatalogButtons.Reset(); FilterButtons.Reset(); DetailButtons.Reset();
    if (Mode == 0)
        BodyHost->SetContent(SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)[SNew(SBox).WidthOverride(248)[BuildCatalog()]]
            +SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 12, 0)[BuildDetail()]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(300)[BuildPreparation()]]);
    else if (Mode == 1)
        BodyHost->SetContent(SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)[SNew(SBox).WidthOverride(240)[BuildCatalog()]]
            +SHorizontalBox::Slot().FillWidth(1)[SNew(SScrollBox).ScrollBarThickness(FVector2D(6, 6)).AllowOverscroll(EAllowOverscroll::No)
                +SScrollBox::Slot().Padding(0, 0, 0, 12)[SNew(SBox).HeightOverride(480)[BuildDetail()]]
                +SScrollBox::Slot()[SNew(SBox).HeightOverride(430)[BuildPreparation()]]]);
    else
        BodyHost->SetContent(CompactPage == 0 ? BuildCatalog() : CompactPage == 1 ? BuildDetail() : BuildPreparation());
    RefreshList();
    RefreshDetail();
    RefreshPreparation();
}
