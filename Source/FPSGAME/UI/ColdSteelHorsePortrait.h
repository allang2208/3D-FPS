#pragma once

#include "../Movement/StableHorseAppearance.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Styling/SlateBrush.h"

namespace ColdSteelHorsePortrait
{
inline UTexture2D* LoadAtlas(bool Soft=false)
{
    static TWeakObjectPtr<UTexture2D> Cache[2];
    auto& Entry=Cache[Soft?1:0];
    if(!Entry.IsValid())
        Entry=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelUI/HorseMarket")/
            (Soft?TEXT("FieldPlatesSoft.jpg"):TEXT("FieldPlates.jpg")));
    return Entry.Get();
}
inline void SetImage(FSlateBrush& Brush,UTexture2D* Atlas,const FStableHorseAppearance& Look)
{
    const int32 Variant=Look.Pattern?1+(Look.Pattern-1)*3+Look.Patch-(Look.Patch>Look.Coat?1:0):0;
    Brush.SetResourceObject(Atlas);
    Brush.DrawAs=ESlateBrushDrawType::Image;
    Brush.SetImageSize(FVector2D(384,184));
    Brush.SetUVRegion(FBox2f(FVector2f((Variant+.003f)/10,(Look.Coat+.003f)/4),
                             FVector2f((Variant+.997f)/10,(Look.Coat+.997f)/4)));
}
}
