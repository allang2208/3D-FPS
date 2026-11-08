#include "ColdSteelStarMarrow.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/StarMarrowComponent.h"
#include "Layout/Geometry.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Styling/SlateBrush.h"
#include "Styling/WidgetStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"

int32 ColdSteelStarMarrow::Paint(const UStarMarrowComponent& Core,const FGeometry& Geometry,
    FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,float PixelToLocal)
{
    if(!Core.HUDVisible())return Layer;
    const FVector2D Center=Geometry.GetLocalSize()*.5f;
    const float Scale=LayoutScale(PixelToLocal,float(Center.Y));
    if(Scale<=0.f)return Layer;
    const float Width=FMath::Min(360.f*Scale,float(Geometry.GetLocalSize().X-40.f*Scale));
    if(Width<=0.f)return Layer;
    const float Alpha=Core.HUDAlpha();
    const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
    const FLinearColor Tint=Style.GetColorAndOpacityTint();
    const auto DrawText=[&](const FString& Text,const FSlateFontInfo& Font,FVector2D Pos,FLinearColor Color)
    {
        const FVector2D Size=Measure->Measure(Text,Font);
        const auto Shadow=Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Pos+FVector2D(0,Scale)));
        FSlateDrawElement::MakeText(Elements,Layer+2,Shadow,Text,Font,ESlateDrawEffect::None,FLinearColor(0,0,0,Color.A*.9f)*Tint);
        FSlateDrawElement::MakeText(Elements,Layer+3,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Pos)),Text,Font,ESlateDrawEffect::None,Color*Tint);
    };
    if(Alpha<=0.f)
    {
        // Transient cast rejection/awaiting feedback only; no permanent empty bar.
        const FString Notice=Core.HUDLabel();const auto Font=ColdSteelUI::NumberFont(14.f*.75f*Scale,true);
        const FVector2D Size=Measure->Measure(Notice,Font);
        DrawText(Notice,Font,Center+FVector2D(-Size.X*.5f,(BarTopOffset+20.f)*Scale),ColdSteelUI::HUDGoldLight);
        return Layer+3;
    }
    const float Seconds=FMath::Clamp(Core.Remaining(),0.f,UStarMarrowComponent::Duration);
    const float Progress=Seconds/UStarMarrowComponent::Duration;
    const FVector2D Size(Width,Width/3.f);
    const FVector2D Position(Center.X-Width*.5f,Center.Y+BarTopOffset*Scale);
    if(auto* Material=Core.HUDMaterial())
    {
        Material->SetScalarParameterValue(TEXT("ChargeProgress"),Progress);
        FSlateBrush Brush;Brush.DrawAs=ESlateBrushDrawType::Image;Brush.ImageSize=Size;Brush.SetResourceObject(Material);
        FSlateDrawElement::MakeBox(Elements,Layer+1,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(Position)),
            &Brush,ESlateDrawEffect::None,FLinearColor(1,1,1,Alpha)*Tint);
    }
    // Share the material's actual fill endpoints, not the artwork's transparent margins.
    const float FillLeft=Position.X+Width*.052f;
    const float FillWidth=Width*.896f;
    const auto* White=FCoreStyle::Get().GetBrush("WhiteBrush");
    const auto Mark=[&](float X,float Y,float W,float H,FLinearColor Color)
    {
        FSlateDrawElement::MakeBox(Elements,Layer+2,
            Geometry.ToPaintGeometry(FVector2D(W,H),FSlateLayoutTransform(FVector2D(X-W*.5f,Y))),
            White,ESlateDrawEffect::None,Color*Tint);
    };
    // Match the compass: 11 px minor labels, 16 px medium major labels.
    const auto TickFont=ColdSteelUI::NumberFont(11.f*.75f*Scale);
    for(int32 Index=0;Index<=4;++Index)
    {
        const float Fraction=float(Index)*.25f;
        const float X=FillLeft+FillWidth*Fraction;
        const bool Filled=Progress>0.f&&Progress+UE_SMALL_NUMBER>=Fraction;
        if(Index>0&&Index<4)
        {
            // Keep the dark hairline behind the shared HUD gold for contrast.
            const float Y=Position.Y+Size.Y*.485f,H=Size.Y*.12f;
            Mark(X,Y,2.5f*Scale,H,FLinearColor(.002f,.01f,.025f,Alpha*.92f));
            Mark(X+.35f*Scale,Y,.75f*Scale,H,
                (Filled?ColdSteelUI::HUDGoldLight:ColdSteelUI::HUDGoldDim).CopyWithNewOpacity(Alpha));
        }
        const FLinearColor Color=(Filled?ColdSteelUI::HUDGoldLight:ColdSteelUI::HUDGold).CopyWithNewOpacity(Alpha);
        Mark(X,Position.Y+Size.Y*.745f,Scale,3.f*Scale,Color);
        const FString Percent=FString::Printf(TEXT("%d%%"),Index*25);
        const FVector2D Extent=Measure->Measure(Percent,TickFont);
        DrawText(Percent,TickFont,FVector2D(X-Extent.X*.5f,Position.Y+Size.Y*.80f),Color);
    }
    const auto LabelFont=ColdSteelUI::NumberFont(16.f*.75f*Scale,true);
    const auto TimerFont=LabelFont;
    const FString Timer=FString::Printf(TEXT("%d%%  ·  %.1f s"),FMath::CeilToInt(Progress*100.f),Seconds);
    const FVector2D TimerSize=Measure->Measure(Timer,TimerFont);
    const float Top=Position.Y+Size.Y*.12f;
    const FLinearColor LabelColor=ColdSteelUI::HUDGoldLight.CopyWithNewOpacity(Alpha);
    DrawText(TEXT("充能"),LabelFont,FVector2D(Position.X+Width*.045f,Top),LabelColor);
    DrawText(Timer,TimerFont,FVector2D(Position.X+Width*.955f-TimerSize.X,Top),LabelColor);
    return Layer+3;
}
