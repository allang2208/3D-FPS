#include "ColdSteelDetailRow.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ProgressBar.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"

void UColdSteelDetailRow::Configure(const FString& Label, float Scale)
{
    SetIsFocusable(true);
    Surface = WidgetTree->ConstructWidget<UBorder>();
    WidgetTree->RootWidget = Surface;
    Surface->SetPadding(FMargin(8 / Scale, 4 / Scale));
    auto* Height = WidgetTree->ConstructWidget<USizeBox>();
    Height->SetMinDesiredHeight(20 / Scale);
    Surface->SetContent(Height);
    auto* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    Line = Row;
    Height->SetContent(Row);
    auto* Name = WidgetTree->ConstructWidget<UTextBlock>();
    Name->SetText(FText::FromString(Label));
    Name->SetFont(ColdSteelUI::TextFont(9 / Scale));
    Name->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    Name->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* NameSlot = Row->AddChildToHorizontalBox(Name);
    NameSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    NameSlot->SetVerticalAlignment(VAlign_Center);
    ValueText = WidgetTree->ConstructWidget<UTextBlock>();
    ValueText->SetFont(ColdSteelUI::NumberFont(10.5f / Scale, true));
    ValueText->SetJustification(ETextJustify::Right);
    ValueText->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* ValueSlot = Row->AddChildToHorizontalBox(ValueText);
    ValueSlot->SetPadding(FMargin(12 / Scale, 0, 0, 0));
    ValueSlot->SetVerticalAlignment(VAlign_Center);
    PlusButton = WidgetTree->ConstructWidget<UButton>();
    PlusButton->SetStyle(FButtonStyle().SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, 4))
        .SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, 4, ColdSteelUI::Accent))
        .SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, 4, ColdSteelUI::Accent)));
    auto* Plus = WidgetTree->ConstructWidget<UTextBlock>();
    Plus->SetText(FText::FromString(TEXT("+")));
    Plus->SetFont(ColdSteelUI::NumberFont(10.5f / Scale, true));
    Plus->SetColorAndOpacity(ColdSteelUI::Accent);
    PlusButton->SetContent(Plus);
    PlusButton->OnClicked.AddDynamic(this, &ThisClass::HandleAllocate);
    Row->AddChildToHorizontalBox(PlusButton)->SetPadding(FMargin(8 / Scale, 0, 0, 0));
    SetCanAllocate(false);
    SetValue(TEXT("—"), false);
    RefreshHighlight();
}

void UColdSteelDetailRow::SetValue(const FString& Value, bool bAvailable)
{
    if (!ValueText) return;
    if (ValueText->GetText().ToString() != Value) ValueText->SetText(FText::FromString(Value));
    ValueText->SetColorAndOpacity(bAvailable ? ColdSteelUI::TextPrimary : ColdSteelUI::TextTertiary);
}
FString UColdSteelDetailRow::GetValue() const { return ValueText ? ValueText->GetText().ToString() : FString(); }
void UColdSteelDetailRow::SetCanAllocate(bool bCanAllocate) { if (PlusButton) PlusButton->SetVisibility(bCanAllocate ? ESlateVisibility::Visible : ESlateVisibility::Collapsed); }
void UColdSteelDetailRow::HandleAllocate() { Allocate.ExecuteIfBound(); }
UProgressBar* UColdSteelDetailRow::AddMeter(const FLinearColor& Color, float Scale)
{
    Surface->SetPadding(FMargin(0, 2 / Scale));
    Cast<USizeBox>(Surface->GetContent())->SetMinDesiredHeight(14 / Scale);
    auto* Name = Cast<UTextBlock>(Line->GetChildAt(0));
    Name->SetMinDesiredWidth(44 / Scale);
    Cast<UHorizontalBoxSlot>(Name->Slot)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    // Insert before values while the widget tree is still being constructed.
    Line->RemoveChild(ValueText); Line->RemoveChild(PlusButton);
    auto* Meter = WidgetTree->ConstructWidget<UProgressBar>();
    FProgressBarStyle Style;
    Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content, 4, ColdSteelUI::Border));
    Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White, 3, FLinearColor::Transparent, 0));
    Meter->SetWidgetStyle(Style); Meter->SetFillColorAndOpacity(Color); Meter->SetPercent(0);
    auto* Track = WidgetTree->ConstructWidget<USizeBox>();
    Track->SetHeightOverride(14 / Scale); Track->SetContent(Meter);
    auto* TrackSlot = Line->AddChildToHorizontalBox(Track);
    TrackSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); TrackSlot->SetVerticalAlignment(VAlign_Center);
    TrackSlot->SetPadding(FMargin(8 / Scale, 0, 12 / Scale, 0));
    ValueText->SetMinDesiredWidth(92 / Scale);
    Line->AddChildToHorizontalBox(ValueText)->SetVerticalAlignment(VAlign_Center);
    Line->AddChildToHorizontalBox(PlusButton);
    return Meter;
}
void UColdSteelDetailRow::RefreshHighlight()
{
    const bool Active = bPointerInside || HasKeyboardFocus();
    if (Surface) Surface->SetBrush(ColdSteelUI::RoundedBrush(Active ? ColdSteelUI::ButtonHover : ColdSteelUI::AttributeRow,
        4, Active ? ColdSteelUI::Accent : FLinearColor::Transparent, Active ? 1 : 0));
}
void UColdSteelDetailRow::NativeOnMouseEnter(const FGeometry& G, const FPointerEvent& E)
{
    Super::NativeOnMouseEnter(G, E); bPointerInside = true; RefreshHighlight(); ShowDetail.ExecuteIfBound();
}
void UColdSteelDetailRow::NativeOnMouseLeave(const FPointerEvent& E)
{
    Super::NativeOnMouseLeave(E); bPointerInside = false; RefreshHighlight();
    if (!HasKeyboardFocus()) HideDetail.ExecuteIfBound();
}
FReply UColdSteelDetailRow::NativeOnFocusReceived(const FGeometry& G, const FFocusEvent& E)
{
    Super::NativeOnFocusReceived(G, E); RefreshHighlight(); ShowDetail.ExecuteIfBound(); return FReply::Handled();
}
void UColdSteelDetailRow::NativeOnFocusLost(const FFocusEvent& E)
{
    Super::NativeOnFocusLost(E); RefreshHighlight(); if (!bPointerInside) HideDetail.ExecuteIfBound();
}
