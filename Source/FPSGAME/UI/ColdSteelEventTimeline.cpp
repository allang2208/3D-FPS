#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
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
    auto* RootSlot=Root->AddChildToCanvas(TimelineWidthBox);RootSlot->SetAnchors(FAnchors(.5f,0));RootSlot->SetAlignment(FVector2D(.5f,0));
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
    Heading->AddChildToVerticalBox(MakeTimelineText(TEXT("事件进度"),20,ColdSteelUI::TextPrimary,false,true));
    TimelineWindowText=MakeTimelineText(TEXT("未来5日 · 暂无事件"),12,ColdSteelUI::TextSecondary);
    TimelineWindowText->SetAutoWrapText(true);Heading->AddChildToVerticalBox(TimelineWindowText);
    auto* Filters=WidgetTree->ConstructWidget<UHorizontalBox>();TimelineExpandedContent->AddChildToVerticalBox(Filters)->SetPadding(FMargin(0,8/Scale));
    TimelineAllFilterButton=Button(TEXT("全部 0"));TimelineAllFilterText=Cast<UTextBlock>(TimelineAllFilterButton->GetContent());
    TimelineWeatherFilterButton=Button(TEXT("天气 0"));TimelineWeatherFilterText=Cast<UTextBlock>(TimelineWeatherFilterButton->GetContent());
    UButton* FilterButtons[]={TimelineAllFilterButton,TimelineWeatherFilterButton};
    for(int32 I=0;I<2;++I){auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetHeightOverride(36/Scale);Size->SetContent(FilterButtons[I]);TimelineButtonSizes.Add(Size);
        auto* FilterSlot=Filters->AddChildToHorizontalBox(Size);FilterSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));FilterSlot->SetPadding(FMargin(I?4/Scale:0,0,0,0));}
    TimelineAllFilterButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineFilterAllClicked);
    TimelineWeatherFilterButton->OnClicked.AddDynamic(this,&ThisClass::HandleTimelineFilterWeatherClicked);
    TimelineInvasionText=MakeTimelineText(TEXT("暂无入侵情报"),12,ColdSteelUI::TextTertiary);TimelineInvasionText->SetAutoWrapText(true);
    TimelineExpandedContent->AddChildToVerticalBox(TimelineInvasionText)->SetPadding(FMargin(0,0,0,8/Scale));

    TimelineTrackSize=WidgetTree->ConstructWidget<USizeBox>();Column->AddChildToVerticalBox(TimelineTrackSize);
    TimelineTrack=WidgetTree->ConstructWidget<UCanvasPanel>();TimelineTrackSize->SetContent(TimelineTrack);
    TimelineTrackBackground=MakeSurface(ColdSteelUI::Content,6/Scale,FLinearColor::Transparent,0);
    TimelineFill(TimelineTrack->AddChildToCanvas(TimelineTrackBackground),FAnchors(0,0,1,1));
    TimelineGradientTexture=UTexture2D::CreateTransient(128,1,PF_B8G8R8A8);
    if(TimelineGradientTexture && TimelineGradientTexture->GetPlatformData())
    {
        auto& Mip=TimelineGradientTexture->GetPlatformData()->Mips[0];auto* Pixels=static_cast<FColor*>(Mip.BulkData.Lock(LOCK_READ_WRITE));
        for(int32 X=0;X<128;++X)Pixels[X]=FColor(FMath::RoundToInt(FMath::Lerp(214.f,90.f,X/127.f)),FMath::RoundToInt(FMath::Lerp(214.f,90.f,X/127.f)),FMath::RoundToInt(FMath::Lerp(214.f,90.f,X/127.f)),255);
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

    TimelinePopover=WidgetTree->ConstructWidget<UBorder>();TimelinePopover->SetBrush(Empty);TimelinePopover->SetPadding(FMargin(0));TimelinePopover->SetVisibility(ESlateVisibility::Collapsed);
    auto* PopSlot=Root->AddChildToCanvas(TimelinePopover);PopSlot->SetAnchors(FAnchors(.5f,0));PopSlot->SetAlignment(FVector2D(.5f,0));PopSlot->SetZOrder(29);
    TimelineDetailBlur=Glass();TimelinePopover->SetContent(TimelineDetailBlur);
    TimelineDetailSurface=MakeSurface(ColdSteelUI::GlassTint,10/Scale,ColdSteelUI::Border,1/Scale);TimelineDetailSurface->SetPadding(FMargin(12/Scale));TimelineDetailBlur->SetContent(TimelineDetailSurface);
    auto* DetailColumn=WidgetTree->ConstructWidget<UVerticalBox>();TimelineDetailSurface->SetContent(DetailColumn);
    auto* DetailHeading=WidgetTree->ConstructWidget<UHorizontalBox>();DetailColumn->AddChildToVerticalBox(DetailHeading)->SetPadding(FMargin(0,0,0,8/Scale));
    TimelinePopoverTitle=MakeTimelineText(TEXT("事件详情"),20,ColdSteelUI::TextPrimary,false,true);
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
    float Top=76/S;
    if(TopHUDBottom>0)Top=FMath::Max(Top,TopHUDBottom+8/S);
    else if(TopVitalsSurface){const auto& G=TopVitalsSurface->GetCachedGeometry();if(G.GetLocalSize().Y>0)Top=FMath::Max(Top,float(GetCachedGeometry().AbsoluteToLocal(G.LocalToAbsolute(G.GetLocalSize())).Y)+8/S);}
    Top=FMath::Min(Top,FMath::Max(12/S,float(View.Y)-84/S));
    Cast<UCanvasPanelSlot>(TimelineWidthBox->Slot)->SetPosition(FVector2D(0,Top));
    const float Width=FMath::Min(FMath::Lerp(360.f,560.f,A)/S,FMath::Max(1.f,float(View.X)-24/S));
    TimelineWidthBox->SetWidthOverride(Width);
    const bool Revealing=TimelineExpansion>0 || !bTimelineCompact;
    TimelineShellBlur->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineShellBlur->SetRenderOpacity(A);
    TimelinePanel->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    TimelineExpandedClip->SetVisibility(Revealing?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);
    TimelineExpandedClip->SetIsEnabled(!bTimelineCompact && TimelineExpansion>=1);
    TimelineExpandedContent->SetVisibility(Revealing?ESlateVisibility::SelfHitTestInvisible:ESlateVisibility::Collapsed);TimelineExpandedContent->SetRenderOpacity(A);
    const float Wanted=FMath::Max(112/S,float(TimelineExpandedContent->GetDesiredSize().Y));
    const float RevealHeight=FMath::Min(Wanted,FMath::Max(32/S,float(View.Y)-Top-124/S));
    TimelineExpandedClip->SetHeightOverride(RevealHeight*A);
    const float PadX=FMath::Lerp(3.f,12.f,A)/S,PadY=12*A/S,Bottom=10*A/S;
    TimelineContentPadding->SetPadding(FMargin(PadX,PadY,PadX,Bottom));
    const float TrackHeight=FMath::Lerp(30.f,52.f,A)/S,LabelSpace=18*A/S,BodyHeight=TrackHeight-LabelSpace;
    TimelineTrackSize->SetHeightOverride(TrackHeight);
    Cast<UCanvasPanelSlot>(TimelineTrackBackground->Slot)->SetOffsets(FMargin(0,0,0,LabelSpace));
    const float Stripe=FMath::Lerp(3.f,4.f,A)/S;
    Cast<UCanvasPanelSlot>(TimelineGradient->Slot)->SetOffsets(FMargin(0,-LabelSpace-Stripe,0,Stripe));
    auto* CursorSlot=Cast<UCanvasPanelSlot>(TimelineCursorLine->Slot);CursorSlot->SetOffsets(FMargin(-.5f/S,1/S,1/S,LabelSpace));
    auto* EventSlot=Cast<UCanvasPanelSlot>(TimelineEventLine->Slot);EventSlot->SetAnchors(FAnchors(TimelineShownEventFraction,0,TimelineShownEventFraction,1));EventSlot->SetOffsets(FMargin(-.5f/S,1/S,1/S,LabelSpace));
    const float IconSize=FMath::Lerp(18.f,22.f,A)/S;
    TimelineMarkerIconSize->SetWidthOverride(IconSize);TimelineMarkerIconSize->SetHeightOverride(IconSize);TimelineMarkerImage->SetDesiredSizeOverride(FVector2D(IconSize));
    TimelineMarkerTimeText->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineMarkerTimeText->SetRenderOpacity(A);
    TimelineNowText->SetVisibility(Revealing?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);TimelineNowText->SetRenderOpacity(A);
    Cast<UCanvasPanelSlot>(TimelineNowText->Slot)->SetPosition(FVector2D(0,-LabelSpace+3/S));
    auto* MarkerSlot=Cast<UCanvasPanelSlot>(TimelineMarkerButton->Slot);MarkerSlot->SetAnchors(FAnchors(0,0));MarkerSlot->SetAlignment(FVector2D::ZeroVector);
    const float TrackWidth=FMath::Max(1.f,Width-2*PadX),MarkerWidth=FMath::Min(TrackWidth,FMath::Max(IconSize,float(TimelineMarkerButton->GetDesiredSize().X)));
    const float Align=TimelineShownEventFraction<=.08f?.08f:TimelineShownEventFraction>=.92f?.92f:.5f;
    MarkerSlot->SetPosition(FVector2D(FMath::Clamp(TrackWidth*TimelineShownEventFraction-MarkerWidth*Align,0.f,FMath::Max(0.f,TrackWidth-MarkerWidth)),FMath::Max(1/S,(BodyHeight-IconSize)/2)));
    TimelineToggleGlyph->SetRenderTransformAngle(180*A);
    const float PanelHeight=PadY+RevealHeight*A+TrackHeight+24/S+Bottom;
    const float PopWidth=FMath::Min(520/S,FMath::Max(1.f,float(View.X)-24/S));
    const float PopY=FMath::Min(Top+PanelHeight+8/S,FMath::Max(12/S,float(View.Y)-140/S));
    const float PopHeight=FMath::Max(1.f,FMath::Min(420/S,float(View.Y)-PopY-12/S));
    auto* PopSlot=Cast<UCanvasPanelSlot>(TimelinePopover->Slot);PopSlot->SetPosition(FVector2D(0,PopY));PopSlot->SetSize(FVector2D(PopWidth,PopHeight));
    TimelinePopover->SetVisibility(TimelineDetailMotion>0 || bTimelineDetailsOpen?(bTimelineDetailsOpen?ESlateVisibility::Visible:ESlateVisibility::HitTestInvisible):ESlateVisibility::Collapsed);
    TimelinePopover->SetRenderOpacity(D);TimelinePopover->SetRenderTranslation(FVector2D(0,4*(1-D)/S));
    const bool DetailNarrowChanged=(TimelineDetailWidth<440)!=(PopWidth*S<440);TimelineDetailWidth=PopWidth*S;
    if(ScaleChanged)
    {
        TimelineLabels.RemoveAll([](const FInventoryLabel& E){return !E.Widget.IsValid();});
        for(const auto& E:TimelineLabels)if(auto* T=E.Widget.Get())T->SetFont(E.Numeric?ColdSteelUI::NumberFont(E.Pixels*.75f/S,E.Medium):ColdSteelUI::TextFont(E.Pixels*.75f/S,E.Medium));
        TimelinePanel->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));
        TimelineDetailSurface->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::GlassTint,10/S,ColdSteelUI::Border,1/S));TimelineDetailSurface->SetPadding(FMargin(12/S));
        TimelineTrackBackground->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,6/S,FLinearColor::Transparent,0));
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
            if(auto* FilterSlot=Cast<UHorizontalBoxSlot>(TimelineButtonSizes[I]->Slot))FilterSlot->SetPadding(FMargin(I?4/S:0,0,0,0));
        }
        if(auto* FiltersSlot=Cast<UVerticalBoxSlot>(TimelineButtonSizes[0]->GetParent()->Slot))FiltersSlot->SetPadding(FMargin(0,8/S));
        if(auto* InvasionSlot=Cast<UVerticalBoxSlot>(TimelineInvasionText->Slot))InvasionSlot->SetPadding(FMargin(0,0,0,8/S));
        if(auto* TimeSlot=Cast<UHorizontalBoxSlot>(TimelineMarkerTimeText->Slot))TimeSlot->SetPadding(FMargin(4/S,0,0,0));
        if(auto* HeadingSlot=Cast<UVerticalBoxSlot>(TimelinePopoverTitle->GetParent()->Slot))HeadingSlot->SetPadding(FMargin(0,0,0,8/S));
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
