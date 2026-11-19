#include "ColdSteelTreePanel.h"
#include "ColdSteelUIStyle.h"
#include "SColdSteelSkillTreeCanvas.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBackgroundBlur.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace ColdSteelTreePanel
{
using namespace ColdSteelUI;
void FStyle::Initialize()
{
    GlassBrush = RoundedBrush(GlassTint, PanelRadius, Border, 1);
    FallbackBrush = RoundedBrush(GlassFallback, PanelRadius);
    BarBrush = RoundedBrush(FLinearColor(0, 0, 0, .5f), 2, FLinearColor::Transparent, 0);
    CardBrush = RoundedBrush(StatusCard, CardRadius, Border, 1);
    RowBrush = RoundedBrush(Gray(200, 9), ButtonRadius, Gray(222, 20), 1);
    RowMetBrush = RoundedBrush(Gray(200, 9), ButtonRadius, FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, .3f), 1);
    ChipBrush = RoundedBrush(FLinearColor::Transparent, 4, Border, 1);
    GlyphBrush = RoundedBrush(Gray(26), 14, Gray(169), 2);
    TabLine = RoundedBrush(Accent, 1, FLinearColor::Transparent, 0);
    Quiet = ButtonStyle(); Muted = ButtonStyle(); Primary = ButtonStyle();
    Quiet.Normal = RoundedBrush(FLinearColor::Transparent, ButtonRadius, FLinearColor::Transparent, 0);
    Quiet.Hovered = RoundedBrush(ButtonHover, ButtonRadius, FLinearColor::Transparent, 0);
    Quiet.Pressed = RoundedBrush(ButtonPressed, ButtonRadius, FLinearColor::Transparent, 0);
    Primary.Normal = RoundedBrush(Accent, ButtonRadius, Accent, 1);
    Primary.Hovered = RoundedBrush(Gray(237), ButtonRadius, Gray(237), 1);
    Primary.Pressed = RoundedBrush(Gray(190), ButtonRadius, Gray(190), 1);
    Primary.Disabled = RoundedBrush(ButtonDisabled, ButtonRadius, Gray(222, 20), 1);
}
float DetailWidth(const UUserWidget* Owner)
{
    const FVector2D View = UWidgetLayoutLibrary::GetViewportSize(Owner);
    return FMath::RoundToFloat(FMath::Clamp((View.X > 100 ? float(View.X) : 1920.f) * .4f, 480.f, 760.f));
}
TSharedRef<SWidget> Label(const FString& Text, float Px, const FLinearColor& Color, bool Medium, bool Wrap)
{
    return SNew(STextBlock).Text(FText::FromString(Text)).Font(TextFont(Px * .75f, Medium)).ColorAndOpacity(Color).AutoWrapText(Wrap).LineHeightPercentage(Wrap ? 1.3f : 1.f);
}
TSharedRef<SWidget> Section(const FString& Title, const FString& Count, TSharedRef<SWidget> Body)
{
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1)[Label(Title, 12, HUDGold, true)]
            + SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(Count)).Font(NumberFont(11 * .75f)).ColorAndOpacity(TextTertiary)]]
        + SVerticalBox::Slot().AutoHeight()[Body];
}
TSharedRef<SWidget> Frame(UUserWidget* Owner, const FStyle& Style, TSharedRef<SWidget> Header, TSharedRef<SWidget> Main, TSharedRef<SWidget> Detail)
{
    const TWeakObjectPtr<UUserWidget> WeakOwner(Owner);
    return SNew(SDPIScaler).DPIScale_Lambda([WeakOwner] { return 1.f / FMath::Max(.1f, PixelScale(WeakOwner.Get())); })
    [SNew(SOverlay)
        + SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(8, 200))]
        + SOverlay::Slot().Padding(12)
        [SNew(SBackgroundBlur).BlurStrength(GlassBlurStrength).BlurRadius(GlassBlurRadius).CornerRadius(FVector4(PanelRadius)).LowQualityFallbackBrush(&Style.FallbackBrush)
            [SNew(SBorder).BorderImage(&Style.GlassBrush).Padding(0)
                [SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[Header]
                    + SVerticalBox::Slot().FillHeight(1)[SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1)[Main]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(22, 250)).Padding(FMargin(1, 0, 0, 0))
                            [SNew(SBox).WidthOverride_Lambda([WeakOwner] { return FOptionalSize(DetailWidth(WeakOwner.Get())); })[Detail]]]]]]]];
}
TSharedRef<SWidget> Tabs(const FStyle& Style, const TArray<FTab>& Items, TAttribute<FName> Selected, TAttribute<bool> ShowLine, TFunction<void(FName)> OnSelect)
{
    auto Row = SNew(SHorizontalBox);
    for(const FTab& Tab : Items)
    {
        const FName Id = Tab.Id;
        Row->AddSlot().AutoWidth().Padding(1, 0)
        [SNew(SButton).ButtonStyle(&Style.Quiet).ContentPadding(FMargin(14, 0)).OnClicked_Lambda([OnSelect, Id] { OnSelect(Id); return FReply::Handled(); })
            [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)
                [SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Tab.Caption)).Font_Lambda([Selected, Id] { return TextFont(14 * .75f, Selected.Get() == Id); })
                        .ColorAndOpacity_Lambda([Selected, Id] { return FSlateColor(Selected.Get() == Id ? TextPrimary : TextSecondary); })]
                    + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 4, 0, 0)[SNew(SBox).WidthOverride(18).HeightOverride(2)
                        .Visibility_Lambda([Selected, ShowLine, Id] { return Selected.Get() == Id && ShowLine.Get() ? EVisibility::HitTestInvisible : EVisibility::Hidden; })[SNew(SImage).Image(&Style.TabLine)]]]]];
    }
    return Row;
}
TSharedRef<SWidget> Header(const FStyle& Style, const FHeader& Data, TSharedRef<SWidget> Tabs, TSharedRef<SWidget> Extra)
{
    return SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(100, 14)).Padding(FMargin(22, 10, 14, 10))
    [SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 18, 0)[Label(Data.Title, 20, TextPrimary, true)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 18, 0)[SNew(STextBlock).Text(Data.Breadcrumb).Font(TextFont(13 * .75f)).ColorAndOpacity(TextTertiary)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Tabs]
        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(18, 0)
        [SNew(SBox).WidthOverride(230).HeightOverride(ActionHeight)
            [SNew(SEditableTextBox).HintText(FText::FromString(Data.SearchHint)).Font(TextFont(14 * .75f))
                .OnTextChanged_Lambda([Search = Data.OnSearch](const FText& Text) { Search(Text); })]]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 14, 0)[SNew(STextBlock).Text(Data.Summary).Font(TextFont(12 * .75f)).ColorAndOpacity(TextTertiary)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)[Extra]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [SNew(SButton).ButtonStyle(&Style.Quiet).ContentPadding(FMargin(12, 0)).OnClicked_Lambda([Close = Data.OnClose] { Close(); return FReply::Handled(); })
            [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)[Label(TEXT("×"), 20, TextSecondary)]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text(FText::FromString(Data.CloseKey)).Font(NumberFont(12 * .75f, true)).ColorAndOpacity(HUDGoldLight)]]]]];
}
TSharedRef<SWidget> Legend(const FStyle& Style, TWeakPtr<SColdSteelSkillTreeCanvas> Canvas, const FString& ItemName)
{
    auto Item = [](const FString& Text, const FLinearColor& Swatch, bool Dashed)
    {
        return SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 7, 0)
                [SNew(SBox).WidthOverride(22).HeightOverride(2)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(Swatch.R, Swatch.G, Swatch.B, Dashed ? .45f : 1.f))]]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(Text, 12, TextTertiary)];
    };
    auto Zoom = [&Style](const FString& Caption, TFunction<void()> Click)
    {
        return SNew(SButton).ButtonStyle(&Style.Quiet).ContentPadding(FMargin(9, 0)).OnClicked_Lambda([Click] { Click(); return FReply::Handled(); })
            [SNew(SBox).HeightOverride(28).VAlign(VAlign_Center)[Label(Caption, 13, TextSecondary)]];
    };
    return SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(18, 184)).Padding(FMargin(20, 6, 14, 6))
    [SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 18, 0)[Item(TEXT("实线：条件已满足"), HUDGold, false)]
        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 18, 0)[Item(TEXT("虚线：条件未满足"), Gray(222), true)]
        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 18, 0)[Item(TEXT("流动亮线：选中") + ItemName + TEXT("的前置路线"), HUDGoldLight, false)]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 18, 0)[Label(TEXT("任一：汇流框　全部 m/n：卡角条件进度　拖动平移 · Ctrl+滚轮缩放"), 12, TextTertiary)]
        + SHorizontalBox::Slot().FillWidth(1)
        + SHorizontalBox::Slot().AutoWidth()[Zoom(TEXT("−"), [Canvas] { if(auto C = Canvas.Pin()) C->ZoomBy(1 / 1.2f); })]
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4, 0)
            [SNew(SBox).WidthOverride(44)[SNew(STextBlock).Justification(ETextJustify::Center).Font(NumberFont(12 * .75f)).ColorAndOpacity(TextTertiary)
                .Text_Lambda([Canvas] { auto C = Canvas.Pin(); return FText::FromString(FString::Printf(TEXT("%d%%"), C ? FMath::RoundToInt(C->GetZoom() * 100) : 100)); })]]
        + SHorizontalBox::Slot().AutoWidth()[Zoom(TEXT("+"), [Canvas] { if(auto C = Canvas.Pin()) C->ZoomBy(1.2f); })]
        + SHorizontalBox::Slot().AutoWidth()[Zoom(TEXT("适应宽度"), [Canvas] { if(auto C = Canvas.Pin()) C->Fit(); })]];
}
TSharedRef<SWidget> DetailHead(const FStyle& Style, TSharedRef<SWidget> Icon, const FString& Breadcrumb, const FString& Title, const FString& Tag)
{
    return SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 18, 0)[SNew(SBox).WidthOverride(92).HeightOverride(92)[Icon]]
        + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[Label(Breadcrumb, 12, HUDGold)]
            + SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 8)[Label(Title, 24, TextPrimary, true)]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left)[SNew(SBorder).BorderImage(&Style.ChipBrush).Padding(FMargin(10, 3))[Label(Tag, 12, TextSecondary)]]];
}
TSharedRef<SWidget> Progress(const FStyle& Style, const FString& State, const FString& Value, const FString& Note, float Fill, const FLinearColor& StateColor, const FLinearColor& FillColor)
{
    Fill = FMath::Clamp(Fill, 0.f, 1.f);
    return SNew(SBorder).BorderImage(&Style.CardBrush).Padding(FMargin(18, 14, 18, 16))[SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(State, 16, StateColor, true)]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(STextBlock).Text(FText::FromString(Value)).Font(NumberFont(16 * .75f, true)).ColorAndOpacity(TextPrimary)]]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 10)[SNew(SBox).HeightOverride(4)[SNew(SOverlay)
            + SOverlay::Slot()[SNew(SImage).Image(&Style.BarBrush)]
            + SOverlay::Slot()[SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(FMath::Max(.001f, Fill))[SNew(SBorder).Visibility(Fill > 0 ? EVisibility::HitTestInvisible : EVisibility::Collapsed)
                    .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FillColor)]
                + SHorizontalBox::Slot().FillWidth(FMath::Max(.001f, 1 - Fill))[SNullWidget::NullWidget]]]]
        + SVerticalBox::Slot().AutoHeight()[Label(Note, 12, TextTertiary, false, true)]];
}
TSharedRef<SWidget> Action(const FString& Caption, const FButtonStyle* Style, bool Enabled, TFunction<void()> OnClick, const FLinearColor& Color, bool Medium)
{
    return SNew(SButton).ButtonStyle(Style).IsEnabled(Enabled).ContentPadding(FMargin(10, 0)).HAlign(HAlign_Center)
        .OnClicked_Lambda([OnClick] { OnClick(); return FReply::Handled(); })
        [SNew(SBox).HeightOverride(ActionHeight).VAlign(VAlign_Center)[Label(Caption, 14, Enabled ? Color : TextTertiary, Medium)]];
}
TSharedRef<SWidget> DetailPage(TSharedRef<SWidget> Body, TSharedRef<SWidget> Actions, TSharedRef<SWidget> Note, float NoteGap)
{
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().FillHeight(1)[SNew(SScrollBox) + SScrollBox::Slot().Padding(FMargin(28, 26, 28, 24))[Body]]
        + SVerticalBox::Slot().AutoHeight()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Gray(18, 160)).Padding(FMargin(28, 14, 28, 18))
            [SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[Actions]
                + SVerticalBox::Slot().AutoHeight().Padding(0, NoteGap, 0, 0)[Note]]];
}
}
