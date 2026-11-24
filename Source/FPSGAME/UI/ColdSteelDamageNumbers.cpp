#include "ColdSteelDamageNumbers.h"
#include "ColdSteelDamageNumberSubsystem.h"
#include "ColdSteelUIStyle.h"
#include "Blueprint/WidgetTree.h"
#include "Components/CanvasPanel.h"
#include "Engine/GameInstance.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"

namespace
{
constexpr int32 MaxEntries=64;
constexpr float EntryLife=1.15f,CritLife=1.3f,KillLife=1.35f;
constexpr float FadeIn=.06f,FadeOut=.28f,MergeWindow=.12f;
constexpr float RisePixels=36.f,SafeMargin=24.f,LabelGap=6.f;
constexpr float NumberPixels=24.f,LabelPixels=12.f;
}

void UColdSteelDamageNumbers::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    SetIsFocusable(false);
    SetClipping(EWidgetClipping::ClipToBounds);
    WidgetTree->RootWidget=WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass());
    RefreshMetrics();
    UpdateVisibility();
}

void UColdSteelDamageNumbers::NativeConstruct()
{
    Super::NativeConstruct();
    Numbers=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelDamageNumberSubsystem>():nullptr;
    UpdateVisibility();
}

void UColdSteelDamageNumbers::NativeDestruct()
{
    if(Numbers)Numbers->Reset();
    Numbers=nullptr;Entries.Reset();
    Super::NativeDestruct();
}

void UColdSteelDamageNumbers::SetPresentationSuppressed(bool Suppressed)
{
    if(bSuppressed==Suppressed)return;
    bSuppressed=Suppressed;
    if(Suppressed){Entries.Reset();if(Numbers)Numbers->Reset();}
    UpdateVisibility();
}

void UColdSteelDamageNumbers::UpdateVisibility()
{
    SetVisibility(bSuppressed?ESlateVisibility::Hidden:ESlateVisibility::HitTestInvisible);
}

void UColdSteelDamageNumbers::RefreshMetrics()
{
    const float NewScale=FMath::Max(.01f,ColdSteelUI::PixelScale(this));
    if(FMath::IsNearlyEqual(NewScale,Scale,.001f)&&AmountHeight>0.f)return;
    Scale=NewScale;
    AmountFont=ColdSteelUI::NumberFont(NumberPixels*.75f/Scale,true);
    LabelFont=ColdSteelUI::TextFont(LabelPixels*.75f/Scale,true);
    CountFont=ColdSteelUI::NumberFont(LabelPixels*.75f/Scale,true);
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    AmountHeight=float(Measure->Measure(TEXT("+0"),AmountFont).Y);
    LabelHeight=float(Measure->Measure(TEXT("暴击"),LabelFont).Y);
    CritWidth=float(Measure->Measure(TEXT("暴击"),LabelFont).X);
    KillWidth=float(Measure->Measure(TEXT("击杀"),LabelFont).X);
    for(FEntry& Entry:Entries)MeasureEntry(Entry);
}

void UColdSteelDamageNumbers::MeasureEntry(FEntry& Entry) const
{
    auto Format=[](float Amount) -> FString
    {
        if(Amount<=0.f)return {};
        if(Amount<.1f)return TEXT("<0.1");
        if(Amount<1.f)return FString::Printf(TEXT("%.1f"),Amount);
        return FString::Printf(TEXT("%lld"),FMath::RoundToInt64(Amount));
    };
    Entry.PhysicalText=Format(Entry.Physical);
    Entry.MagicText=Format(Entry.Magic);
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    Entry.PhysicalWidth=Entry.PhysicalText.IsEmpty()?0.f:float(Measure->Measure(Entry.PhysicalText,AmountFont).X);
    Entry.MagicWidth=Entry.MagicText.IsEmpty()?0.f:float(Measure->Measure(Entry.MagicText,AmountFont).X);
    Entry.CountText=Entry.Count>1?FString::Printf(TEXT("×%d"),Entry.Count):FString();
    Entry.CountWidth=Entry.CountText.IsEmpty()?0.f:float(Measure->Measure(Entry.CountText,CountFont).X);
}

void UColdSteelDamageNumbers::NativeTick(const FGeometry& Geometry,float DeltaTime)
{
    Super::NativeTick(Geometry,DeltaTime);
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f))RefreshMetrics();
    if(!Numbers)
    {
        Numbers=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelDamageNumberSubsystem>():nullptr;
        if(!Numbers)return;
    }
    if(bSuppressed||UGameplayStatics::IsGamePaused(this))return;

    const bool bHadEntries=!Entries.IsEmpty();
    TArray<FColdSteelDamageNumberEvent> Events;
    if(Numbers->ConsumeDamageNumbers(Events))
    {
        APlayerController* Owner=GetOwningPlayer();
        for(const FColdSteelDamageNumberEvent& Event:Events)
        {
            // The target can be destroyed before this HUD tick (killing blow / ragdoll
            // cleanup); the queued world point still owns a readable number.
            if(!Event.Viewer.IsValid()||Event.Viewer.Get()!=Owner)continue;
            FEntry* Existing=nullptr;
            if(Event.Target.IsValid())
                for(FEntry& Entry:Entries)
                    if(Entry.Target==Event.Target&&Entry.Age<=MergeWindow){Existing=&Entry;break;}
            if(Existing)
            {
                Existing->Physical+=Event.Physical;
                Existing->Magic+=Event.Magic;
                ++Existing->Count;
                Existing->bCritical|=Event.bCritical;
                Existing->bKilled|=Event.bKilled;
                Existing->bBig|=Event.bBig;
                Existing->bTrackTarget|=Event.bTrackTarget;
                Existing->Age=FMath::Min(Existing->Age,.06f);
                Existing->WorldPoint=Event.WorldPoint;
                Existing->Life=Existing->bKilled?KillLife:Existing->bCritical?CritLife:EntryLife;
                MeasureEntry(*Existing);
            }
            else
            {
                if(Entries.Num()>=MaxEntries)
                {
                    int32 Oldest=0;float OldestAge=-1.f;
                    for(int32 Index=0;Index<Entries.Num();++Index)
                        if(Entries[Index].Age>OldestAge){OldestAge=Entries[Index].Age;Oldest=Index;}
                    Entries.RemoveAt(Oldest);
                }
                FEntry Entry;
                Entry.Target=Event.Target;
                Entry.WorldPoint=Event.WorldPoint;
                Entry.Physical=Event.Physical;
                Entry.Magic=Event.Magic;
                Entry.Count=1;
                Entry.bCritical=Event.bCritical;
                Entry.bKilled=Event.bKilled;
                Entry.bBig=Event.bBig;
                Entry.bTrackTarget=Event.bTrackTarget;
                Entry.Life=Entry.bKilled?KillLife:Entry.bCritical?CritLife:EntryLife;
                MeasureEntry(Entry);
                Entries.Add(MoveTemp(Entry));
            }
        }
    }

    for(FEntry& Entry:Entries)Entry.Age+=DeltaTime;
    Entries.RemoveAll([](const FEntry& Entry){return Entry.Age>=Entry.Life;});
    if(bHadEntries||!Entries.IsEmpty())
        if(const auto Widget=GetCachedWidget())Widget->Invalidate(EInvalidateWidgetReason::Paint);
}

int32 UColdSteelDamageNumbers::NativePaint(const FPaintArgs& Args,const FGeometry& AllottedGeometry,const FSlateRect& MyCullingRect,
    FSlateWindowElementList& OutDrawElements,int32 LayerId,const FWidgetStyle& InWidgetStyle,bool bParentEnabled) const
{
    LayerId=Super::NativePaint(Args,AllottedGeometry,MyCullingRect,OutDrawElements,LayerId,InWidgetStyle,bParentEnabled);
    if(bSuppressed||Entries.IsEmpty()||Scale<=0.f)return LayerId;
    APlayerController* PC=GetOwningPlayer();
    if(!PC)return LayerId;

    const FVector2D Size=AllottedGeometry.GetLocalSize();
    if(Size.X<1.f||Size.Y<1.f)return LayerId;
    const float ViewWidth=float(Size.X),ViewHeight=float(Size.Y);
    const FVector2D ViewportPixels(ViewWidth*Scale,ViewHeight*Scale);
    const FLinearColor Tint=InWidgetStyle.GetColorAndOpacityTint();
    const float Safe=SafeMargin/Scale;
    const float Gap=LabelGap/Scale;

    auto DrawText=[&](const FString& Value,const FSlateFontInfo& Font,const FVector2D& Position,
        float Width,float Height,float TextScale,const FLinearColor& Color,float Alpha,int32 TextLayer,bool bFourWay)
    {
        FLinearColor Fill=Color;Fill*=Tint;Fill.A*=Alpha;
        if(Fill.A<=.001f)return;
        const FLinearColor Shadow(0.f,0.f,0.f,.82f*Fill.A);
        const float O=(bFourWay?1.25f:1.f)/Scale;
        const FVector2D Offsets[4]={FVector2D(O,0.f),FVector2D(-O,0.f),FVector2D(0.f,O),FVector2D(0.f,-O)};
        const int32 OffsetCount=bFourWay?4:1;
        const FVector2D TextSize(Width+8.f/Scale,Height+8.f/Scale);
        for(int32 Index=0;Index<OffsetCount;++Index)
            FSlateDrawElement::MakeText(OutDrawElements,TextLayer-1,
                AllottedGeometry.ToPaintGeometry(TextSize,FSlateLayoutTransform(TextScale,Position+Offsets[Index])),
                Value,Font,ESlateDrawEffect::None,Shadow);
        FSlateDrawElement::MakeText(OutDrawElements,TextLayer,
            AllottedGeometry.ToPaintGeometry(TextSize,FSlateLayoutTransform(TextScale,Position)),
            Value,Font,ESlateDrawEffect::None,Fill);
    };

    for(const FEntry& Entry:Entries)
    {
        const float Alpha=FMath::Min(FMath::Clamp(Entry.Age/FadeIn,0.f,1.f),
            FMath::Clamp((Entry.Life-Entry.Age)/FadeOut,0.f,1.f));
        if(Alpha<=0.f)continue;
        FVector WorldPoint=Entry.WorldPoint;
        if(Entry.bTrackTarget&&Entry.Target.IsValid())
            WorldPoint=UColdSteelDamageNumberSubsystem::TargetTopAnchor(Entry.Target.Get());
        FVector2D Screen;
        if(!UGameplayStatics::ProjectWorldToScreen(PC,WorldPoint,Screen,true))continue;
        if(Screen.X<0.f||Screen.Y<0.f||Screen.X>ViewportPixels.X||Screen.Y>ViewportPixels.Y)continue;

        const float T=FMath::Clamp(Entry.Age/Entry.Life,0.f,1.f);
        const float Ease=1.f-FMath::Pow(1.f-T,3.f);
        const float BaseScale=Entry.bCritical?1.16f:Entry.bBig?1.06f:1.f;
        const float Pop=.10f*FMath::Sin(PI*FMath::Clamp(Entry.Age/.18f,0.f,1.f));
        const float DrawScale=BaseScale+Pop;
        const float ChannelGap=Entry.Physical>0.f&&Entry.Magic>0.f?12.f/Scale:0.f;
        const float DrawnWidth=(Entry.PhysicalWidth+Entry.MagicWidth)*DrawScale+ChannelGap;
        const float DrawnHeight=AmountHeight*DrawScale;
        if(ViewWidth-Safe*2.f<DrawnWidth||ViewHeight-Safe*2.f<DrawnHeight)continue;

        FVector2D Pos=Screen/Scale;
        Pos.X-=DrawnWidth*.5f;
        Pos.Y-=DrawnHeight+6.f/Scale;
        Pos.Y-=RisePixels*Ease/Scale;
        Pos.X=FMath::Clamp(Pos.X,Safe,ViewWidth-Safe-DrawnWidth);
        Pos.Y=FMath::Clamp(Pos.Y,Safe,ViewHeight-Safe-DrawnHeight);

        const FLinearColor Tone=Entry.bCritical?ColdSteelUI::DamageCritical:
            Entry.bBig?ColdSteelUI::DamageHeavy:ColdSteelUI::HUDGoldLight;
        if(Entry.Physical>0.f)
            DrawText(Entry.PhysicalText,AmountFont,Pos,Entry.PhysicalWidth,AmountHeight,DrawScale,Tone,Alpha,LayerId+2,true);
        if(Entry.Magic>0.f)
        {
            const FVector2D MagicPos(Pos.X+Entry.PhysicalWidth*DrawScale+ChannelGap,Pos.Y);
            DrawText(Entry.MagicText,AmountFont,MagicPos,Entry.MagicWidth,AmountHeight,DrawScale,ColdSteelUI::DamageMagic,Alpha,LayerId+2,true);
        }

        float LabelX=Pos.X+DrawnWidth+Gap;
        const float MaxLabelWidth=FMath::Max(CritWidth,FMath::Max(KillWidth,Entry.CountWidth));
        if(LabelX+MaxLabelWidth>ViewWidth-Safe)LabelX=FMath::Max(Safe,Pos.X-MaxLabelWidth-Gap);
        float LabelY=Pos.Y;
        if(Entry.bCritical)
        {
            DrawText(TEXT("暴击"),LabelFont,FVector2D(LabelX,LabelY),CritWidth,LabelHeight,1.f,
                ColdSteelUI::DamageCritical,Alpha,LayerId+3,false);
            LabelY+=16.f/Scale;
        }
        if(Entry.bKilled)
        {
            DrawText(TEXT("击杀"),LabelFont,FVector2D(LabelX,LabelY),KillWidth,LabelHeight,1.f,
                ColdSteelUI::HUDGoldLight,Alpha,LayerId+3,false);
            LabelY+=16.f/Scale;
        }
        if(Entry.Count>1)
            DrawText(Entry.CountText,CountFont,FVector2D(LabelX,LabelY),Entry.CountWidth,LabelHeight,1.f,
                ColdSteelUI::TextSecondary,Alpha,LayerId+3,false);
    }
    return LayerId+3;
}
