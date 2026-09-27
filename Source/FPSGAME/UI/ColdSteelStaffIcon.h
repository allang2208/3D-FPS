#pragma once
#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"

class UTexture2D;

namespace ColdSteelStaffIcon
{
// Called once when publishing/importing a staff icon, never from Paint or Tick.
void FrameVisiblePixels(FSlateBrush& Brush,const FColor* Pixels,int32 Width,int32 Height);
void FrameImportedTexture(FSlateBrush& Brush,UTexture2D* Texture);

// Return the upright draw size. A quarter-turn changes only the orientation.
inline FVector2D InventorySize(FVector2D Image,FVector2D Card,bool Rotated)
{
    const FVector2D Upright=Rotated?FVector2D(Card.Y,Card.X):Card;
    // The caption consumes 20 pixels of screen height. Reserve the same clearance
    // on both canonical axes so neither orientation changes the uniform scale.
    const double Fit=FMath::Min(FMath::Max(1.0,Upright.X-20)/FMath::Max(1.0,Image.X),
                               FMath::Max(1.0,Upright.Y-20)/FMath::Max(1.0,Image.Y));
    return Image*Fit;
}
}
