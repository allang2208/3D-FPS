#include "ColdSteelAcquisitionFeed.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/SlateRenderer.h"
#include "Rendering/DrawElements.h"
#include "Kismet/GameplayStatics.h"

namespace { constexpr float FeedPitch=FColdSteelAcquisitionTimeline::Pitch,FeedLife=FColdSteelAcquisitionTimeline::Life,FeedFade=FColdSteelAcquisitionTimeline::Fade; }

void UColdSteelAcquisitionFeed::NativeOnInitialized()
{
    Super::NativeOnInitialized();SetIsFocusable(false);SetClipping(EWidgetClipping::ClipToBounds);
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<UCanvasPanel>();
    SetLayout(ColdSteelUI::PixelScale(this),360,PreferredHeight);UpdateVisibility();
}
void UColdSteelAcquisitionFeed::NativeConstruct()
{
    Super::NativeConstruct();Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(Model){Model->SetAcquisitionFeedEnabled(true);Epoch=Model->AcquisitionNoticeEpoch();}
}
void UColdSteelAcquisitionFeed::NativeDestruct()
{
    if(Model)Model->SetAcquisitionFeedEnabled(false);
    Timeline.Reset();Model=nullptr;Super::NativeDestruct();
}
void UColdSteelAcquisitionFeed::SetLayout(float PixelScale,float PixelWidth,float PixelHeight)
{
    Scale=FMath::Max(.01f,PixelScale);Width=FMath::Max(1.f,PixelWidth);Height=FMath::Max(0.f,PixelHeight);
    MaxLines=FMath::Clamp(FMath::FloorToInt((Height-24.f)/FeedPitch),0,5);
    TextFont=ColdSteelUI::TextFont(14*.75f/Scale);
    NumberFont=ColdSteelUI::NumberFont(14*.75f/Scale,true);
    for(auto& Line:Timeline.Lines)PrepareLine(Line);
    UpdateVisibility();
}
void UColdSteelAcquisitionFeed::SetPresentationSuppressed(bool Suppressed)
{if(bSuppressed!=Suppressed){bSuppressed=Suppressed;UpdateVisibility();}}
void UColdSteelAcquisitionFeed::UpdateVisibility()
{SetVisibility(bSuppressed||MaxLines<=0?ESlateVisibility::Hidden:ESlateVisibility::HitTestInvisible);}
void UColdSteelAcquisitionFeed::PrepareLine(FLine& Line)
{
    Line.bTextChanged=false;
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    Line.Quantity=TEXT("× ")+FText::AsNumber(Line.Notice.Count).ToString();
    Line.NameX=10+float(Measure->Measure(TEXT("获得"),TextFont).X)*Scale+9;
    Line.QuantityX=FMath::Max(Line.NameX,Width-6-float(Measure->Measure(Line.Quantity,NumberFont).X)*Scale);
    const float Available=FMath::Max(0.f,Line.QuantityX-Line.NameX-12);
    Line.DisplayName=ColdSteelUI::Ellipsize(Line.Notice.Name,TextFont,Available/Scale,*Measure);
}
void UColdSteelAcquisitionFeed::NativeTick(const FGeometry& G,float Delta)
{
    Super::NativeTick(G,Delta);
    if(!Model||bSuppressed||MaxLines<=0||UGameplayStatics::IsGamePaused(this))return;
    const bool HadLines=!Timeline.Lines.IsEmpty();
    if(Epoch!=Model->AcquisitionNoticeEpoch())
    {Epoch=Model->AcquisitionNoticeEpoch();Timeline.Reset();}
    const bool Changed=Timeline.Advance(Delta,MaxLines,[&](auto& Notice,const auto& Key){return Model->PopAcquisitionNotice(Notice,Key);});
    for(auto& Line:Timeline.Lines)if(Line.bTextChanged)PrepareLine(Line);
    if(HadLines||Changed)if(auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);
}
int32 UColdSteelAcquisitionFeed::NativePaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Clip,
    FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled)const
{
    Layer=Super::NativePaint(Args,G,Clip,Out,Layer,Style,Enabled);
    const auto Tint=Style.GetColorAndOpacityTint();
    auto DrawText=[&](const FString& Caption,float X,float Y,const FSlateFontInfo& Font,FLinearColor Color,float Alpha)
    {
        Color*=Tint;Color.A*=Alpha;
        const auto Geometry=G.ToPaintGeometry(FVector2D(Width,22)/Scale,FSlateLayoutTransform(FVector2D(X,Y)/Scale));
        const auto Shadow=G.ToPaintGeometry(FVector2D(Width,22)/Scale,FSlateLayoutTransform(FVector2D(X+1,Y+1)/Scale));
        FSlateDrawElement::MakeText(Out,Layer+1,Shadow,Caption,Font,ESlateDrawEffect::None,FLinearColor(0,0,0,.85f*Color.A));
        FSlateDrawElement::MakeText(Out,Layer+2,Geometry,Caption,Font,ESlateDrawEffect::None,Color);
    };
    for(int32 Index=0;Index<FMath::Min(MaxLines,Timeline.Lines.Num());++Index)
    {
        const auto& Line=Timeline.Lines[Index];
        const float Alpha=FMath::Min(FMath::Clamp(Line.Age/.16f,0.f,1.f),FMath::Clamp((FeedLife-Line.Age)/FeedFade,0.f,1.f));
        const float Y=Height-22.f+Line.Y;
        DrawText(TEXT("获得"),10,Y,TextFont,ColdSteelUI::HUDGoldLight,Alpha);
        DrawText(Line.DisplayName,Line.NameX,Y,TextFont,Line.Notice.Color,Alpha);
        DrawText(Line.Quantity,Line.QuantityX,Y,NumberFont,ColdSteelUI::HUDGoldLight,Alpha);
    }
    return Layer+2;
}
