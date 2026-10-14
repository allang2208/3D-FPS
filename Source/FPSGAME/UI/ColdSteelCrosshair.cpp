#include "ColdSteelHUDWidget.h"
#include "ColdSteelExplosiveWarnings.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "HAL/PlatformTime.h"
#include "ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"

namespace
{
int32 PaintBowRhythm(const UBowWeaponComponent& Bow,const FGeometry& Geometry,
    FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,float S)
{
    FBowDrawRhythm Rhythm;
    if (!Bow.GetDrawRhythm(Rhythm)) return Layer;
    constexpr float Width=208.f,TrackWidth=192.f;
    const FVector2D At=Geometry.GetLocalSize()*.5f+FVector2D(-Width*.5f,50.f)*S;
    const float Duration=Rhythm.FullDrawSeconds+ColdSteelBow::PerfectReleaseWindow+.30f;
    const float Progress=FMath::Clamp(Rhythm.Elapsed/Duration,0.f,1.f);
    const float WindowStart=Rhythm.FullDrawSeconds/Duration;
    const float WindowWidth=ColdSteelBow::PerfectReleaseWindow/Duration;
    const bool Late=Rhythm.Elapsed>Rhythm.FullDrawSeconds+ColdSteelBow::PerfectReleaseWindow;
    auto Tint=[&](FLinearColor Color){Color*=Style.GetColorAndOpacityTint();Color.A*=Rhythm.Opacity;return Color;};
    const auto* White=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
    auto Box=[&](int32 Z,FVector2D Offset,FVector2D Size,FLinearColor Color)
    {
        FSlateDrawElement::MakeBox(Elements,Layer+Z,Geometry.ToPaintGeometry(Size*S,FSlateLayoutTransform(At+Offset*S)),
            White,ESlateDrawEffect::None,Tint(Color));
    };
    const auto Frame=ColdSteelUI::RoundedBrush(FLinearColor::White,ColdSteelUI::ButtonRadius*S,
        Tint(Rhythm.bPerfect?ColdSteelUI::HUDGold:ColdSteelUI::Border),S);
    FSlateDrawElement::MakeBox(Elements,Layer+1,Geometry.ToPaintGeometry(FVector2D(Width,38.f)*S,FSlateLayoutTransform(At)),
        &Frame,ESlateDrawEffect::None,Tint(ColdSteelUI::GlassTint));
    Box(2,FVector2D(8,24),FVector2D(TrackWidth,6),ColdSteelUI::Content);
    if (Progress>0.f)
        Box(3,FVector2D(8,24),FVector2D(TrackWidth*Progress,6),Late?ColdSteelUI::TextTertiary:ColdSteelUI::Accent);
    Box(4,FVector2D(8+TrackWidth*WindowStart,23),FVector2D(TrackWidth*WindowWidth,8),
        Rhythm.bPerfect?ColdSteelUI::HUDGoldLight:Late?ColdSteelUI::HUDGoldDim:ColdSteelUI::HUDGold);
    // The marker reads the combat clock directly; UI easing must not shift the release window.
    Box(5,FVector2D(7+TrackWidth*Progress,21),FVector2D(2,12),ColdSteelUI::TextPrimary);
    static const FString DrawLabel=TEXT("拉弓 · 金色区间松手");
    static const FString LateLabel=TEXT("节拍已过 · 满拉");
    static const FString PerfectLabel=FString::Printf(TEXT("松手 · 伤害 +%.0f%%"),(ColdSteelBow::PerfectReleaseMultiplier-1.f)*100.f);
    static const FString ReleasedLabel=FString::Printf(TEXT("完美释放 · 伤害 +%.0f%%"),(ColdSteelBow::PerfectReleaseMultiplier-1.f)*100.f);
    const FString& Label=Rhythm.bReleased?ReleasedLabel:Rhythm.bPerfect?PerfectLabel:Late?LateLabel:DrawLabel;
    FSlateDrawElement::MakeText(Elements,Layer+5,Geometry.ToPaintGeometry(FVector2D(TrackWidth,18)*S,FSlateLayoutTransform(At+FVector2D(8,4)*S)),
        Label,ColdSteelUI::TextFont(12.f*.75f*S),ESlateDrawEffect::None,
        Tint(Rhythm.bPerfect?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextSecondary));
    return Layer+5;
}
}

int32 UColdSteelHUDWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    auto* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    Result=PaintHUDNavigation(Geometry,Elements,Result,Style);
    Result=ColdSteelExplosiveWarnings::Paint(PC,Geometry,Elements,Result,Style.GetColorAndOpacityTint());
    if(!Character||bInventoryOpen||bExternalDrawerOpen||bWarehouseOpen||PC->bShowMouseCursor||Character->IsAmmoWheelOpen())return Result;
    const FVector2D Center=Geometry.GetLocalSize()*.5;
    const float Scale=Geometry.GetLocalSize().Y/1080.f;
    FMonsterHitFeedback Feedback;
    const bool bHasFeedback=Character->GetMonsterHitFeedback(Feedback);
    // 2026-09-24：原「准星下方交互提示」即时绘制块已移除——高炉/工作台/宝箱/储物箱/拾取/门/祭坛/宝箱
    // 全部改由 UColdSteelHUDWidget::UpdateInteractHint 的毛玻璃小浮窗统一承载（NativeTick 驱动）。
    if(bHasFeedback)
    {
        const float S=1.f/ColdSteelUI::PixelScale(this);
        const FVector2D View=Geometry.GetLocalSize();
        const FColdSteelHUDLayout Layout(View.X/S);
        const bool Split=Feedback.DamageResult.bResolved&&Feedback.DamageResult.HasAdditional();
        const bool MatchingTarget=HUDDisplayTarget==Feedback.Target;
        const bool MatchingMeters=HUDMeterTarget==Feedback.Target;
        const bool HasToughness=Feedback.ToughnessThreshold>0.f;
        const int32 EffectCount=MatchingTarget&&!Feedback.bKilled?HUDTargetEffects.Num():0;
        const float Width=FMath::Max(1.f,FMath::Min(440.f,float(View.X/S)-24.f));
        const float ContentWidth=FMath::Max(1.f,Width-24.f);
        const bool InlineResources=Width>=340.f;
        const int32 Columns=FMath::Clamp(FMath::FloorToInt(ContentWidth/125.f),1,3);
        const int32 EffectRows=FMath::DivideAndRoundUp(EffectCount,Columns);
        constexpr float ResourceTop=24.f;
        const float ResourceRowHeight=InlineResources?20.f:28.f;
        const float ResourceBottom=ResourceTop+(HasToughness?2.f:1.f)*ResourceRowHeight;
        const float DetailHeight=Split?(InlineResources?20.f:36.f):0.f;
        const float EffectsTop=ResourceBottom+DetailHeight;
        const float Height=EffectsTop+EffectRows*22.f+4.f;
        const FVector2D At((View.X-Width*S)*.5f,Layout.TargetTop*S);
        const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
        const auto NameFont=ColdSteelUI::TextFont(14.f*.75f*S,true);
        const auto LabelFont=ColdSteelUI::TextFont(12.f*.75f*S);
        const auto NumberFont=ColdSteelUI::NumberFont(12.f*.75f*S);
        const auto DamageFont=ColdSteelUI::NumberFont(14.f*.75f*S);
        auto Fit=[&](FString Value,const FSlateFontInfo& Font,float Available){
            if(Measure->Measure(Value,Font).X<=Available)return Value;
            while(!Value.IsEmpty()&&Measure->Measure(Value+TEXT("…"),Font).X>Available)Value.LeftChopInline(1);
            return Value+TEXT("…");
        };
        auto Tint=[&](FLinearColor Color){Color*=Style.GetColorAndOpacityTint();Color.A*=Feedback.Opacity;return Color;};
        auto Box=[&](FVector2D Offset,FVector2D Size,FLinearColor Color,float Radius=0.f,FLinearColor Edge=FLinearColor::Transparent){
            // Fade the outline explicitly: Slate's secondary outline colour ignores render opacity.
            const auto Brush=ColdSteelUI::RoundedBrush(FLinearColor::White,Radius*S,Tint(Edge),Edge.A>0.f?S:0.f);
            FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size*S,FSlateLayoutTransform(At+Offset*S)),&Brush,ESlateDrawEffect::None,Tint(Color));
        };
        auto Text=[&](const FString& Value,FVector2D Offset,const FSlateFontInfo& Font,FLinearColor Color){
            FSlateDrawElement::MakeText(Elements,Result+5,Geometry.ToPaintGeometry(FVector2D(ContentWidth,24.f)*S,FSlateLayoutTransform(At+Offset*S)),Value,Font,ESlateDrawEffect::None,Tint(Color));
        };
        auto RightText=[&](const FString& Value,float Y,const FSlateFontInfo& Font,FLinearColor Color){
            Text(Value,FVector2D(Width-12.f-Measure->Measure(Value,Font).X/S,Y),Font,Color);
        };
        Box(FVector2D::ZeroVector,FVector2D(Width,Height),ColdSteelUI::GlassTint,ColdSteelUI::PanelRadius,ColdSteelUI::Border);
        const FLinearColor HitColor=Feedback.bKilled?ColdSteelUI::Success:ColdSteelUI::Danger;
        const FString DamageText=FString::Printf(TEXT("-%.1f"),Feedback.Damage);
        const float DamageWidth=Measure->Measure(DamageText,DamageFont).X/S;
        Text(Fit(Feedback.Name.ToString()+(MatchingTarget?HUDTargetLevel:FString())+(Feedback.bKilled?TEXT(" · 击杀"):TEXT("")),NameFont,FMath::Max(1.f,ContentWidth-DamageWidth-12.f)*S),FVector2D(12,4),NameFont,Feedback.bKilled?HitColor:ColdSteelUI::TextPrimary);
        RightText(DamageText,4,DamageFont,HitColor);

        const double Now=FPlatformTime::Seconds();
        // Both resources share a fixed value column, including the poise-phase timer.
        // Changing digit counts must not change either track's length.
        const float ResourceValueWidth=FMath::Min(144.f,FMath::Max(1.f,ContentWidth-124.f));
        auto ResourceRow=[&](float Y,const FString& Label,const FString& Value,float Ratio,
            const FLinearColor& Fill,const FLinearColor& Deep,const FLinearColor& LabelColor,
            const FLinearColor& ValueColor,const FLinearColor& Edge,float TrackHeight)
        {
            const bool Inline=InlineResources;
            const FString DisplayValue=Fit(Value,NumberFont,(Inline?ResourceValueWidth:FMath::Max(1.f,ContentWidth-36.f))*S);
            Text(Label,FVector2D(12,Y+1),LabelFont,LabelColor);
            RightText(DisplayValue,Y+1,NumberFont,ValueColor);
            const float TrackX=Inline?48.f:12.f;
            const float TrackY=Y+(Inline?7.f:19.f);
            const float TrackWidth=Inline?ContentWidth-36.f-ResourceValueWidth-8.f:ContentWidth;
            ColdSteelUI::PaintResourceMeter(Geometry,Elements,Result+2,At+FVector2D(TrackX,TrackY)*S,FVector2D(TrackWidth,TrackHeight)*S,
                Ratio,Fill,Deep,Edge,Tint(FLinearColor::White));
        };
        const float HealthRatio=FMath::Clamp(Feedback.Health/FMath::Max(1.f,Feedback.MaxHealth),0.f,1.f);
        ResourceRow(ResourceTop,TEXT("生命"),FString::Printf(TEXT("%.1f / %.0f"),Feedback.Health,Feedback.MaxHealth),
            MatchingMeters?HUDTargetHealthTransition.ValueAt(Now):HealthRatio,
            ColdSteelUI::Health,ColdSteelUI::HealthDeep,ColdSteelUI::TextSecondary,
            HealthRatio<=.25f?ColdSteelUI::Danger:ColdSteelUI::TextPrimary,
            HealthRatio<=.25f?ColdSteelUI::Danger:ColdSteelUI::Border,8.f);
        if(HasToughness)
        {
            const float ToughRatio=FMath::Clamp(Feedback.Toughness/FMath::Max(1.f,Feedback.ToughnessThreshold),0.f,1.f);
            const bool Broken=Feedback.ToughnessPhase==EMonsterToughnessPhase::Broken;
            const bool Recovering=Feedback.ToughnessPhase==EMonsterToughnessPhase::Recovering;
            FString PoiseText=FString::Printf(TEXT("%.0f / %.0f"),Feedback.Toughness,Feedback.ToughnessThreshold);
            if(!Feedback.bKilled&&(Broken||Recovering))PoiseText+=FString::Printf(TEXT("  %.1fs"),Feedback.ToughnessPhaseRemaining);
            ResourceRow(ResourceTop+ResourceRowHeight,Broken?TEXT("破韧"):Recovering?TEXT("回韧"):TEXT("韧性"),PoiseText,
                MatchingMeters?HUDTargetToughnessTransition.ValueAt(Now):ToughRatio,
                ColdSteelUI::Toughness,ColdSteelUI::ToughnessDeep,Broken?ColdSteelUI::Danger:ColdSteelUI::TextSecondary,
                ColdSteelUI::TextPrimary,ColdSteelUI::Border,6.f);
        }
        if(Split)
        {
            const auto& Before=Feedback.DamageResult.BeforeDefense;
            const auto& Applied=Feedback.DamageResult.Applied;
            auto Kind=[](double Physical,double Magic){return Physical>0&&Magic>0?TEXT("物理+魔法"):Magic>0?TEXT("魔法"):TEXT("物理");};
            const float DetailWidth=InlineResources?(ContentWidth-12.f)*.5f:ContentWidth;
            auto DamagePart=[&](const FString& Label,double Value,int32 Index)
            {
                const float X=12.f+(InlineResources?Index*(DetailWidth+12.f):0.f);
                const float Y=ResourceBottom+(InlineResources?0.f:Index*18.f);
                const FString Amount=FString::Printf(TEXT("-%.1f"),Value);
                const float AmountWidth=Measure->Measure(Amount,NumberFont).X/S;
                Text(Fit(Label,LabelFont,FMath::Max(1.f,DetailWidth-AmountWidth-6.f)*S),FVector2D(X,Y),LabelFont,ColdSteelUI::TextSecondary);
                Text(Amount,FVector2D(X+DetailWidth-AmountWidth,Y),NumberFont,ColdSteelUI::TextPrimary);
            };
            DamagePart(FString::Printf(TEXT("基础·%s"),Kind(Before.BasePhysical,Before.BaseMagic)),Applied.Base(),0);
            DamagePart(FString::Printf(TEXT("附加·%s"),Kind(Before.AddedPhysical,Before.AddedMagic)),Applied.Additional(),1);
        }
        if(EffectCount>0)
        {
            const float CellWidth=(ContentWidth-(Columns-1)*6.f)/Columns;
            for(int32 I=0;I<EffectCount;++I)
            {
                const auto& Effect=HUDTargetEffects[I];
                const FVector2D Offset(12+(I%Columns)*(CellWidth+6),EffectsTop+(I/Columns)*22);
                Box(Offset,FVector2D(CellWidth,20),ColdSteelUI::StatusCard,ColdSteelUI::ButtonRadius,ColdSteelUI::Border);
                Box(Offset+FVector2D(5,6),FVector2D(3,8),Effect.Color,1.5f);
                Text(Fit(Effect.Text,LabelFont,FMath::Max(1.f,CellWidth-18)*S),Offset+FVector2D(12,1),LabelFont,ColdSteelUI::TextPrimary);
            }
        }
        // Match the player's rounded gold corner arcs without colouring the whole frame.
        for(int32 X:{0,1})for(int32 Y:{0,1})
        {
            constexpr float Radius=ColdSteelUI::PanelRadius,Inset=.75f;
            TArray<FVector2D> Points;
            auto Point=[&](FVector2D P){if(X)P.X=Width-P.X;if(Y)P.Y=Height-P.Y;Points.Add(At+P*S);};
            Point(FVector2D(Radius+6,Inset));
            for(int32 I=0;I<=8;++I)
            {
                const float Angle=-PI*.5f-I*(PI*.5f/8);
                Point(FVector2D(Radius+(Radius-Inset)*FMath::Cos(Angle),Radius+(Radius-Inset)*FMath::Sin(Angle)));
            }
            Point(FVector2D(Inset,Radius+6));
            FSlateDrawElement::MakeLines(Elements,Result+6,Geometry.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,Tint(ColdSteelUI::HUDGold),true,1.25f*S);
        }
        Result+=6;
    }
    const float HitAlpha=Character->GetHitMarkerOpacity();
    if(HitAlpha>0.f)
    {
        for(int32 X : {-1,1}) for(int32 Y : {-1,1})
        {
            TArray<FVector2D> Points;
            Points.Add(Center+FVector2D(X*10.f,Y*10.f)*Scale);
            Points.Add(Center+FVector2D(X*20.f,Y*20.f)*Scale);
            FSlateDrawElement::MakeLines(Elements,Result+2,Geometry.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,bHasFeedback&&Feedback.bKilled?ColdSteelUI::Success.CopyWithNewOpacity(HitAlpha):FLinearColor(1,1,1,HitAlpha),true,2.f*Scale);
        }
    }
    // Delayed projectiles and magic can confirm a hit after the weapon is put away.
    if(const auto* Electric=Character->FindComponentByClass<UFPSElectricMagicComponent>();Electric&&Electric->IsCharging())
    {
        const float Charge=Electric->LanceChargeFraction();const auto Extent=Electric->LanceCrosshairExtent(Geometry.GetLocalSize());
        const auto Color=ColdSteelUI::ActionProgressColor(Charge);
        const float DotSize=FMath::Max(2.f,3.f*Scale);
        const auto* Brush=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
        auto Bar=[&](FVector2D Position,FVector2D Size)
        {
            const float Border=FMath::Max(.6f,Scale);
            FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size+FVector2D(Border*2),FSlateLayoutTransform(Center+Position-FVector2D(Border))),
                Brush,ESlateDrawEffect::None,FLinearColor(0,0,0,.75f));
            FSlateDrawElement::MakeBox(Elements,Result+2,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Center+Position)),
                Brush,ESlateDrawEffect::None,Color);
        };
        const float Length=9.f*Scale*(1.f-Charge),HalfWidth=DotSize*.5f;
        if(Charge<1.f&&Length>.01f)
        {
            // Inner edges track the projected scatter radius, as the gun crosshair does.
            Bar(FVector2D(-HalfWidth,-Extent.Y-Length),FVector2D(DotSize,Length));
            Bar(FVector2D(-HalfWidth,Extent.Y),FVector2D(DotSize,Length));
            Bar(FVector2D(-Extent.X-Length,-HalfWidth),FVector2D(Length,DotSize));
            Bar(FVector2D(Extent.X,-HalfWidth),FVector2D(Length,DotSize));
        }
        Bar(FVector2D(-HalfWidth),FVector2D(DotSize));
        return Result+2;
    }
    const auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>();
    const bool bBow=Bow&&Bow->IsEquipped();
    // Independent of the reticle/sight gate: physical sights and full ADS hide
    // the crosshair, but never the owner's draw timing cue.
    if(bBow&&!Character->IsTraversing())
        Result=PaintBowRhythm(*Bow,Geometry,Elements,Result+2,Style,1.f/ColdSteelUI::PixelScale(this));
    if(Character->IsTraversing() || (bBow ? !Bow->ShouldShowCrosshair() : !Character->HasInventoryWeapon()&&!Character->HasOffhandPistol()))return Result+2;
    if(!bBow&&Character->HasInventoryWeapon()&&Character->IsAiming()&&Character->GetGunsmithOpticVariant()==TEXT("lpvo_1_6x")&&!bInventoryOpen&&!bWarehouseOpen&&!PC->bShowMouseCursor){
        const FVector2D Size=Geometry.GetLocalSize();
        FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(FVector2D(150,24),FSlateLayoutTransform(FVector2D(Size.X*.5f-75,Size.Y*.87f-3))),FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")),ESlateDrawEffect::None,FLinearColor(0,0,0,.65f));
        FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(FVector2D(220,24),FSlateLayoutTransform(FVector2D(Size.X*.5f-65,Size.Y*.87f))),
            FString::Printf(TEXT("%.1f×  |  滚轮调倍率"),Character->GetOpticMagnification()),FCoreStyle::GetDefaultFontStyle("Regular",12),ESlateDrawEffect::None,FLinearColor::White);
        return Result+2;
    }
    if(!bBow&&Character->IsAiming())return Result+2;
    const float BowAim=bBow?Bow->AimAlpha():0.f;
    const FVector2D Extent=Character->GetCrosshairHalfExtent(Geometry.GetLocalSize());
    if(!bBow&&Character->HasInventoryWeapon()&&Character->IsSuper90Weapon())
    {
        // Four open quadrants, with gaps on the horizontal/vertical axes.
        // Cache the unit arc; only its projected radius changes with hip spread.
        constexpr int32 ArcSegments=24;
        static const TArray<FVector2D> UnitArc=[]
        {
            TArray<FVector2D> Points;
            Points.Reserve(ArcSegments+1);
            for(int32 I=0;I<=ArcSegments;++I)
            {
                const float Angle=FMath::DegreesToRadians(5.f+80.f*I/ArcSegments);
                Points.Emplace(FMath::Cos(Angle),FMath::Sin(Angle));
            }
            return Points;
        }();
        const float Stroke=FMath::Max(1.25f,2.f*Scale);
        const float Border=FMath::Max(.65f,.85f*Scale);
        // Keep the inner edge at the existing spread boundary, as with the bars.
        const float Radius=FMath::Max(Extent.X,Extent.Y)+Stroke*.5f;
        TArray<FVector2D> Points;
        Points.SetNumUninitialized(UnitArc.Num());
        for(int32 Quadrant=0;Quadrant<4;++Quadrant)
        {
            for(int32 I=0;I<UnitArc.Num();++I)
            {
                const FVector2D P=UnitArc[I];
                const FVector2D Direction=Quadrant==0?P:Quadrant==1?FVector2D(-P.Y,P.X)
                    :Quadrant==2?-P:FVector2D(P.Y,-P.X);
                Points[I]=Center+Direction*Radius;
            }
            FSlateDrawElement::MakeLines(Elements,Result+1,Geometry.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,FLinearColor(0,0,0,.72f)*Style.GetColorAndOpacityTint(),true,Stroke+Border*2.f);
            // Keep the hit marker on Result+2 above both strokes.
            FSlateDrawElement::MakeLines(Elements,Result+1,Geometry.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,FLinearColor::White*Style.GetColorAndOpacityTint(),true,Stroke);
        }
        return Result+2;
    }
    const float Length=9.f*Scale,HalfWidth=1.5f*Scale;
    const FSlateBrush* Brush=FCoreStyle::Get().GetBrush("WhiteBrush");
    // A fitted physical pin takes over in ADS; keep the fallback dot only
    // for bow recipes without a sight. Hip spread bars retain their fade.
    if(BowAim>0.f&&!Bow->HasPhysicalSight())
    {
        const float DotSize=2.5f*Scale;
        FSlateDrawElement::MakeBox(Elements,Result+1,
            Geometry.ToPaintGeometry(FVector2D(DotSize),FSlateLayoutTransform(Center-FVector2D(DotSize*.5f))),
            Brush,ESlateDrawEffect::None,FLinearColor::White.CopyWithNewOpacity(BowAim));
    }
    if(BowAim>=1.f)return Result+2;
    auto Bar=[&](FVector2D Position,FVector2D Size){
        FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Center+Position)),
            Brush,ESlateDrawEffect::None,FLinearColor::White.CopyWithNewOpacity(1.f-BowAim));
    };
    Bar(FVector2D(-HalfWidth,-Extent.Y-Length),FVector2D(HalfWidth*2,Length));
    Bar(FVector2D(-HalfWidth,Extent.Y),FVector2D(HalfWidth*2,Length));
    Bar(FVector2D(-Extent.X-Length,-HalfWidth),FVector2D(Length,HalfWidth*2));
    Bar(FVector2D(Extent.X,-HalfWidth),FVector2D(Length,HalfWidth*2));
    return Result+2;
}
