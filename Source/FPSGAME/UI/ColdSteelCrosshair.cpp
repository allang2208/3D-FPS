#include "ColdSteelHUDWidget.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"


int32 UColdSteelHUDWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    const auto* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    const int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    if(!Character||!Character->HasInventoryWeapon()||Character->IsTraversing()
        ||bInventoryOpen||bWarehouseOpen||PC->bShowMouseCursor)return Result;
    const FVector2D Center=Geometry.GetLocalSize()*.5;
    const float Scale=Geometry.GetLocalSize().Y/1080.f;
    const float HitAlpha=Character->GetHitMarkerOpacity();
    if(HitAlpha>0.f)
    {
        for(int32 X : {-1,1}) for(int32 Y : {-1,1})
        {
            TArray<FVector2D> Points;
            Points.Add(Center+FVector2D(X*10.f,Y*10.f)*Scale);
            Points.Add(Center+FVector2D(X*20.f,Y*20.f)*Scale);
            FSlateDrawElement::MakeLines(Elements,Result+2,Geometry.ToPaintGeometry(),Points,
                ESlateDrawEffect::None,FLinearColor(1,1,1,HitAlpha),true,2.f*Scale);
        }
    }
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
