#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"

struct FSlateFontInfo;

namespace ColdSteelUI
{
    inline const FLinearColor GlassTint = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("171D23F5")));
    inline const FLinearColor Content = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("10151AB8")));
    inline const FLinearColor TextPrimary = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("DCE2E6FF")));
    inline const FLinearColor TextSecondary = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B5C0C8FF")));
    inline const FLinearColor TextTertiary = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("9AA4ADFF")));
    inline const FLinearColor Accent = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B8D6DFFF")));
    inline const FLinearColor Border = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("DCEAF038")));
    inline const FLinearColor Warning = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("F0BE71FF")));
    inline const FLinearColor Danger = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("FF8193FF")));
    inline const FLinearColor Success = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("68D5ADFF")));
    inline const FLinearColor ButtonNormal = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("28323BFF")));
    inline const FLinearColor ButtonHover = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("36434EFF")));
    inline const FLinearColor ButtonPressed = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("1B242CFF")));
    inline const FLinearColor AttributeRow = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("27303945")));
    inline const FLinearColor StatusCard = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("171D23E8")));
    inline const FLinearColor Tooltip = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("10151AFA")));
    // Item inspection cards: source white tooltip, explicitly requested 2026-09-09.
    inline const FLinearColor ItemTooltipSurface = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("F5F5F5FF")));
    inline const FLinearColor ItemTooltipText = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("292520FF")));
    inline const FLinearColor ItemTooltipSecondary = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6B5D4FFF")));
    inline const FLinearColor ItemTooltipBorder = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("00000033")));
    inline const FLinearColor ItemTooltipPositive = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("247124FF")));
    inline const FLinearColor ItemTooltipNegative = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B82020FF")));

    FPSGAME_API FSlateBrush RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline = Border, float OutlineWidth = 1.0f);
    FPSGAME_API FSlateFontInfo TextFont(float Size);
    FPSGAME_API FSlateFontInfo NumberFont(float Size, bool bBold = false);
    FPSGAME_API float PixelScale(const UObject* Context);
    // Source cold-steel rarity/processing tokens; keep item semantics shared by UI surfaces.
    FPSGAME_API FLinearColor RarityColor(const FString& Rarity);
    FPSGAME_API FString RarityLabel(const FString& Rarity);
    inline const FLinearColor Enhanced = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E9BF63FF")));
    inline const FLinearColor Crafted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("9B72C6FF")));
    inline const FLinearColor Enchanted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6FA7DEFF")));
}
