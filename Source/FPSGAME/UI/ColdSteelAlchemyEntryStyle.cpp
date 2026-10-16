#include "ColdSteelAlchemyWidget.h"
#include "ColdSteelForgeBoard.h"
#include "ColdSteelGunRecipeOptionWidget.h"
#include "ColdSteelUIStyle.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/GridSlot.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBoxSlot.h"

void UColdSteelAlchemyWidget::ScaleEntry()
{
    if(!Management||FMath::IsNearlyEqual(EntryScale,Scale,.001f))return;EntryScale=Scale;
    EntryOptions.RemoveAll([](const auto& Entry){return !Entry.IsValid();});
    for(const auto& Option:EntryOptions)if(auto* Widget=Option.Get())Widget->SetPixelScale(Scale);
    for(const auto& Pair:Actions)if(auto* B=Pair.Value.Get())
    {B->SetStyle(ColdSteelUI::ButtonStyle(Scale));if(auto* ContentSlot=Cast<UButtonSlot>(B->GetContent()->Slot))ContentSlot->SetPadding(FMargin(12/Scale,4/Scale));}
    for(const auto& W:ButtonSizes)if(auto* Size=W.Get())Size->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);
    EntryCloseSize->SetWidthOverride(ColdSteelUI::ActionHeight/Scale);
    EntryDiscardSlot->SetPadding(FMargin(ColdSteelUI::ActionGap/Scale,0,0,0));EntryManualSlot->SetPadding(FMargin(ColdSteelUI::ActionGap/Scale,0,0,0));
    auto ComboStyle=Choice->GetWidgetStyle();auto ComboButton=ComboStyle.ComboButtonStyle;
    ComboButton.SetButtonStyle(ColdSteelUI::ButtonStyle(Scale));
    ComboButton.SetMenuBorderBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(25,252),ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));
    ComboButton.DownArrowImage.ImageSize=FVector2D(8/Scale,8/Scale);
    ComboButton.SetDownArrowPadding(FMargin(4/Scale,0,0,0));ComboButton.SetShadowOffset(FVector2D::ZeroVector);
    ComboStyle.SetComboButtonStyle(ComboButton);Choice->SetWidgetStyle(ComboStyle);
    Choice->SetContentPadding(FMargin(22/Scale,4/Scale,10/Scale,4/Scale));Choice->SetMaxListHeight(240/Scale);
    auto ItemStyle=Choice->GetItemStyle();
    ItemStyle.SetEvenRowBackgroundBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundBrush(ItemStyle.EvenRowBackgroundBrush);
    ItemStyle.SetEvenRowBackgroundHoveredBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale));
    ItemStyle.SetOddRowBackgroundHoveredBrush(ItemStyle.EvenRowBackgroundHoveredBrush);
    ItemStyle.SetActiveBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,ColdSteelUI::ButtonRadius/Scale,ColdSteelUI::Accent,1/Scale));
    ItemStyle.SetInactiveBrush(ItemStyle.ActiveBrush);Choice->SetItemStyle(ItemStyle);
    if(auto* LeftSlot=Cast<UHorizontalBoxSlot>(EntryPreview->Slot))LeftSlot->SetPadding(FMargin(0,0,4/Scale,0));
    EntryParameterSlot->SetPadding(FMargin(4/Scale,0,0,0));
    for(const auto& Cell:EntryParameterSlots)if(auto* CellSlot=Cell.Get())CellSlot->SetPadding(FMargin(CellSlot->GetColumn()==0?0.f:12.f/Scale,6.f/Scale,0,6.f/Scale));
    for(const auto& Card:EntryCards)if(auto* Border=Card.Get())
    {Border->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale,ColdSteelUI::Border,1/Scale));Border->SetPadding(12/Scale);}
    for(const auto& Row:EntrySpacings)if(auto* RowSlot=Row.Slot.Get())RowSlot->SetPadding(Row.Padding*(1.f/Scale));
    for(const auto& Cell:EntryMaterialSlots)if(auto* CellSlot=Cell.Get())CellSlot->SetPadding(FMargin(CellSlot->GetColumn()==0?0.f:12.f/Scale,4.f/Scale,0,4.f/Scale));
    EntryScroll->SetScrollbarThickness(FVector2D(6/Scale,6/Scale));EntryScroll->SetScrollbarPadding(FMargin(4/Scale,0,0,0));
    EntryTimerSize->SetHeightOverride(3/Scale);
    FProgressBarStyle Progress;Progress.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(45),1.5f/Scale,FLinearColor::Transparent,0));
    Progress.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f/Scale,FLinearColor::Transparent,0));EntryTimer->SetWidgetStyle(Progress);
    Management->SetBrush(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,ColdSteelUI::PanelRadius/Scale,ColdSteelUI::Border,1/Scale));Management->SetPadding(1/Scale);
    EntryBlur->SetBlurStrength(ColdSteelUI::GlassBlurStrength);EntryBlur->SetBlurRadius(ColdSteelUI::GlassBlurRadius);EntryBlur->SetCornerRadius(FVector4(10,10,10,10)/Scale);
    EntryBlur->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/Scale));
    EntryHeader->SetPadding(FMargin(18/Scale,12/Scale));EntryBody->SetPadding(12/Scale);EntryFooter->SetPadding(12/Scale);
}
void UColdSteelAlchemyWidget::LayoutEntry(FVector2D Size)
{
    ScaleEntry();
    const float PixelsX=float(Size.X*Scale),Inset=ColdSteelUI::NavigationDrawerInset;
    const float Width=FMath::Min(FMath::Min(PixelsX-Inset-12.f,FMath::Clamp(PixelsX*.48f,720.f,1040.f)),(PixelsX-Inset-12.f)*.5f)/Scale;
    const float PanelHeight=FMath::Max(1.f,float(Size.Y)-24/Scale);
    if(ManagementSlot.IsValid())
    {ManagementSlot->SetPosition(FVector2D(Size.X-Inset/Scale-2*Width,12/Scale));ManagementSlot->SetSize(FVector2D(Width,PanelHeight));}
    const float Height=FMath::Clamp(PanelHeight*Scale-520.f,200.f,420.f)/Scale;
    if(!FMath::IsNearlyEqual(Height,EntryBoardHeight,.5f)){EntryBoardHeight=Height;EntryBoardSize->SetHeightOverride(Height);}
}
