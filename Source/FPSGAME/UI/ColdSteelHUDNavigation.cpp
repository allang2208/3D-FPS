#include "ColdSteelHUDWidget.h"
#include "ColdSteelHUDLayout.h"
#include "ColdSteelAmmoReadout.h"
#include "ColdSteelWorldClock.h"
#include "ColdSteelMapMarkers.h"
#include "ColdSteelDungeonMap.h"
#include "../FPSGAMEPlayerController.h"
#include "StatusEffectsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCoreStats.h"
#include "../NPC/VillageResidentStatus.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "Components/Border.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/SizeBox.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "GameFramework/PlayerController.h"

bool UColdSteelHUDWidget::ReadHUDTarget(const AFPSGAMECharacter& Player,FMonsterHitFeedback& Out) const
{
    if(const auto* Section=FocusedDefense.Get())
    {
        Out=FMonsterHitFeedback{};
        Out.Target=FocusedDefense.Get();
        if(Section->IsA<AHighVillageGate>())Out.Name=NSLOCTEXT("VillageDefense","HighGate","石城门 · 升降铁闸");
        else if(Section->IsA<AHighVillageWall>())Out.Name=NSLOCTEXT("VillageDefense","HighWall","石砌高墙");
        else if(Section->IsA<AVillageDefenseStairs>())Out.Name=NSLOCTEXT("VoxelBuilding","VillageWallStairs","城墙石阶");
        else Out.Name=Section->IsA<AVillageDefenseGate>()
            ? NSLOCTEXT("VillageDefense","Gate","村庄城门") : NSLOCTEXT("VillageDefense","Wall","村庄围墙");
        Out.Health=Section->GetHealth();
        Out.MaxHealth=Section->GetMaximumHealth();
        Out.Opacity=1.f;
        return Out.MaxHealth>0.f;
    }
    if(FocusedResident.IsValid() && FocusedResident==ResidentReadout.Target)
    {Out=ResidentReadout;return true;}
    return Player.GetMonsterHitFeedback(Out);
}

void UColdSteelHUDWidget::RefreshHUDTargetDisplay()
{
    // Use the established HUD 20 Hz read-only refresh. Never scan world actors or
    // create status components from paint. Reuse the local interaction focus.
    FMonsterHitFeedback Hit;
    ResidentReadout={};
    if(auto* Resident=FocusedResident.Get())VillageResidentStatus::Read(*Resident,ResidentReadout);
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwningPlayerPawn());
    if(!Player||!ReadHUDTarget(*Player,Hit)||!Hit.Target.IsValid())
    {HUDDisplayTarget.Reset();HUDTargetLevel.Reset();HUDTargetEffects.Reset();return;}
    const auto* Target=Hit.Target.Get();
    if(HUDDisplayTarget!=Hit.Target)
    {
        HUDDisplayTarget=Hit.Target;HUDTargetLevel.Reset();
        FMonsterCoreStats Stats;
        if(MonsterCoreStats::Get(Target,Stats))HUDTargetLevel=FString::Printf(TEXT(" · Lv.%d"),Stats.Level);
    }
    HUDTargetEffects.Reset();
    if(!Hit.bKilled && (Hit.Health>0.f || !Hit.FriendlyActivity.IsEmpty()))
        if(const auto* Effects=Target->FindComponentByClass<UStatusEffectsComponent>())
        {
            auto Snapshot=Effects->Snapshot();
            if(FocusedDefense.IsValid())
                Snapshot.RemoveAll([](const FStatusEffectView& Effect){return Effect.Kind!=TEXT("debuff");});
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
    if (const auto* Controller=Cast<AFPSGAMEPlayerController>(PC))
        if (const auto* Markers=Controller->GetMapMarkers(); Markers && PC->GetPawn())
        {
            struct FCompassMarker { const FColdSteelMapMarker* Marker; float Delta; double Metres; };
            TArray<FCompassMarker,TInlineAllocator<FColdSteelMapMarkers::Limit>> Visible;
            const FVector PlayerPosition=PC->GetPawn()->GetActorLocation();
            for (const auto& M:Markers->All()) if (Markers->IsActive(M))
            {
                const FVector Offset=M.Position-PlayerPosition;
                const float Bearing=Offset.SizeSquared2D()<1.?Heading:Offset.Rotation().Yaw;
                Visible.Add({&M,FMath::FindDeltaAngleDegrees(Heading,Bearing),Offset.Size2D()*.01});
            }
            Visible.Sort([](const auto& A,const auto& B){return FMath::Abs(A.Delta)<FMath::Abs(B.Delta);});
            const auto LabelFont=ColdSteelUI::TextFont(12*.75f*U);
            TArray<FBox2D,TInlineAllocator<FColdSteelMapMarkers::Limit>> Labels;
            for (const auto& Item:Visible)
            {
                const auto& M=*Item.Marker;
                const auto Color=FColdSteelMapMarkers::Color(M.ColorIndex);
                const bool bOutside=FMath::Abs(Item.Delta)>60.f;
                const float X=Center+FMath::Clamp(Item.Delta,-60.f,60.f)/120.f*Width;
                const float Y=Top+36*U;
                Line({FVector2D(X,Y-4*U),FVector2D(X+4*U,Y),FVector2D(X,Y+4*U),FVector2D(X-4*U,Y),FVector2D(X,Y-4*U)},Color,1.5f);
                if (bOutside)
                {
                    const float Side=Item.Delta<0?-1.f:1.f;
                    Line({FVector2D(X-Side*3*U,Y+7*U),FVector2D(X+Side*2*U,Y+11*U),FVector2D(X-Side*3*U,Y+15*U)},Color,1.5f);
                }
                // The hit-target card owns the area immediately below the compass during combat.
                if (HUDDisplayTarget.IsValid()) continue;
                const FString Name=M.Label+(M.bReadOnly?TEXT(" · ")+M.OwnerName:FString());
                const FString Distance=FString::Printf(TEXT("%.0f m"),Item.Metres);
                const FString Details=M.bDungeon?Distance+TEXT(" · ")+FColdSteelDungeonMap::FloorName(M.Floor):Distance;
                const FString Suffix=TEXT(" · ")+Details;
                const float Maximum=FMath::Min(210.f*U,Width*.55f);
                const FString Short=ColdSteelUI::Ellipsize(Name,LabelFont,Maximum-Measure->Measure(Suffix,LabelFont).X,*Measure);
                const FString Caption=Short.IsEmpty()?ColdSteelUI::Ellipsize(Details,LabelFont,Maximum,*Measure):Short+Suffix;
                const FVector2D Span=FVector2D(Measure->Measure(Caption,LabelFont))+FVector2D(12,4)*U;
                const float LabelX=FMath::Clamp(X,Left+float(Span.X*.5),Left+Width-float(Span.X*.5));
                for (int32 Row=0;Row<3;++Row)
                {
                    const FVector2D At(LabelX-Span.X*.5,Top+(76+22*Row)*U);
                    const FBox2D Rect(At,At+Span);
                    if (Labels.ContainsByPredicate([&](const auto& Used){return Used.Intersect(Rect.ExpandBy(3.*U));})) continue;
                    Labels.Add(Rect);
                    FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(Span,FSlateLayoutTransform(At)),&Badge,ESlateDrawEffect::None,ColdSteelUI::GlassTint*Tint);
                    Text(Caption,LabelX,At.Y+2*U,LabelFont,Color);
                    break;
                }
            }
        }
    return Layer+3;
}
