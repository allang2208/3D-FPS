#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelHUDLayout.h"
#include "ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"


int32 UColdSteelHUDWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    const auto* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    Result=PaintHUDNavigation(Geometry,Elements,Result,Style);
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
        const bool Split=Feedback.DamageResult.bResolved&&Feedback.DamageResult.HasAdditional();
        const FColdSteelHUDLayout Layout(View.X/S);
        const bool MatchingTarget=HUDDisplayTarget==Feedback.Target;
        const int32 EffectCount=MatchingTarget&&!Feedback.bKilled?HUDTargetEffects.Num():0;
        const float Width=FMath::Min(400.f*S,View.X-24.f*S),Height=(Split?134.f:90.f)*S;
        const FVector2D At((View.X-Width)*.5f,Layout.TargetTop*S);
        const FSlateBrush* Brush=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
        const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
        auto Fit=[&](FString Value,const FSlateFontInfo& Font,float Available){
            if(Measure->Measure(Value,Font).X<=Available)return Value;
            while(!Value.IsEmpty()&&Measure->Measure(Value+TEXT("…"),Font).X>Available)Value.LeftChopInline(1);
            return Value+TEXT("…");
        };
        auto Tint=[&](FLinearColor Color){Color.A*=Feedback.Opacity;return Color;};
        auto Box=[&](FVector2D Offset,FVector2D Size,FLinearColor Color){
            FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(At+Offset)),Brush,ESlateDrawEffect::None,Tint(Color));
        };
        auto Text=[&](const FString& Value,FVector2D Offset,const FSlateFontInfo& Font,FLinearColor Color){
            FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(FVector2D(Width,22.f*S),FSlateLayoutTransform(At+Offset)),Value,Font,ESlateDrawEffect::None,Tint(Color));
        };
        Box(FVector2D::ZeroVector,FVector2D(Width,Height),ColdSteelUI::Content);
        const FLinearColor HitColor=Feedback.bKilled?ColdSteelUI::Success:ColdSteelUI::Danger;
        const auto NameFont=ColdSteelUI::TextFont(14.f*.75f*S,true);
        Text(Fit(Feedback.Name.ToString()+(MatchingTarget?HUDTargetLevel:FString())+(Feedback.bKilled?TEXT(" · 击杀"):TEXT("")),NameFont,Width-102*S),FVector2D(10,6)*S,NameFont,Feedback.bKilled?HitColor:ColdSteelUI::TextPrimary);
        Text(FString::Printf(TEXT("-%.1f"),Feedback.Damage),FVector2D(Width-82.f*S,6.f*S),ColdSteelUI::NumberFont(14.f*.75f*S,true),HitColor);
        const float DetailHeight=Split?44.f:0.f;
        if(Split)
        {
            const auto& Before=Feedback.DamageResult.BeforeDefense;
            const auto& Applied=Feedback.DamageResult.Applied;
            auto Kind=[](double Physical,double Magic){return Physical>0&&Magic>0?TEXT("物理+魔法"):Magic>0?TEXT("魔法"):TEXT("物理");};
            Text(FString::Printf(TEXT("基础 · %s   -%.1f"),Kind(Before.BasePhysical,Before.BaseMagic),Applied.Base()),FVector2D(10,28)*S,ColdSteelUI::TextFont(12.f*.75f*S),ColdSteelUI::TextPrimary);
            Text(FString::Printf(TEXT("附加 · %s   -%.1f"),Kind(Before.AddedPhysical,Before.AddedMagic),Applied.Additional()),FVector2D(10,49)*S,ColdSteelUI::TextFont(12.f*.75f*S),ColdSteelUI::TextSecondary);
        }
        Box(FVector2D(10,31+DetailHeight)*S,FVector2D(Width-20.f*S,5.f*S),ColdSteelUI::ButtonNormal);
        const float Ratio=FMath::Clamp(Feedback.Health/FMath::Max(1.f,Feedback.MaxHealth),0.f,1.f);
        if(Ratio>0.f)Box(FVector2D(10,31+DetailHeight)*S,FVector2D((Width-20.f*S)*Ratio,5.f*S),ColdSteelUI::Danger);
        Text(TEXT("生命"),FVector2D(10,42+DetailHeight)*S,ColdSteelUI::TextFont(12.f*.75f*S),ColdSteelUI::TextSecondary);
        Text(FString::Printf(TEXT("%.1f / %.0f"),Feedback.Health,Feedback.MaxHealth),FVector2D(55,42+DetailHeight)*S,ColdSteelUI::NumberFont(12.f*.75f*S),ColdSteelUI::TextPrimary);
        // 韧性栏（2026-09-29，类别×阶级基准）：格式镜像生命行（12px 标签/等宽数值），
        // 填充用 Toughness 语义色；破韧瞬间（Toughness 归零）以满条深色短暂示意。
        if(Feedback.ToughnessThreshold>0.f)
        {
            Box(FVector2D(10,64+DetailHeight)*S,FVector2D(Width-20.f*S,4.f*S),ColdSteelUI::ButtonNormal);
            const float ToughRatio=FMath::Clamp(Feedback.Toughness/FMath::Max(1.f,Feedback.ToughnessThreshold),0.f,1.f);
            if(ToughRatio>0.f)Box(FVector2D(10,64+DetailHeight)*S,FVector2D((Width-20.f*S)*ToughRatio,4.f*S),ColdSteelUI::Toughness);
            Text(TEXT("韧性"),FVector2D(10,71+DetailHeight)*S,ColdSteelUI::TextFont(12.f*.75f*S),ColdSteelUI::TextSecondary);
            Text(FString::Printf(TEXT("%.0f / %.0f"),Feedback.Toughness,Feedback.ToughnessThreshold),FVector2D(55,71+DetailHeight)*S,ColdSteelUI::NumberFont(12.f*.75f*S),ColdSteelUI::TextPrimary);
        }
        // Actual target effects only. Preserve original split-damage and kill feedback.
        const float CellWidth=(Width-20*S)/3;
        for(int32 I=0;I<EffectCount;++I)
        {
            const auto& Effect=HUDTargetEffects[I];
            const FVector2D Offset(10*S+(I%3)*CellWidth,Height+6*S+(I/3)*25*S);
            Box(Offset,FVector2D(CellWidth-5*S,22*S),ColdSteelUI::Content);
            Box(Offset+FVector2D(3,7)*S,FVector2D(4,8)*S,Effect.Color);
            const auto EffectFont=ColdSteelUI::TextFont(11.f*.75f*S);
            Text(Fit(Effect.Text,EffectFont,CellWidth-20*S),Offset+FVector2D(11,3)*S,EffectFont,ColdSteelUI::TextPrimary);
        }
        Result+=2;
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
    const auto* Bow=Character->FindComponentByClass<UBowWeaponComponent>();
    const bool bBow=Bow&&Bow->IsEquipped();
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
