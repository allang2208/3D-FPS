#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/BackgroundBlur.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/Overlay.h"
#include "Components/OverlaySlot.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"

namespace
{
// game-dev: transition .16s ease == cubic-bezier(.25,.1,.25,1).
float TimelineCSSEase(float T)
{
    if(T<=0 || T>=1)return FMath::Clamp(T,0.f,1.f);
    float Low=0,High=1,U=.5f;
    for(int32 I=0;I<12;++I){U=(Low+High)*.5f;const float V=1-U;const float X=3*V*V*U*.25f+3*V*U*U*.25f+U*U*U;if(X<T)Low=U;else High=U;}
    const float V=1-U;return 3*V*V*U*.1f+3*V*U*U+U*U*U;
}
void TimelineFill(UCanvasPanelSlot* Slot,const FAnchors& Anchors,FMargin Margin=FMargin(0),int32 Z=0)
{Slot->SetAnchors(Anchors);Slot->SetOffsets(Margin);Slot->SetZOrder(Z);}
void TimelineOverlayFill(UOverlaySlot* Slot)
{Slot->SetHorizontalAlignment(HAlign_Fill);Slot->SetVerticalAlignment(VAlign_Fill);}
}

UTextBlock* UColdSteelHUDWidget::MakeTimelineText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric,bool Medium)
{
    auto* Label=WidgetTree->ConstructWidget<UTextBlock>();Label->SetText(FText::FromString(Text));Label->SetColorAndOpacity(Color);
    const float Points=Pixels*.75f/ColdSteelUI::PixelScale(this);
    Label->SetFont(Numeric?ColdSteelUI::NumberFont(Points,Medium):ColdSteelUI::TextFont(Points,Medium));
    TimelineLabels.Add({Label,Pixels,Numeric,Medium});return Label;
}

void UColdSteelHUDWidget::BuildEventTimeline(UCanvasPanel* Root)
{
    const float Scale=ColdSteelUI::PixelScale(this);
    auto Button=[this,Scale](const FString& Text,float Size=14.f)
    {
        auto* B=WidgetTree->ConstructWidget<UButton>();B->SetStyle(ColdSteelUI::ButtonStyle(Scale));
        B->SetContent(MakeTimelineText(Text,Size,ColdSteelUI::TextPrimary));
        if(auto* S=Cast<UButtonSlot>(B->GetContent()->Slot)){S->SetPadding(FMargin(8/Scale,2/Scale));S->SetHorizontalAlignment(HAlign_Center);S->SetVerticalAlignment(VAlign_Center);}
        return B;
    };
    auto Glass=[this,Scale]()
    {
        auto* B=WidgetTree->ConstructWidget<UBackgroundBlur>();B->SetPadding(FMargin(0));B->SetBlurStrength(ColdSteelUI::GlassBlurStrength);
        B->SetOverrideAutoRadiusCalculation(true);B->SetBlurRadius(ColdSteelUI::GlassBlurRadius);B->SetApplyAlphaToBlur(true);
        B->SetCornerRadius(FVector4(10/Scale));B->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/Scale));return B;
    };
    TimelineWidthBox=WidgetTree->ConstructWidget<USizeBox>();
    auto* RootSlot=Root->AddChildToCanvas(TimelineWidthBox);RootSlot->SetAnchors(FAnchors(0,0));RootSlot->SetAlignment(FVector2D(0,0));
    RootSlot->SetPosition(FVector2D(0,76/Scale));RootSlot->SetAutoSize(true);RootSlot->SetZOrder(28);
    auto* Layers=WidgetTree->ConstructWidget<UOverlay>();TimelineWidthBox->SetContent(Layers);
    TimelineShellBlur=Glass();TimelineShellBlur->SetVisibility(ESlateVisibility::Collapsed);TimelineShellBlur->SetRenderOpacity(0);
    TimelineOverlayFill(Layers->AddChildToOverlay(TimelineShellBlur));
    TimelinePanel=MakeSurface(ColdSteelUI::GlassTint,10/Scale,ColdSteelUI::Border,1/Scale);TimelinePanel->SetPadding(FMargin(0));TimelineShellBlur->SetContent(TimelinePanel);
    // Only this decorative sibling owns the outline. Collapsing it cannot leave an expanded frame behind.
    TimelineContentPadding=WidgetTree->ConstructWidget<UBorder>();FSlateBrush Empty;Empty.DrawAs=ESlateBrushDrawType::NoDrawType;
    TimelineContentPadding->SetBrush(Empty);TimelineContentPadding->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
    TimelineOverlayFill(Layers->AddChildToOverlay(TimelineContentPadding));
    auto* Column=WidgetTree->ConstructWidget<UVerticalBox>();TimelineContentPadding->SetContent(Column);
    TimelineExpandedClip=WidgetTree->ConstructWidget<USizeBox>();TimelineExpandedClip->SetHeightOverride(0);TimelineExpandedClip->SetClipping(EWidgetClipping::ClipToBoundsAlways);
    TimelineExpandedClip->SetVisibility(ESlateVisibility::Collapsed);Column->AddChildToVerticalBox(TimelineExpandedClip);
    TimelineExpandedScroll=WidgetTree->ConstructWidget<UScrollBox>();TimelineExpandedScroll->SetAllowOverscroll(false);
    TimelineExpandedScroll->SetScrollbarThickness(FVector2D(6/Scale));TimelineExpandedClip->SetContent(TimelineExpandedScroll);
    TimelineExpandedContent=WidgetTree->ConstructWidget<UVerticalBox>();TimelineExpandedScroll->AddChild(TimelineExpandedContent);
    auto* Heading=WidgetTree->ConstructWidget<UVerticalBox>();TimelineExpandedContent->AddChildToVerticalBox(Heading);
    auto* HeadingLabel=MakeTimelineText(TEXT("事件进度"),20,ColdSteelUI::TextPrimary,false,true);HeadingLabel->SetJustification(ETextJustify::Center);
    Heading->AddChildToVerticalBox(HeadingLabel);
    TimelineWindowText=MakeTimelineText(TEXT("未来5日 · 暂无事件"),12,ColdSteelUI::TextSecondary);
    TimelineWindowText->SetAutoWrapText(true);TimelineWindowText->SetJustification(ETextJustify::Center);Heading->AddChildToVerticalBox(TimelineWindowText);
    auto* Filters=WidgetTree->ConstructWidget<UHorizontalBox>();TimelineExpandedContent->AddChildToVerticalBox(Filters)->SetPadding(FMargin(0,8/Scale));
    TimelineAllFilterButton=Button(TEXT("全部 0"));TimelineAllFilterText=Cast<UTextBlock>(TimelineAllFilterButton->GetContent());
    TimelineWeatherFilterButton=Button(TEXT("天气 0"));TimelineWeatherFilterText=Cast<UTextBlock>(TimelineWeatherFilterButton->GetContent());
    UButton* FilterButtons[]={TimelineAllFilterButton,TimelineWeatherFilterButton};
    for(int32 I=0;I<2;++I){auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetHeightOverride(36/Scale);Size->SetContent(FilterButtons[I]);TimelineButtonSizes.Add(Size);
        auto* FilterSlot=Filters->AddChildToHorizontalBox(Size);FilterSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));FilterSlot->SetPadding(FMargin(I?2/Scale:0,0,I?0:2/Scale,0));}
    TimelineAllFilterButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineFilterAllClicked);
    TimelineWeatherFilterButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineFilterWeatherClicked);
    TimelineInvasionText=MakeTimelineText(TEXT("暂无入侵情报"),12,ColdSteelUI::TextTertiary);TimelineInvasionText->SetAutoWrapText(true);
    TimelineExpandedContent->AddChildToVerticalBox(TimelineInvasionText)->SetPadding(FMargin(0,0,0,8/Scale));

    TimelineTrackSize=WidgetTree->ConstructWidget<USizeBox>();Column->AddChildToVerticalBox(TimelineTrackSize);
    TimelineTrack=WidgetTree->ConstructWidget<UCanvasPanel>();TimelineTrackSize->SetContent(TimelineTrack);
    TimelineTrack->SetClipping(EWidgetClipping::ClipToBounds);
    TimelineTrackBackground=MakeSurface(ColdSteelUI::Content,6/Scale,FLinearColor::Transparent,0);
    TimelineFill(TimelineTrack->AddChildToCanvas(TimelineTrackBackground),FAnchors(0,0,1,1));
    TimelineCompactTitle=MakeTimelineText(TEXT("事件"),12,ColdSteelUI::TextSecondary);
    TimelineCompactTitle->SetVisibility(ESlateVisibility::HitTestInvisible);
    auto* CompactTitleSlot=TimelineTrack->AddChildToCanvas(TimelineCompactTitle);
    CompactTitleSlot->SetPosition(FVector2D(10/Scale,6/Scale));CompactTitleSlot->SetAutoSize(true);CompactTitleSlot->SetZOrder(5);
    TimelineGradientTexture=UTexture2D::CreateTransient(128,1,PF_B8G8R8A8);
    if(TimelineGradientTexture && TimelineGradientTexture->GetPlatformData())
    {
        auto& Mip=TimelineGradientTexture->GetPlatformData()->Mips[0];auto* Pixels=static_cast<FColor*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
        // game-dev game-style.css .world-invasion-bar: red / yellow / blue / green.
        const FColor Colors[]={FColor(229,65,62),FColor(241,193,63),FColor(65,139,231),FColor(61,196,91)};
        const float Stops[]={0.f,.33f,.66f,1.f};
        for(int32 X=0;X<128;++X)
        {
            const float Position=X/127.f;
            const int32 Segment=Position<=Stops[1]?0:Position<=Stops[2]?1:2;
            const float T=(Position-Stops[Segment])/(Stops[Segment+1]-Stops[Segment]);
            const FColor& From=Colors[Segment];const FColor& To=Colors[Segment+1];
            Pixels[X]=FColor(FMath::RoundToInt(FMath::Lerp(float(From.R),float(To.R),T)),
                FMath::RoundToInt(FMath::Lerp(float(From.G),float(To.G),T)),
                FMath::RoundToInt(FMath::Lerp(float(From.B),float(To.B),T)),255);
        }
        Mip.BulkData.Unlock();TimelineGradientTexture->UpdateResource();LoadedTextures.Add(TimelineGradientTexture);
    }
    TimelineGradient=WidgetTree->ConstructWidget<UImage>();TimelineGradient->SetBrushFromTexture(TimelineGradientTexture,false);
    TimelineFill(TimelineTrack->AddChildToCanvas(TimelineGradient),FAnchors(0,1,1,1),FMargin(0,-3/Scale,0,3/Scale),1);
    TimelineCursorLine=MakeSurface(ColdSteelUI::Accent,0,FLinearColor::Transparent,0);
    TimelineFill(TimelineTrack->AddChildToCanvas(TimelineCursorLine),FAnchors(.04f,0,.04f,1),FMargin(-1/Scale,0,2/Scale,0),3);
    TimelineEventLine=MakeSurface(ColdSteelUI::Accent,0,FLinearColor::Transparent,0);
    TimelineFill(TimelineTrack->AddChildToCanvas(TimelineEventLine),FAnchors(.04f,0,.04f,1),FMargin(-1/Scale,0,2/Scale,0),2);
    TimelineMarkerButton=Button(TEXT(""));TimelineMarkerButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineMarkerClicked);
    auto* MarkerRow=WidgetTree->ConstructWidget<UHorizontalBox>();TimelineMarkerButton->SetContent(MarkerRow);
    TimelineMarkerImage=WidgetTree->ConstructWidget<UImage>();if(auto* T=LoadUiTexture(TEXT("rain-light.png")))TimelineMarkerImage->SetBrushFromTexture(T,true);
    TimelineMarkerIconSize=WidgetTree->ConstructWidget<USizeBox>();TimelineMarkerIconSize->SetContent(TimelineMarkerImage);MarkerRow->AddChildToHorizontalBox(TimelineMarkerIconSize);
    TimelineMarkerTimeText=MakeTimelineText(TEXT(""),12,ColdSteelUI::TextPrimary,true);MarkerRow->AddChildToHorizontalBox(TimelineMarkerTimeText)->SetPadding(FMargin(4/Scale,0,0,0));
    auto* MarkerSlot=TimelineTrack->AddChildToCanvas(TimelineMarkerButton);MarkerSlot->SetAutoSize(true);MarkerSlot->SetZOrder(4);
    TimelineNowText=MakeTimelineText(TEXT("现在"),12,ColdSteelUI::TextSecondary);auto* NowSlot=TimelineTrack->AddChildToCanvas(TimelineNowText);
    NowSlot->SetAnchors(FAnchors(.04f,1));NowSlot->SetAlignment(FVector2D(.04f,0));NowSlot->SetAutoSize(true);NowSlot->SetZOrder(4);

    TimelineToggleSize=WidgetTree->ConstructWidget<USizeBox>();TimelineToggleSize->SetWidthOverride(56/Scale);TimelineToggleSize->SetHeightOverride(24/Scale);
    Column->AddChildToVerticalBox(TimelineToggleSize)->SetHorizontalAlignment(HAlign_Center);
    TimelineToggleButton=Button(TEXT(""));TimelineToggleButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineToggleClicked);TimelineToggleSize->SetContent(TimelineToggleButton);
    TimelineToggleGlyphSize=WidgetTree->ConstructWidget<USizeBox>();TimelineToggleGlyphSize->SetWidthOverride(14/Scale);TimelineToggleGlyphSize->SetHeightOverride(12/Scale);
    TimelineToggleGlyph=WidgetTree->ConstructWidget<UCanvasPanel>();TimelineToggleGlyphSize->SetContent(TimelineToggleGlyph);TimelineToggleButton->SetContent(TimelineToggleGlyphSize);
    if(auto* S=Cast<UButtonSlot>(TimelineToggleGlyphSize->Slot)){S->SetPadding(FMargin(0));S->SetHorizontalAlignment(HAlign_Center);S->SetVerticalAlignment(VAlign_Center);}
    for(int32 I=0;I<2;++I){auto* Line=MakeSurface(ColdSteelUI::Accent,1/Scale,FLinearColor::Transparent,0);Line->SetRenderTransformAngle(I?-45:45);
        auto* S=TimelineToggleGlyph->AddChildToCanvas(Line);S->SetPosition(FVector2D((I?5:0)/Scale,4/Scale));S->SetSize(FVector2D(9/Scale,2/Scale));}

    // The compact track stays beside the clock; expanded content opens DOWNWARD.
    Column->RemoveChild(TimelineExpandedClip);
    Column->AddChildToVerticalBox(TimelineExpandedClip);

    TimelinePopover=WidgetTree->ConstructWidget<UBorder>();TimelinePopover->SetBrush(Empty);TimelinePopover->SetPadding(FMargin(0));TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
    auto* PopSlot=Root->AddChildToCanvas(TimelinePopover);PopSlot->SetAnchors(FAnchors(0,0));PopSlot->SetAlignment(FVector2D(0,0));PopSlot->SetZOrder(29);
    TimelineDetailBlur=Glass();TimelinePopover->SetContent(TimelineDetailBlur);
    TimelineDetailSurface=MakeSurface(ColdSteelUI::GlassTint,10/Scale,ColdSteelUI::Border,1/Scale);TimelineDetailSurface->SetPadding(FMargin(12/Scale));TimelineDetailBlur->SetContent(TimelineDetailSurface);
    auto* DetailColumn=WidgetTree->ConstructWidget<UVerticalBox>();TimelineDetailSurface->SetContent(DetailColumn);
    auto* DetailHeading=WidgetTree->ConstructWidget<UHorizontalBox>();DetailColumn->AddChildToVerticalBox(DetailHeading)->SetPadding(FMargin(0,0,0,8/Scale));
    auto* HeadingBalance=WidgetTree->ConstructWidget<USizeBox>();HeadingBalance->SetWidthOverride(72/Scale);DetailHeading->AddChildToHorizontalBox(HeadingBalance);
    TimelinePopoverTitle=MakeTimelineText(TEXT("事件详情"),20,ColdSteelUI::TextPrimary,false,true);
    TimelinePopoverTitle->SetJustification(ETextJustify::Center);
    auto* TitleSlot=DetailHeading->AddChildToHorizontalBox(TimelinePopoverTitle);TitleSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TitleSlot->SetVerticalAlignment(VAlign_Center);
    TimelineDetailsClose=Button(TEXT("关闭"));TimelineDetailsClose->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineDetailsCloseClicked);
    auto* CloseSize=WidgetTree->ConstructWidget<USizeBox>();CloseSize->SetWidthOverride(72/Scale);CloseSize->SetHeightOverride(36/Scale);CloseSize->SetContent(TimelineDetailsClose);TimelineButtonSizes.Add(CloseSize);
    DetailHeading->AddChildToHorizontalBox(CloseSize);
    TimelineDetailScroll=WidgetTree->ConstructWidget<UScrollBox>();TimelineDetailScroll->SetAllowOverscroll(false);TimelineDetailScroll->SetScrollbarThickness(FVector2D(6/Scale));
    DetailColumn->AddChildToVerticalBox(TimelineDetailScroll)->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
    TimelineDetailContent=WidgetTree->ConstructWidget<UVerticalBox>();TimelineDetailScroll->AddChild(TimelineDetailContent);
    SetEventTimelineCompact(true);UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::TickEventTimelinePresentation(float Delta)
{
    TimelineExpansion=FMath::FInterpConstantTo(TimelineExpansion,bTimelineCompact?0.f:1.f,Delta,1/.16f);
    TimelineDetailMotion=FMath::FInterpConstantTo(TimelineDetailMotion,bTimelineDetailsOpen?1.f:0.f,Delta,1/.16f);
    if(!FMath::IsNearlyEqual(TimelineEventFraction,TimelineEventMoveTarget,1.e-7f))
    {TimelineEventMoveFrom=TimelineShownEventFraction;TimelineEventMoveTarget=TimelineEventFraction;TimelineEventMoveTime=0;}
    TimelineEventMoveTime=FMath::Min(.18f,TimelineEventMoveTime+Delta);
    TimelineShownEventFraction=FMath::Lerp(TimelineEventMoveFrom,TimelineEventMoveTarget,TimelineEventMoveTime/.18f);
    UpdateEventTimelineLayout();
}

void UColdSteelHUDWidget::UpdateEventTimelineLayout()
{
    if(!TimelineWidthBox || !TimelineExpandedClip)return;
    const float S=ColdSteelUI::PixelScale(this),A=TimelineCSSEase(TimelineExpansion),D=TimelineCSSEase(TimelineDetailMotion);
    FVector2D View=GetCachedGeometry().GetLocalSize();if(View.X<100 || View.Y<100)View=UWidgetLayoutLibrary::GetViewportSize(this)/S;
    if(View.X<100 || View.Y<100)View=FVector2D(1280,720)/S;
    const bool ScaleChanged=!FMath::IsNearlyEqual(TimelineScale,S,.001f);TimelineScale=S;
    const FColdSteelHUDLayout Layout(View.X*S);
    const float Top=Layout.CornerTop/S;
    const float EventRight=(Layout.EventLeft+Layout.CornerWidth)/S;
    // Keep the clock-sized top row fixed even while its details reveal below it.
    const float TrackWidthFixed=Layout.CornerWidth/S;
    const float EventCenter=EventRight-TrackWidthFixed*.5f;
    // Preserve the track anchor and symmetric expansion without leaving a narrow viewport.
    const float SymmetricSpace=2*FMath::Min(EventCenter-12/S,float(View.X)-12/S-EventCenter);
    const float ExpandedWidth=FMath::Max(TrackWidthFixed,FMath::Min(360/S,SymmetricSpace));
    const float Width=FMath::Lerp(TrackWidthFixed,ExpandedWidth,A);
    const float Left=EventRight-TrackWidthFixed-(Width-TrackWidthFixed)*.5f;
    Cast<UCanvasPanelSlot>(TimelineWidthBox->Slot)->SetPosition(FVector2D(Left,Top));
    TimelineWidthBox->SetWidthOverride(Width);
    // Widen the lower details equally on both sides; the clock-sized track stays put.
    TimelineTrackSize->SetWidthOverride(TrackWidthFixed);
    Cast<UVerticalBoxSlot>(TimelineTrackSize->Slot)->SetHorizontalAlignment(HAlign_Center);
    Cast<UOverlaySlot>(TimelineShellBlur->Slot)->SetPadding(FMargin(0,Layout.CornerHeight/S,0,0));
    const bool Revealing=TimelineExpansion>0 || !bTimelineCompact;
    TimelineShellBlur->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineShellBlur->SetRenderOpacity(A);
    TimelinePanel->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    TimelineExpandedClip->SetVisibility(Revealing?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
    TimelineExpandedClip->SetIsEnabled(!bTimelineCompact && TimelineExpansion>=1);
    TimelineExpandedContent->SetVisibility(Revealing?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);TimelineExpandedContent->SetRenderOpacity(A);
    const float Wanted=FMath::Max(112/S,float(TimelineExpandedContent->GetDesiredSize().Y));
    const float RevealHeight=FMath::Min(Wanted,FMath::Max(32/S,float(View.Y)-Top-124/S));
    TimelineExpandedClip->SetHeightOverride(RevealHeight*A);
    const float PadX=0,PadY=0,Bottom=10*A/S;
    TimelineContentPadding->SetPadding(FMargin(PadX,PadY,PadX,Bottom));
    Cast<UVerticalBoxSlot>(TimelineExpandedClip->Slot)->SetPadding(FMargin(12*A/S,8*A/S,12*A/S,0));
    const float TrackHeight=Layout.CornerHeight/S,BodyHeight=TrackHeight-16/S;
    TimelineTrackSize->SetHeightOverride(TrackHeight);
    Cast<UCanvasPanelSlot>(TimelineTrackBackground->Slot)->SetOffsets(FMargin(0));
    const float Stripe=FMath::Lerp(3.f,4.f,A)/S;
    // Keep the rainbow inside the unchanged 72px rounded body in BOTH states.
    Cast<UCanvasPanelSlot>(TimelineGradient->Slot)->SetOffsets(FMargin(12/S,-8/S-Stripe,12/S,Stripe));
    const float TrackInset=12/S;
    const float InnerTrackWidth=FMath::Max(1.f,TrackWidthFixed-2*TrackInset);
    auto* CursorSlot=Cast<UCanvasPanelSlot>(TimelineCursorLine->Slot);CursorSlot->SetAnchors(FAnchors(0,0,0,1));CursorSlot->SetOffsets(FMargin(TrackInset+InnerTrackWidth*.04f-.5f/S,22/S,1/S,8/S+Stripe));
    auto* EventSlot=Cast<UCanvasPanelSlot>(TimelineEventLine->Slot);EventSlot->SetAnchors(FAnchors(0,0,0,1));EventSlot->SetOffsets(FMargin(TrackInset+InnerTrackWidth*TimelineShownEventFraction-.5f/S,22/S,1/S,8/S+Stripe));
    const float IconSize=FMath::Lerp(18.f,22.f,A)/S;
    TimelineMarkerIconSize->SetWidthOverride(IconSize);TimelineMarkerIconSize->SetHeightOverride(IconSize);TimelineMarkerImage->SetDesiredSizeOverride(FVector2D(IconSize));
    TimelineMarkerTimeText->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineMarkerTimeText->SetRenderOpacity(A);
    TimelineNowText->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineNowText->SetRenderOpacity(A);
    auto* NowSlot=Cast<UCanvasPanelSlot>(TimelineNowText->Slot);NowSlot->SetAnchors(FAnchors(1,0));NowSlot->SetAlignment(FVector2D(1,0));NowSlot->SetPosition(FVector2D(-TrackInset,6/S));
    auto* MarkerSlot=Cast<UCanvasPanelSlot>(TimelineMarkerButton->Slot);MarkerSlot->SetAnchors(FAnchors(0,0));MarkerSlot->SetAlignment(FVector2D::ZeroVector);
    const float TrackWidth=InnerTrackWidth,MarkerWidth=FMath::Min(TrackWidth,FMath::Max(IconSize,float(TimelineMarkerButton->GetDesiredSize().X)));
    const float Align=TimelineShownEventFraction<=.08f?.08f:TimelineShownEventFraction>=.92f?.92f:.5f;
    MarkerSlot->SetPosition(FVector2D(TrackInset+FMath::Clamp(TrackWidth*TimelineShownEventFraction-MarkerWidth*Align,0.f,FMath::Max(0.f,TrackWidth-MarkerWidth)),FMath::Max(22/S,(BodyHeight-IconSize)/2)));
    TimelineToggleGlyph->SetRenderTransformAngle(180*A);
    const float PanelHeight=PadY+RevealHeight*A+TrackHeight+24/S+Bottom+8*A/S;
    const float PopWidth=FMath::Min(520/S,FMath::Max(1.f,float(View.X)-24/S));
    const float PopY=FMath::Min(Top+PanelHeight+8/S,FMath::Max(12/S,float(View.Y)-140/S));
    const float PopHeight=FMath::Max(1.f,FMath::Min(420/S,float(View.Y)-PopY-12/S));
    auto* PopSlot=Cast<UCanvasPanelSlot>(TimelinePopover->Slot);PopSlot->SetPosition(FVector2D(FMath::Clamp(Left+(Width-PopWidth)*.5f,12/S,FMath::Max(12/S,float(View.X)-PopWidth-12/S)),PopY));PopSlot->SetSize(FVector2D(PopWidth,PopHeight));
    const bool DrawerOut=bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen;
    TimelineWidthBox->SetVisibility(DrawerOut?ESlateVisibility::Collapsed:ESlateVisibility::SelfHitTestInvisible);
    TimelinePopover->SetVisibility(!DrawerOut&&(TimelineDetailMotion>0 || bTimelineDetailsOpen)?(bTimelineDetailsOpen?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible):ESlateVisibility::Collapsed);
    TimelinePopover->SetRenderOpacity(D);TimelinePopover->SetRenderTranslation(FVector2D(0,4*(1-D)/S));
    const bool DetailNarrowChanged=(TimelineDetailWidth<440)!=(PopWidth*S<440);TimelineDetailWidth=PopWidth*S;
    if(ScaleChanged)
    {
        Cast<UCanvasPanelSlot>(TimelineCompactTitle->Slot)->SetPosition(FVector2D(10/S,6/S));
        TimelineLabels.RemoveAll([](const FInventoryLabel& E){return !E.Widget.IsValid();});
        for(const auto& E:TimelineLabels)if(auto* T=E.Widget.Get())T->SetFont(E.Numeric?ColdSteelUI::NumberFont(E.Pixels*.75f/S,E.Medium):ColdSteelUI::TextFont(E.Pixels*.75f/S,E.Medium));
        TimelinePanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));
        TimelineDetailSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));TimelineDetailSurface->SetPadding(FMargin(12/S));
        TimelineTrackBackground->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));
        for(auto* B:{TimelineShellBlur.Get(),TimelineDetailBlur.Get()}){B->SetCornerRadius(FVector4(10/S));B->SetLowQualityFallbackBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassFallback,10/S));}
        for(auto* Sc:{TimelineExpandedScroll.Get(),TimelineDetailScroll.Get()})Sc->SetScrollbarThickness(FVector2D(6/S));
        for(auto* B:{TimelineToggleButton.Get(),TimelineDetailsClose.Get()})B->SetStyle(ColdSteelUI::ButtonStyle(S));
        auto MarkerStyle=ColdSteelUI::ButtonStyle(S);MarkerStyle.SetNormal(ColdSteelUI::RoundedBrush(FLinearColor::Transparent,6/S,FLinearColor::Transparent,0));TimelineMarkerButton->SetStyle(MarkerStyle);
        if(auto* MarkerContentSlot=Cast<UButtonSlot>(TimelineMarkerButton->GetContent()->Slot)){MarkerContentSlot->SetPadding(FMargin(2/S));MarkerContentSlot->SetVerticalAlignment(VAlign_Center);}
        for(const auto& Size:TimelineButtonSizes)Size->SetHeightOverride(36/S);
        if(TimelineButtonSizes.Num()>2)TimelineButtonSizes.Last()->SetWidthOverride(72/S);
        UButton* Filters[]={TimelineAllFilterButton,TimelineWeatherFilterButton};
        for(int32 I=0;I<2;++I)
        {
            if(auto* ContentSlot=Cast<UButtonSlot>(Filters[I]->GetContent()->Slot))ContentSlot->SetPadding(FMargin(8/S,2/S));
            if(auto* FilterSlot=Cast<UHorizontalBoxSlot>(TimelineButtonSizes[I]->Slot))FilterSlot->SetPadding(FMargin(I?2/S:0,0,I?0:2/S,0));
        }
        if(auto* FiltersSlot=Cast<UVerticalBoxSlot>(TimelineButtonSizes[0]->GetParent()->Slot))FiltersSlot->SetPadding(FMargin(0,8/S));
        if(auto* InvasionSlot=Cast<UVerticalBoxSlot>(TimelineInvasionText->Slot))InvasionSlot->SetPadding(FMargin(0,0,0,8/S));
        if(auto* TimeSlot=Cast<UHorizontalBoxSlot>(TimelineMarkerTimeText->Slot))TimeSlot->SetPadding(FMargin(4/S,0,0,0));
        if(auto* HeadingSlot=Cast<UVerticalBoxSlot>(TimelinePopoverTitle->GetParent()->Slot))HeadingSlot->SetPadding(FMargin(0,0,0,8/S));
        if(auto* HeadingRow=Cast<UHorizontalBox>(TimelinePopoverTitle->GetParent()))if(auto* Balance=Cast<USizeBox>(HeadingRow->GetChildAt(0)))Balance->SetWidthOverride(72/S);
        if(auto* CloseSlot=Cast<UButtonSlot>(TimelineDetailsClose->GetContent()->Slot))CloseSlot->SetPadding(FMargin(8/S,2/S));
        TimelineToggleSize->SetWidthOverride(56/S);TimelineToggleSize->SetHeightOverride(24/S);TimelineToggleGlyphSize->SetWidthOverride(14/S);TimelineToggleGlyphSize->SetHeightOverride(12/S);
        for(int32 I=0;I<TimelineToggleGlyph->GetChildrenCount();++I){auto* Line=Cast<UBorder>(TimelineToggleGlyph->GetChildAt(I));Line->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Accent,1/S,FLinearColor::Transparent,0));auto* GlyphSlot=Cast<UCanvasPanelSlot>(Line->Slot);GlyphSlot->SetPosition(FVector2D((I?5:0)/S,4/S));GlyphSlot->SetSize(FVector2D(9/S,2/S));}
        UpdateEventTimelineFilterButtons();
    }
    if(ScaleChanged || DetailNarrowChanged)RebuildEventDetails();
}

void UColdSteelHUDWidget::UpdateEventTimelineFilterButtons()
{
    const float S=ColdSteelUI::PixelScale(this);UButton* Buttons[]={TimelineAllFilterButton,TimelineWeatherFilterButton};
    for(int32 I=0;I<2;++I)if(Buttons[I]){auto Style=ColdSteelUI::ButtonStyle(S);if(bTimelineWeatherFilter==(I==1))Style.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6/S,ColdSteelUI::Accent,1/S));Buttons[I]->SetStyle(Style);}
}
void UColdSteelHUDWidget::SetEventTimelineCompact(bool Compact)
{
    bTimelineCompact=Compact;
    if(TimelineToggleButton)TimelineToggleButton->SetToolTipText(FText::FromString(Compact?TEXT("展开事件进度详情"):TEXT("收起事件进度详情")));
    if(Compact){bTimelineDetailsOpen=false;TimelineDetailMotion=0;if(TimelinePopover)TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);}
    if(TimelineExpandedContent && !Compact){TimelineExpandedContent->SetVisibility(ESlateVisibility::SelfHitTestInvisible);TimelineExpandedContent->ForceLayoutPrepass();}
    UpdateEventTimelineLayout();
}
void UColdSteelHUDWidget::SetTimelineDetailsOpen(bool Open)
{
    bTimelineDetailsOpen=Open && bTimelineHasEvent;
    if(bTimelineDetailsOpen && bTimelineCompact)SetEventTimelineCompact(false);
    UpdateEventTimelineLayout();
}
