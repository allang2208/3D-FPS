#include "ColdSteelHUDWidget.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"


int32 UColdSteelHUDWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    const auto* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    if(!Character||bInventoryOpen||bWarehouseOpen||PC->bShowMouseCursor||Character->IsAmmoWheelOpen())return Result;
    const FVector2D Center=Geometry.GetLocalSize()*.5;
    const float Scale=Geometry.GetLocalSize().Y/1080.f;
    FMonsterHitFeedback Feedback;
    const bool bHasFeedback=Character->GetMonsterHitFeedback(Feedback);
    const AActor* UseTarget=bHasFeedback?nullptr:ColdSteelWorldInteraction::TraceTarget(PC);
    const bool bTreasure=ColdSteelWorldInteraction::IsTreasureChest(UseTarget);
    const bool bFurnace=!bTreasure&&ColdSteelWorldInteraction::IsSmeltingFurnace(UseTarget);
    const bool bWorkbench=!bTreasure&&!bFurnace&&ColdSteelWorldInteraction::IsWorkbench(UseTarget);
    if(!bHasFeedback && (bTreasure||bFurnace||bWorkbench||ColdSteelWorldInteraction::IsExpeditionAltar(UseTarget)))
    {
        const float Pixel=1.f/ColdSteelUI::PixelScale(this);
        const FVector2D HintSize=FVector2D(232,48)*Pixel;
        const FVector2D HintAt=Center+FVector2D(-116,48)*Pixel;
        static const FSlateBrush HintBrush=ColdSteelUI::RoundedBrush(ColdSteelUI::Tooltip,ColdSteelUI::CardRadius);
        FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(HintSize,FSlateLayoutTransform(HintAt)),
            &HintBrush,ESlateDrawEffect::None,FLinearColor::White);
        if(!bTreasure||!ColdSteelWorldInteraction::IsTreasureChestActivated(UseTarget))
        FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(HintSize,FSlateLayoutTransform(HintAt+FVector2D(16,12)*Pixel)),
            TEXT("E"),ColdSteelUI::NumberFont(12.f*Pixel,true),ESlateDrawEffect::None,ColdSteelUI::Accent);
        const FString HintText=bTreasure?ColdSteelWorldInteraction::TreasureChestPrompt(UseTarget)
            :bFurnace?ColdSteelWorldInteraction::SmeltingFurnacePrompt(UseTarget)
            :bWorkbench?ColdSteelWorldInteraction::WorkbenchPrompt(UseTarget)
            :FString(TEXT("祭坛 · 打开出征面板"));
        FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(HintSize,FSlateLayoutTransform(HintAt+FVector2D(44,14)*Pixel)),
            HintText,ColdSteelUI::TextFont(10.5f*Pixel),ESlateDrawEffect::None,ColdSteelUI::TextPrimary);
        Result+=2;
    }
    if(bHasFeedback)
    {
        const float S=1.f/ColdSteelUI::PixelScale(this);
        const FVector2D View=Geometry.GetLocalSize();
        const float Width=FMath::Min(280.f*S,View.X-24.f*S),Height=64.f*S;
        const FVector2D At((View.X-Width)*.5f,FMath::Clamp(Center.Y+52.f*S,12.f*S,FMath::Max(12.f*S,View.Y-Height-12.f*S)));
        const FSlateBrush* Brush=FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));
        auto Tint=[&](FLinearColor Color){Color.A*=Feedback.Opacity;return Color;};
        auto Box=[&](FVector2D Offset,FVector2D Size,FLinearColor Color){
            FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(At+Offset)),Brush,ESlateDrawEffect::None,Tint(Color));
        };
        auto Text=[&](const FString& Value,FVector2D Offset,const FSlateFontInfo& Font,FLinearColor Color){
            FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(FVector2D(Width,22.f*S),FSlateLayoutTransform(At+Offset)),Value,Font,ESlateDrawEffect::None,Tint(Color));
        };
        Box(FVector2D::ZeroVector,FVector2D(Width,Height),ColdSteelUI::Content);
        const FLinearColor HitColor=Feedback.bKilled?ColdSteelUI::Success:ColdSteelUI::Danger;
        Text(Feedback.Name.ToString()+(Feedback.bKilled?TEXT(" · 击杀"):TEXT("")),FVector2D(10,6)*S,ColdSteelUI::TextFont(14.f*.75f*S,true),Feedback.bKilled?HitColor:ColdSteelUI::TextPrimary);
        Text(FString::Printf(TEXT("-%.1f"),Feedback.Damage),FVector2D(Width-82.f*S,6.f*S),ColdSteelUI::NumberFont(14.f*.75f*S,true),HitColor);
        Box(FVector2D(10,31)*S,FVector2D(Width-20.f*S,5.f*S),ColdSteelUI::ButtonNormal);
        const float Ratio=FMath::Clamp(Feedback.Health/FMath::Max(1.f,Feedback.MaxHealth),0.f,1.f);
        if(Ratio>0.f)Box(FVector2D(10,31)*S,FVector2D((Width-20.f*S)*Ratio,5.f*S),ColdSteelUI::Danger);
        Text(TEXT("生命"),FVector2D(10,42)*S,ColdSteelUI::TextFont(12.f*.75f*S),ColdSteelUI::TextSecondary);
        Text(FString::Printf(TEXT("%.1f / %.0f"),Feedback.Health,Feedback.MaxHealth),FVector2D(55,42)*S,ColdSteelUI::NumberFont(12.f*.75f*S),ColdSteelUI::TextPrimary);
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
    if(!Character->HasInventoryWeapon()||Character->IsTraversing())return Result+2;
    if(Character&&Character->HasInventoryWeapon()&&Character->IsAiming()&&Character->GetGunsmithOpticVariant()==TEXT("lpvo_1_6x")&&!bInventoryOpen&&!bWarehouseOpen&&!PC->bShowMouseCursor){
        const FVector2D Size=Geometry.GetLocalSize();
        FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(FVector2D(150,24),FSlateLayoutTransform(FVector2D(Size.X*.5f-75,Size.Y*.87f-3))),FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")),ESlateDrawEffect::None,FLinearColor(0,0,0,.65f));
        FSlateDrawElement::MakeText(Elements,Result+2,Geometry.ToPaintGeometry(FVector2D(220,24),FSlateLayoutTransform(FVector2D(Size.X*.5f-65,Size.Y*.87f))),
            FString::Printf(TEXT("%.1f×  |  滚轮调倍率"),Character->GetOpticMagnification()),FCoreStyle::GetDefaultFontStyle("Regular",12),ESlateDrawEffect::None,FLinearColor::White);
        return Result+2;
    }
    if(Character->IsAiming())return Result+2;
    const FVector2D Extent=Character->GetCrosshairHalfExtent(Geometry.GetLocalSize());
    const float Length=9.f*Scale,HalfWidth=1.5f*Scale;
    const FSlateBrush* Brush=FCoreStyle::Get().GetBrush("WhiteBrush");
    auto Bar=[&](FVector2D Position,FVector2D Size){
        FSlateDrawElement::MakeBox(Elements,Result+1,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Center+Position)),
            Brush,ESlateDrawEffect::None,FLinearColor::White);
    };
    Bar(FVector2D(-HalfWidth,-Extent.Y-Length),FVector2D(HalfWidth*2,Length));
    Bar(FVector2D(-HalfWidth,Extent.Y),FVector2D(HalfWidth*2,Length));
    Bar(FVector2D(-Extent.X-Length,-HalfWidth),FVector2D(Length,HalfWidth*2));
    Bar(FVector2D(Extent.X,-HalfWidth),FVector2D(Length,HalfWidth*2));
    return Result+2;
}
