#include "ColdSteelExperienceFeed.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelBowResonance.h"
#include "ColdSteelStarMarrow.h"
#include "../Weapons/StarMarrowComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowScopeOptics.h"
#include "../Weapons/Bow/BowMountainEchoComponent.h"
#include "../Weapons/Bow/BowCadenceComponent.h"
#include "GameFramework/Pawn.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"

namespace
{
constexpr float XpFeedLife=1.65f;
constexpr float XpFeedFadeIn=.12f;
constexpr float XpFeedFadeOut=.38f;
constexpr float XpFeedPitch=38.f;
constexpr float XpFeedRise=9.f;
constexpr float XpFeedBaseOffset=96.f;
constexpr float XpFeedAdmissionInterval=.15f;
constexpr float XpFeedTextGap=6.f;
constexpr float XpFeedFramePadX=4.f;
constexpr float XpFeedFramePadY=3.f;
constexpr float XpFeedFrameThickness=1.5f;
constexpr int32 XpFeedMaxLines=3;
}

void UColdSteelExperienceFeed::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    SetClipping(EWidgetClipping::ClipToBounds);
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
    RefreshMetrics();
    UpdateVisibility();
}

void UColdSteelExperienceFeed::NativeConstruct()
{
    Super::NativeConstruct();
    Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    UpdateVisibility();
}

void UColdSteelExperienceFeed::NativeDestruct()
{
    if(Model)Model->ResetExperienceNotices();
    Model=nullptr;Lines.Reset();
    Super::NativeDestruct();
}

void UColdSteelExperienceFeed::SetPresentationSuppressed(bool Suppressed)
{
    if(bSuppressed==Suppressed)return;
    bSuppressed=Suppressed;
    UpdateVisibility();
}

void UColdSteelExperienceFeed::UpdateVisibility()
{
    SetVisibility(bSuppressed?ESlateVisibility::Hidden:ESlateVisibility::HitTestInvisible);
}

void UColdSteelExperienceFeed::RefreshMetrics()
{
    const float NewScale=FMath::Max(.01f,ColdSteelUI::PixelScale(this));
    if(FMath::IsNearlyEqual(NewScale,Scale,.001f)&&!UnitText.IsEmpty())return;
    const float OldScale=Scale;
    Scale=NewScale;
    // Slate points at 96 DPI; the HUD contract is physical pixels.
    AmountFont=ColdSteelUI::NumberFont(24.f*.75f/Scale,true);
    UnitFont=ColdSteelUI::TextFont(16.f*.75f/Scale,true);
    UnitText=TEXT("经验");
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    UnitWidth=float(Measure->Measure(UnitText,UnitFont).X);
    UnitHeight=float(Measure->Measure(UnitText,UnitFont).Y);
    AmountHeight=float(Measure->Measure(TEXT("+0"),AmountFont).Y);
    for(FLine& Line:Lines)
    {
        MeasureLine(Line);
        if(OldScale>0.f)Line.Y=Line.Y*OldScale/Scale;
    }
}

void UColdSteelExperienceFeed::MeasureLine(FLine& Line) const
{
    Line.Text=FString::Printf(TEXT("+%lld"),Line.Amount);
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    Line.Width=float(Measure->Measure(Line.Text,AmountFont).X);
}

void UColdSteelExperienceFeed::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f))RefreshMetrics();
    if(!Model)
    {
        Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
        if(!Model)return;
    }
    if(bSuppressed||UGameplayStatics::IsGamePaused(this))return;

    const bool bHadLines=!Lines.IsEmpty();
    for(FLine& Line:Lines)Line.Age+=DeltaTime;
    Lines.RemoveAll([](const FLine& Line){return Line.Age>=XpFeedLife;});

    AdmissionAge+=DeltaTime;
    if(AdmissionAge>=XpFeedAdmissionInterval&&Lines.Num()<XpFeedMaxLines)
    {
        int64 Amount=0;
        if(Model->TakeExperienceNotice(Amount))
        {
            FLine Line;Line.Amount=Amount;MeasureLine(Line);
            // Start slightly above the resting slot so the first frame reads as a drop-in, not a pop.
            Line.Y=-8.f/Scale;
            Lines.Insert(MoveTemp(Line),0);
            AdmissionAge=0.f;
        }
    }

    // The newest entry stays closest to the crosshair; older lines slide down as the stack grows.
    for(int32 Index=0;Index<Lines.Num();++Index)
        Lines[Index].Y=FMath::FInterpTo(Lines[Index].Y,float(Index)*XpFeedPitch/Scale,DeltaTime,16.f);

    // NativeTick owns the fade/rise state; without an explicit paint invalidation the
    // child widget keeps its cached frame while the HUD around it repaints.
    if(bHadLines||!Lines.IsEmpty())
        if(const auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);
}

int32 UColdSteelExperienceFeed::NativePaint(const FPaintArgs& Args,const FGeometry& AllottedGeometry,const FSlateRect& MyCullingRect,
    FSlateWindowElementList& OutDrawElements,int32 LayerId,const FWidgetStyle& InWidgetStyle,bool bParentEnabled) const
{
    LayerId=Super::NativePaint(Args,AllottedGeometry,MyCullingRect,OutDrawElements,LayerId,InWidgetStyle,bParentEnabled);
    if(bSuppressed||Lines.IsEmpty()||Scale<=0.f)return LayerId;

    const FVector2D Size=AllottedGeometry.GetLocalSize();
    if(Size.X<1.f||Size.Y<1.f)return LayerId;
    const float ViewWidth=float(Size.X),ViewHeight=float(Size.Y);
    const FLinearColor Tint=InWidgetStyle.GetColorAndOpacityTint();
    const float Gap=XpFeedTextGap/Scale;
    const auto* Pawn=GetOwningPlayerPawn();
    const auto* Bow=Pawn?Pawn->FindComponentByClass<UBowWeaponComponent>():nullptr;
    const auto* Echo=Pawn?Pawn->FindComponentByClass<UBowMountainEchoComponent>():nullptr;
    const auto* Cadence=Pawn?Pawn->FindComponentByClass<UBowCadenceComponent>():nullptr;
    const ColdSteelBowResonance::FCueLayout* BowLayout=nullptr;
    if(Bow&&Bow->IsEquipped())
    {
        if(Cadence&&Cadence->IsEquippedFor(Bow->EquippedInstance()))BowLayout=&ColdSteelBowResonance::CadenceLayout;
        else if(Echo&&Echo->IsEquippedFor(Bow->EquippedInstance()))BowLayout=&ColdSteelBowResonance::LightPillarLayout;
    }
    const FVector2D ScopeOffset=Bow&&Bow->ScopeOptics()?Bow->ScopeOptics()->CueOffset(AllottedGeometry,1.f/Scale):FVector2D::ZeroVector;
    const auto* Core=Pawn?Pawn->FindComponentByClass<UStarMarrowComponent>():nullptr;
    const bool StarMarrowVisible=Core&&Core->HUDVisible();
    const float CueOffset=StarMarrowVisible?ColdSteelStarMarrow::ExperienceOffset:
        BowLayout?BowLayout->ExperienceOffset():XpFeedBaseOffset;
    const float CuePixelToLocal=StarMarrowVisible?ColdSteelStarMarrow::LayoutScale(1.f/Scale,ViewHeight*.5f):
        BowLayout?BowLayout->Scale(Size*.5f,1.f/Scale):1.f/Scale;
    const float BaseY=ViewHeight*.5f+ScopeOffset.Y+CueOffset*CuePixelToLocal;
    const float ShadowOffset=1.5f/Scale;
    const FVector2D ShadowShift(ShadowOffset);
    const float FramePadX=XpFeedFramePadX/Scale;
    const float FramePadY=XpFeedFramePadY/Scale;
    const float FrameThickness=XpFeedFrameThickness/Scale;

    // One tight, right-angled gold outline per gain. Each frame follows its own
    // line (stack offset, rise and fade) and has no fill, card or blur.
    for(const FLine& Line:Lines)
    {
        const float Alpha=FMath::Min(FMath::Clamp(Line.Age/XpFeedFadeIn,0.f,1.f),
            FMath::Clamp((XpFeedLife-Line.Age)/XpFeedFadeOut,0.f,1.f));
        if(Alpha<=0.f)continue;
        const float Rise=-XpFeedRise/Scale*ColdSteelUI::EaseSmooth(FMath::Clamp(Line.Age/XpFeedLife,0.f,1.f));
        const float Y=BaseY+Line.Y+Rise;
        const float Total=Line.Width+Gap+UnitWidth;
        const float FrameWidth=Total+2.f*FramePadX;
        const float FrameHeight=AmountHeight+2.f*FramePadY;
        const float FrameLeft=ViewWidth*.5f+ScopeOffset.X-FrameWidth*.5f;
        const float FrameTop=Y-FramePadY;
        TArray<FVector2D> Points;
        Points.Reserve(5);
        Points.Add(FVector2D(FrameLeft,FrameTop));
        Points.Add(FVector2D(FrameLeft+FrameWidth,FrameTop));
        Points.Add(FVector2D(FrameLeft+FrameWidth,FrameTop+FrameHeight));
        Points.Add(FVector2D(FrameLeft,FrameTop+FrameHeight));
        // Close with a fresh value, never with Points[0]: Add() must not receive
        // a reference into the same TArray or the container-alias assert fires.
        Points.Add(FVector2D(FrameLeft,FrameTop));
        TArray<FVector2D> ShadowPoints=Points;
        const float FrameShift=1.f/Scale;
        for(FVector2D& Point:ShadowPoints)Point+=FVector2D(FrameShift);
        FLinearColor FrameColor=ColdSteelUI::HUDGold;
        FrameColor*=Tint;FrameColor.A*=Alpha;
        FLinearColor FrameShadow(0.f,0.f,0.f,.55f);
        FrameShadow*=Tint;FrameShadow.A*=Alpha;
        FSlateDrawElement::MakeLines(OutDrawElements,LayerId+1,AllottedGeometry.ToPaintGeometry(),
            ShadowPoints,ESlateDrawEffect::None,FrameShadow,true,FrameThickness+1.f/Scale);
        FSlateDrawElement::MakeLines(OutDrawElements,LayerId+2,AllottedGeometry.ToPaintGeometry(),
            Points,ESlateDrawEffect::None,FrameColor,true,FrameThickness);
    }

    auto DrawText=[&](const FString& Value,const FSlateFontInfo& Font,const FVector2D& Position,float Width,
        const FLinearColor& Color,float Alpha)
    {
        FLinearColor Fill=Color;Fill*=Tint;Fill.A*=Alpha;
        if(Fill.A<=.001f)return;
        const FLinearColor Shadow(0.f,0.f,0.f,.78f*Fill.A);
        const FVector2D TextSize(Width+12.f/Scale,AmountHeight+UnitHeight+8.f/Scale);
        FSlateDrawElement::MakeText(OutDrawElements,LayerId+3,
            AllottedGeometry.ToPaintGeometry(TextSize,FSlateLayoutTransform(Position+ShadowShift)),
            Value,Font,ESlateDrawEffect::None,Shadow);
        FSlateDrawElement::MakeText(OutDrawElements,LayerId+4,
            AllottedGeometry.ToPaintGeometry(TextSize,FSlateLayoutTransform(Position)),
            Value,Font,ESlateDrawEffect::None,Fill);
    };

    for(const FLine& Line:Lines)
    {
        const float Alpha=FMath::Min(FMath::Clamp(Line.Age/XpFeedFadeIn,0.f,1.f),
            FMath::Clamp((XpFeedLife-Line.Age)/XpFeedFadeOut,0.f,1.f));
        if(Alpha<=0.f)continue;
        const float Rise=-XpFeedRise/Scale*ColdSteelUI::EaseSmooth(FMath::Clamp(Line.Age/XpFeedLife,0.f,1.f));
        const float Y=BaseY+Line.Y+Rise;
        const float Total=Line.Width+Gap+UnitWidth;
        const float X=ViewWidth*.5f+ScopeOffset.X-Total*.5f;
        DrawText(Line.Text,AmountFont,FVector2D(X,Y),Line.Width,ColdSteelUI::HUDGoldLight,Alpha);
        DrawText(UnitText,UnitFont,FVector2D(X+Line.Width+Gap,Y+(AmountHeight-UnitHeight)-1.f/Scale),
            UnitWidth,ColdSteelUI::HUDGold,Alpha);
    }
    return LayerId+4;
}
