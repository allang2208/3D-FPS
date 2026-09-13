#include "ColdSteelDetailRow.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/ProgressBar.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"

void UColdSteelDetailRow::Configure(const FString& Label, float Scale, bool bNumeric)
{
    SetIsFocusable(true);
    bNumericValue=bNumeric;
    Surface = WidgetTree->ConstructWidget<UBorder>();
    WidgetTree->RootWidget = Surface;
    auto* Height = WidgetTree->ConstructWidget<USizeBox>();
    Surface->SetContent(Height);
    auto* Row = WidgetTree->ConstructWidget<UHorizontalBox>();
    Line = Row;
    Height->SetContent(Row);
    NameText = WidgetTree->ConstructWidget<UTextBlock>();
    NameText->SetText(FText::FromString(Label));
    NameText->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    NameText->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* NameSlot = Row->AddChildToHorizontalBox(NameText);
    NameSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    NameSlot->SetVerticalAlignment(VAlign_Center);
    ValueText = WidgetTree->ConstructWidget<UTextBlock>();
    ValueText->SetJustification(ETextJustify::Right);
    ValueText->SetAutoWrapText(!bNumericValue);
    ValueText->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* ValueSlot = Row->AddChildToHorizontalBox(ValueText);
    if(!bNumericValue){auto Fill=FSlateChildSize(ESlateSizeRule::Fill);Fill.Value=2;ValueSlot->SetSize(Fill);}
    ValueSlot->SetVerticalAlignment(VAlign_Center);
    PlusButton = WidgetTree->ConstructWidget<UButton>();
    PlusText = WidgetTree->ConstructWidget<UTextBlock>();
    PlusText->SetText(FText::FromString(TEXT("+")));
    PlusText->SetColorAndOpacity(ColdSteelUI::Accent);
    PlusText->SetJustification(ETextJustify::Center);
    PlusButton->SetContent(PlusText);
    Cast<UButtonSlot>(PlusText->Slot)->SetPadding(FMargin(0));
    PlusButton->SetToolTipText(FText::FromString(TEXT("分配 1 点")+Label));
    PlusButton->OnClicked.AddDynamic(this, &ThisClass::HandleAllocate);
    PlusSize=WidgetTree->ConstructWidget<USizeBox>();PlusSize->SetContent(PlusButton);
    Row->AddChildToHorizontalBox(PlusSize)->SetVerticalAlignment(VAlign_Center);
    SetCanAllocate(false);
    SetValue(TEXT("—"), false);
    UpdateScale(Scale);
}

void UColdSteelDetailRow::UpdateScale(float Scale)
{
    VisualScale=Scale;
    const float Points=14.f*.75f/Scale;
    NameText->SetFont(ColdSteelUI::TextFont(Points));
    ValueText->SetFont(bNumericValue?ColdSteelUI::NumberFont(Points,true):ColdSteelUI::TextFont(Points,true));
    PlusText->SetFont(ColdSteelUI::NumberFont(Points,true));
    Surface->SetPadding(FMargin(8/Scale,6/Scale));
    Cast<USizeBox>(Surface->GetContent())->SetMinDesiredHeight(24/Scale);
    PlusButton->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    PlusSize->SetWidthOverride(24/Scale);PlusSize->SetHeightOverride(24/Scale);
    Cast<UHorizontalBoxSlot>(PlusSize->Slot)->SetPadding(FMargin(8/Scale,0,0,0));
    Cast<UHorizontalBoxSlot>(ValueText->Slot)->SetPadding(FMargin(Meter?0:12/Scale,0,0,0));
    if(Meter)
    {
        NameText->SetMinDesiredWidth(44/Scale);ValueText->SetMinDesiredWidth(100/Scale);
        MeterTrack->SetHeightOverride(8/Scale);
        Cast<UHorizontalBoxSlot>(MeterTrack->Slot)->SetPadding(FMargin(8/Scale,0,12/Scale,0));
        FProgressBarStyle Style;
        Style.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,4/Scale,ColdSteelUI::Border,1/Scale));
        Style.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,3/Scale,FLinearColor::Transparent,0));
        Meter->SetWidgetStyle(Style);
    }
    RefreshHighlight();
}

void UColdSteelDetailRow::SetValue(const FString& Value, bool bAvailable)
{
    if (!ValueText) return;
    if (ValueText->GetText().ToString() != Value) ValueText->SetText(FText::FromString(Value));
    ValueText->SetColorAndOpacity(bAvailable ? ColdSteelUI::TextPrimary : ColdSteelUI::TextTertiary);
}
FString UColdSteelDetailRow::GetValue() const { return ValueText ? ValueText->GetText().ToString() : FString(); }
void UColdSteelDetailRow::SetCanAllocate(bool bCanAllocate) { if (PlusSize) PlusSize->SetVisibility(bCanAllocate ? ESlateVisibility::Visible : ESlateVisibility::Collapsed); }
void UColdSteelDetailRow::HandleAllocate() { Allocate.ExecuteIfBound(); }
UProgressBar* UColdSteelDetailRow::AddMeter(const FLinearColor& Color, float Scale)
{
    Cast<UHorizontalBoxSlot>(NameText->Slot)->SetSize(FSlateChildSize(ESlateSizeRule::Automatic));
    // Insert before values while the widget tree is still being constructed.
    Line->RemoveChild(ValueText); Line->RemoveChild(PlusSize);
    Meter = WidgetTree->ConstructWidget<UProgressBar>();
    Meter->SetFillColorAndOpacity(Color); Meter->SetPercent(0);
    MeterTrack = WidgetTree->ConstructWidget<USizeBox>();
    MeterTrack->SetContent(Meter);
    auto* TrackSlot = Line->AddChildToHorizontalBox(MeterTrack);
    TrackSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill)); TrackSlot->SetVerticalAlignment(VAlign_Center);
    Line->AddChildToHorizontalBox(ValueText)->SetVerticalAlignment(VAlign_Center);
    Line->AddChildToHorizontalBox(PlusSize)->SetVerticalAlignment(VAlign_Center);
    UpdateScale(Scale);
    return Meter;
}
void UColdSteelDetailRow::RefreshHighlight()
{
    const bool Active = bPointerInside || HasKeyboardFocus();
    if (Surface) Surface->SetBrush(ColdSteelUI::RoundedBrush(Active ? ColdSteelUI::ButtonHover : ColdSteelUI::AttributeRow,
        ColdSteelUI::ButtonRadius/VisualScale, Active ? ColdSteelUI::Accent : FLinearColor::Transparent, Active ? 1/VisualScale : 0));
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
