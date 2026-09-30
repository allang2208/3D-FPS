#include "ColdSteelHUDWidget.h"
#include "ColdSteelHUDLayout.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelWorldClock.h"
#include "StatusEffectsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Components/Border.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "GameFramework/PlayerController.h"

void UColdSteelHUDWidget::RefreshHUDTargetDisplay()
{
    // Use the established HUD 20 Hz read-only refresh. Never scan world actors or
    // create status components from paint; only read the accepted hit's target.
    FMonsterHitFeedback Hit;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn());
    if(!Player||!Player->GetMonsterHitFeedback(Hit)||!Hit.Target.IsValid())
    {HUDDisplayTarget.Reset();HUDTargetLevel.Reset();HUDTargetEffects.Reset();return;}
    const auto* Target=Hit.Target.Get();
    if(HUDDisplayTarget!=Hit.Target)
    {
        HUDDisplayTarget=Hit.Target;HUDTargetLevel.Reset();
        FMonsterCoreStats Stats;
        if(MonsterCoreStats::Get(Target,Stats))HUDTargetLevel=FString::Printf(TEXT(" · Lv.%d"),Stats.Level);
    }
    HUDTargetEffects.Reset();
    if(!Hit.bKilled)
        if(const auto* Effects=Target->FindComponentByClass<UStatusEffectsComponent>())
        {
            const auto Snapshot=Effects->Snapshot();
            for(int32 I=0;I<FMath::Min(6,Snapshot.Num());++I)
            {
                const auto& Effect=Snapshot[I];
                const FString Count=Effect.Stacks>1?FString::Printf(TEXT(" ×%d"),Effect.Stacks):FString();
                HUDTargetEffects.Add({Effect.Name+Count+TEXT(" ")+Effect.TimeText(),Effect.Color});
            }
            if(Snapshot.Num()>6)HUDTargetEffects.Add({FString::Printf(TEXT("+%d"),Snapshot.Num()-6),ColdSteelUI::TextSecondary});
        }
}

int32 UColdSteelHUDWidget::PaintHUDNavigation(const FGeometry& G,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style) const
{
    const float U=1.f/ColdSteelUI::PixelScale(this);
    const auto View=G.GetLocalSize();
    const FColdSteelHUDLayout Layout(View.X/U);
    const FLinearColor Tint=Style.GetColorAndOpacityTint();
    auto Line=[&](const TArray<FVector2D>& Points,const FLinearColor& Color,float Width=1.f)
    {FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Color*Tint,true,Width*U);};
    auto Corners=[&](const UWidget* Widget,float RadiusPixels=10.f)
    {
        if(!Widget||!Widget->IsVisible())return;
        // NativePaint runs after the children: use their current paint geometry,
        // not the tick-space geometry cached before DPI/layout changes.
        const auto& WG=Widget->GetPaintSpaceGeometry();
        const auto Size=WG.GetLocalSize();if(Size.X<2||Size.Y<2)return;
        const auto* Border=Cast<UBorder>(Widget);
        for(int32 X:{0,1})for(int32 Y:{0,1})
        {
            // Follow the panel's actual rounded outline, inset by half the stroke.
            const float Inset=.75f*U;
            const int32 Corner=Y?(X?2:3):(X?1:0);
            const float PanelRadius=Border?Border->Background.OutlineSettings.CornerRadii[Corner]:RadiusPixels*U;
            const float Radius=FMath::Min(PanelRadius,float(FMath::Min(Size.X,Size.Y))*.5f);
            const float ArcRadius=FMath::Max(0.f,Radius-Inset);
            TArray<FVector2D> Points;
            auto Point=[&](FVector2D P){if(X)P.X=Size.X-P.X;if(Y)P.Y=Size.Y-P.Y;Points.Add(P);};
            Point(FVector2D(Radius+6*U,Inset));
            for(int32 I=0;I<=8;++I)
            {
                const float Angle=-PI*.5f-I*(PI*.5f/8);
                Point(FVector2D(Radius+ArcRadius*FMath::Cos(Angle),Radius+ArcRadius*FMath::Sin(Angle)));
            }
            Point(FVector2D(Inset,Radius+6*U));
            FSlateDrawElement::MakeLines(Out,Layer+1,WG.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,ColdSteelUI::HUDGold*Tint,true,1.25f*U);
        }
    };
    const bool DrawerOut=bInventoryOpen||DrawerProgress>KINDA_SMALL_NUMBER||bExternalDrawerOpen;
    // Don't put ornament over foreground drawers or their dimming layer.
    if(!DrawerOut&&!bWarehouseOpen&&WarehouseMotion<=KINDA_SMALL_NUMBER)
    {
        Corners(TopVitalsTint);Corners(WorldClock);Corners(AmmoReadout,8.f);
        if(TimelineExpansion<=KINDA_SMALL_NUMBER&&TimelineWidthBox&&TimelineWidthBox->IsVisible())Corners(TimelineTrackBackground);
        if(HotbarCanvasSlot)Corners(HotbarCanvasSlot->Content);
    }
    const auto* PC=GetOwningPlayer();
    if(!PC||DrawerOut||bWarehouseOpen||PC->bShowMouseCursor)return Layer+1;
    const float Width=Layout.CompassWidth*U,Left=(View.X-Width)*.5f,Top=Layout.CompassTop*U;
    const float Heading=FRotator::ClampAxis(PC->GetControlRotation().Yaw);
    // World +X is north, +Y east. This also handles the 359 -> 0 seam.
    const auto MajorFont=ColdSteelUI::NumberFont(16*.75f*U,true);
    const auto MinorFont=ColdSteelUI::NumberFont(11*.75f*U);
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    auto Text=[&](const FString& Value,float X,float Y,const FSlateFontInfo& Font,const FLinearColor& Color)
    {
        const FVector2D Size=Measure->Measure(Value,Font);
        const FVector2D At(X-Size.X*.5f,Y);
        FSlateDrawElement::MakeText(Out,Layer+2,G.ToPaintGeometry(Size,FSlateLayoutTransform(At+FVector2D(U,U))),Value,Font,ESlateDrawEffect::None,FLinearColor(0,0,0,.9f)*Tint);
        FSlateDrawElement::MakeText(Out,Layer+3,G.ToPaintGeometry(Size,FSlateLayoutTransform(At)),Value,Font,ESlateDrawEffect::None,Color*Tint);
    };
    Line({FVector2D(Left,Top+30*U),FVector2D(Left+Width,Top+30*U)},ColdSteelUI::HUDGoldDim);
    static const TCHAR* Directions[]={TEXT("N"),TEXT("NE"),TEXT("E"),TEXT("SE"),TEXT("S"),TEXT("SW"),TEXT("W"),TEXT("NW")};
    const int32 First=FMath::CeilToInt((Heading-60)/5),Last=FMath::FloorToInt((Heading+60)/5);
    for(int32 I=First;I<=Last;++I)
    {
        const int32 Degree=((I*5)%360+360)%360;
        const bool Cardinal=Degree%45==0,Label=Degree%15==0;
        const float X=View.X*.5f+(I*5-Heading)/120.f*Width;
        const float H=Cardinal?11.f:Label?7.f:4.f;
        Line({FVector2D(X,Top+(30-H)*U),FVector2D(X,Top+30*U)},Cardinal?ColdSteelUI::HUDGoldLight:ColdSteelUI::HUDGoldDim);
        if(Cardinal||Label)Text(Cardinal?FString(Directions[Degree/45]):FString::FromInt(Degree),X,Top,Cardinal?MajorFont:MinorFont,Cardinal?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextSecondary);
    }
    const float Center=View.X*.5f;
    Line({FVector2D(Center-4*U,Top+37*U),FVector2D(Center,Top+42*U),FVector2D(Center+4*U,Top+37*U)},ColdSteelUI::HUDGoldLight,2.f);
    const auto Badge=ColdSteelUI::RoundedBrush(FLinearColor::White,3*U,FLinearColor::Transparent,0);
    FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(FVector2D(58,25)*U,FSlateLayoutTransform(FVector2D(Center-29*U,Top+46*U))),&Badge,ESlateDrawEffect::None,ColdSteelUI::GlassTint*Tint);
    Text(FString::Printf(TEXT("%03d°"),FMath::RoundToInt(Heading)%360),Center,Top+49*U,MajorFont,ColdSteelUI::HUDGoldLight);
    return Layer+3;
}
