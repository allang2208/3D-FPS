#include "ColdSteelHUDWidget.h"
#include "ColdSteelQuickBarTypes.h"
#include "ColdSteelQuickSlot.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Overlay.h"
#include "Components/SizeBox.h"

namespace
{
    constexpr float SlotPixels=48.f, GapPixels=8.f, GroupGap=16.f, BarPadding=9.f;
    constexpr float Step=SlotPixels+GapPixels;
    float RowWidth(int32 Count) { return Count*SlotPixels+(Count-1)*GapPixels; }
}

void UColdSteelHUDWidget::BuildHotbar(UCanvasPanel* Root)
{
    auto* Surface=MakeSurface(ColdSteelUI::GlassTint,10.f,ColdSteelUI::Border);
    HotbarLayoutSize=WidgetTree->ConstructWidget<USizeBox>();Surface->SetContent(HotbarLayoutSize);
    HotbarLayoutPanel=WidgetTree->ConstructWidget<UCanvasPanel>();HotbarLayoutSize->SetContent(HotbarLayoutPanel);
    for(int32 Index=0;Index<ColdSteelQuickBar::Count;++Index)
    {
        auto* CellSurface=MakeHotbarSlot(Index);QuickSlotSurfaces.Add(CellSurface);
        if(Index>=ColdSteelQuickBar::ItemOffset)HotbarDropSlots.Add(CellSurface);
        HotbarLayoutPanel->AddChildToCanvas(CellSurface)->SetZOrder(1);
    }
    // Fixed F/G actions are deliberately absent from the binding and drop-target arrays.
    QuickCombatSlotSurface=MakeHotbarSlot(INDEX_NONE,TEXT("quickCombat"));
    HotbarLayoutPanel->AddChildToCanvas(QuickCombatSlotSurface)->SetZOrder(1);
    RuneBladesSlotSurface=MakeHotbarSlot(INDEX_NONE,TEXT("runeBlades"));
    HotbarLayoutPanel->AddChildToCanvas(RuneBladesSlotSurface)->SetZOrder(1);
    RuneBladesSlotSurface->SetVisibility(ESlateVisibility::Collapsed);
    const auto Divider=[this]()
    {
        auto* Line=MakeSurface(ColdSteelUI::Border,0,FLinearColor::Transparent,0);
        Line->SetPadding(FMargin(0));Line->SetVisibility(ESlateVisibility::HitTestInvisible);
        HotbarLayoutPanel->AddChildToCanvas(Line);return Line;
    };
    HotbarNumberDivider=Divider();HotbarSpecialDivider=Divider();RuneBladesDivider=Divider();
    RuneBladesDivider->SetVisibility(ESlateVisibility::Collapsed);
    HotbarCanvasSlot=Root->AddChildToCanvas(Surface);
    HotbarCanvasSlot->SetAnchors(FAnchors(.5f,1.f));HotbarCanvasSlot->SetAlignment(FVector2D(.5f,1.f));
    HotbarCanvasSlot->SetAutoSize(false);HotbarCanvasSlot->SetZOrder(30);
    UpdateHotbarLayout(GetCachedGeometry());
}

UBorder* UColdSteelHUDWidget::MakeHotbarSlot(int32 Index,FName FixedSkill)
{
    const float S=ColdSteelUI::PixelScale(this);
    auto* Surface=MakeSurface(ColdSteelUI::Content,7/S,ColdSteelUI::Border,1/S);
    Surface->SetPadding(FMargin(0));Surface->SetHorizontalAlignment(HAlign_Fill);Surface->SetVerticalAlignment(VAlign_Fill);
    auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetWidthOverride(SlotPixels/S);Size->SetHeightOverride(SlotPixels/S);
    Surface->SetContent(Size);
    auto* Overlay=WidgetTree->ConstructWidget<UOverlay>();Size->SetContent(Overlay);
    BuildQuickSlot(Overlay,Index,FixedSkill);return Surface;
}

void UColdSteelHUDWidget::UpdateHotbarLayout(const FGeometry& Geometry)
{
    if(!HotbarCanvasSlot||!HotbarLayoutPanel)return;
    const float S=ColdSteelUI::PixelScale(this);
    float ViewWidth=Geometry.GetLocalSize().X*S;
    if(ViewWidth<100)ViewWidth=UWidgetLayoutLibrary::GetViewportSize(this).X;
    if(ViewWidth<100)ViewWidth=1280;
    const bool HasSpecial=RuneBladesSlotSurface->GetVisibility()!=ESlateVisibility::Collapsed;
    const float SpecialWidth=RowWidth(HasSpecial?2:1),LettersWidth=RowWidth(3),NumbersWidth=RowWidth(10);
    const float FullWidth=LettersWidth+GroupGap+NumbersWidth+GroupGap+SpecialWidth;
    const int32 Mode=ViewWidth>=FullWidth+2*BarPadding+24?0:ViewWidth>=NumbersWidth+2*BarPadding+24?1:2;
    if(Mode==HotbarLayoutMode&&FMath::IsNearlyEqual(S,HotbarLayoutScale,.0001f)&&HasSpecial==bHotbarLayoutHasSpecial)return;
    HotbarLayoutMode=Mode;HotbarLayoutScale=S;bHotbarLayoutHasSpecial=HasSpecial;
    const float HeaderWidth=LettersWidth+GroupGap+SpecialWidth;
    const float InnerWidth=Mode==0?FullWidth:Mode==1?NumbersWidth:FMath::Max(HeaderWidth,RowWidth(5));
    const float InnerHeight=SlotPixels+Mode*Step;
    HotbarPixelSize=FVector2D(InnerWidth+2*BarPadding,InnerHeight+2*BarPadding);
    HotbarCanvasSlot->SetSize(HotbarPixelSize/S);HotbarCanvasSlot->SetPosition(FVector2D(0,-12/S));
    HotbarLayoutSize->SetWidthOverride(InnerWidth/S);HotbarLayoutSize->SetHeightOverride(InnerHeight/S);
    auto* Surface=CastChecked<UBorder>(HotbarCanvasSlot->GetContent());
    Surface->SetPadding(FMargin(BarPadding/S));Surface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));
    const auto Place=[S](UBorder* Widget,float X,float Y)
    {
        auto* CellLayout=CastChecked<UCanvasPanelSlot>(Widget->Slot);CellLayout->SetPosition(FVector2D(X,Y)/S);
        CellLayout->SetSize(FVector2D(SlotPixels,SlotPixels)/S);
        auto* Size=CastChecked<USizeBox>(Widget->GetContent());Size->SetWidthOverride(SlotPixels/S);Size->SetHeightOverride(SlotPixels/S);
        Widget->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,7/S,ColdSteelUI::Border,1/S));
    };
    const auto PlaceDivider=[S](UBorder* Widget,float X)
    {
        auto* DividerLayout=CastChecked<UCanvasPanelSlot>(Widget->Slot);DividerLayout->SetPosition(FVector2D(X,8)/S);DividerLayout->SetSize(FVector2D(1,32)/S);
    };
    const float HeaderStart=Mode==0?0:(InnerWidth-HeaderWidth)*.5f;
    for(int32 Index=0;Index<ColdSteelQuickBar::ItemOffset;++Index)Place(QuickSlotSurfaces[Index],HeaderStart+Index*Step,0);
    for(int32 N=0;N<10;++N)
    {
        const float X=Mode==0?LettersWidth+GroupGap+N*Step:Mode==1?N*Step:(InnerWidth-RowWidth(5))*.5f+(N%5)*Step;
        const float Y=Mode==0?0:Mode==1?Step:(1+N/5)*Step;
        Place(QuickSlotSurfaces[ColdSteelQuickBar::ItemOffset+N],X,Y);
    }
    const float SpecialStart=Mode==0?LettersWidth+GroupGap+NumbersWidth+GroupGap:HeaderStart+LettersWidth+GroupGap;
    Place(QuickCombatSlotSurface,SpecialStart,0);Place(RuneBladesSlotSurface,SpecialStart+Step,0);
    PlaceDivider(HotbarNumberDivider,LettersWidth+7);
    HotbarNumberDivider->SetVisibility(Mode==0?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    PlaceDivider(HotbarSpecialDivider,SpecialStart-9);PlaceDivider(RuneBladesDivider,SpecialStart+SlotPixels+3);
    for(const auto& QuickSlot:QuickSlots)if(QuickSlot)QuickSlot->SetDisplayScale(S);
    // The left status card also depends on the actual bar width/height and G visibility.
    TopHUDViewport=FVector2D::ZeroVector;
}
