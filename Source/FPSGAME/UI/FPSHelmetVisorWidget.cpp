#include "FPSHelmetVisorWidget.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Engine/Texture2D.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"

void UFPSHelmetVisorWidget::Configure(UFPSPlayerBodyComponent* Body,UTexture2D* Texture)
{
    Source=Body;
    Visor.SetResourceObject(Texture);
    Visor.DrawAs=ESlateBrushDrawType::Image;
    Visor.ImageSize=FVector2D(Texture->GetSizeX(),Texture->GetSizeY());
    SetVisibility(ESlateVisibility::HitTestInvisible);
    // The view mode can change without inventory changing. No per-frame asset
    // lookup, JSON parsing, or component creation is needed to paint this layer.
    ForceVolatile(true);
}

int32 UFPSHelmetVisorWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,
    const FWidgetStyle& Style,bool Enabled) const
{
    const int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    const auto* PC=GetOwningPlayer();
    if(!Source.IsValid()||!PC||PC->GetPawn()!=Source->GetOwner()||
       PC->GetViewTarget()!=Source->GetOwner()||!Source->ShouldShowHelmetVisor())return Result;
    // Normalized coverage survives aspect/FOV/ADS changes; gameplay projection
    // and the central aim ray are never modified by the helmet.
    FSlateDrawElement::MakeBox(Elements,Result+1,
        Geometry.ToPaintGeometry(Geometry.GetLocalSize(),FSlateLayoutTransform()),
        &Visor,ESlateDrawEffect::None,FLinearColor::White);
    return Result+1;
}
