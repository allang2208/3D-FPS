#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateBrush.h"

struct FSlateFontInfo;
struct FButtonStyle;

namespace ColdSteelUI
{
    // Authoritative palette: Docs/UI/ui-cold-steel-design-system.md (2026-09-12).
    inline FLinearColor Gray(uint8 Value,uint8 Alpha=255){return FLinearColor::FromSRGBColor(FColor(Value,Value,Value,Alpha));}
    inline const FLinearColor GlassTint = Gray(26,248);
    inline const FLinearColor GlassFallback = Gray(29);
    inline const FLinearColor HeaderTint = Gray(100,22);
    inline const FLinearColor Content = Gray(18,235);
    inline const FLinearColor TextPrimary = Gray(232);
    inline const FLinearColor TextSecondary = Gray(183);
    inline const FLinearColor TextTertiary = Gray(145);
    inline const FLinearColor Accent = Gray(214);
    inline const FLinearColor Border = Gray(222,46);
    inline const FLinearColor Warning = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("F0BE71FF")));
    inline const FLinearColor Stamina = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("A1A44FFF")));
    inline const FLinearColor StaminaDeep = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("666B35FF")));
    inline const FLinearColor Danger = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("FF8193FF")));
    inline const FLinearColor Success = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("68D5ADFF")));
    inline const FLinearColor ButtonNormal = Gray(43,190);
    inline const FLinearColor ButtonHover = Gray(65,230);
    inline const FLinearColor ButtonPressed = Gray(24,240);
    inline const FLinearColor ButtonDisabled = Gray(22,120);
    inline const FLinearColor AttributeRow = Gray(200,9);
    inline const FLinearColor StatusCard = Gray(37,232);
    inline const FLinearColor Tooltip = Gray(25,252);
    // Shared tooltip-card tokens (equipment tooltip and the building panel use the same card).
    inline const FLinearColor TooltipGlass = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0B1116FA")));
    inline const FLinearColor TooltipOutline = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("7187928A")));
    inline const FLinearColor TooltipRule = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B8D6DF3D")));
    inline const FLinearColor TooltipCloseNormal = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("C83232CC")));
    inline const FLinearColor TooltipCloseHover = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("DC4646FF")));
    inline constexpr float GlassBlurStrength=9.f,PanelRadius=10.f,CardRadius=8.f,ButtonRadius=6.f;
    inline constexpr int32 GlassBlurRadius=21;
    inline constexpr float ActionHeight=36.f,ActionGap=4.f;
    inline constexpr float NavigationSize=88.f,NavigationGap=25.f,NavigationRight=32.f;
    inline constexpr float NavigationHoverScale=1.25f,NavigationHoverDuration=.2f;
    inline constexpr float NavigationOverflow=NavigationSize*(NavigationHoverScale-1.f)*.5f;
// The drawer hugs the right screen edge; the navigation strip steps aside while it is out, so it
// reserves no width. Keep this at zero when changing NavigationRight/Size/Overflow.
inline constexpr float NavigationDrawerInset=0.f;
    inline const FLinearColor NavigationSelected = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("176C86FF")));
    inline const FLinearColor NavigationKey = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("54D9DCFF")));
    inline constexpr float InventoryItemRadius=5.f,ProcessingCornerUnderlap=.5f;
    // Item inspection cards: source white tooltip, explicitly requested 2026-09-09.
    inline const FLinearColor ItemTooltipSurface = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("EEF0F2FF")));
    inline const FLinearColor ItemTooltipHeader = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E2E6E9FF")));
    inline const FLinearColor ItemTooltipText = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("252A2EFF")));
    inline const FLinearColor ItemTooltipSecondary = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("697278FF")));
    inline const FLinearColor ItemTooltipRule = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("CDD2D5FF")));
    inline const FLinearColor ItemTooltipBorder = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("00000033")));
    inline const FLinearColor ItemTooltipPositive = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("247124FF")));
    inline const FLinearColor ItemTooltipNegative = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B82020FF")));
    inline const FLinearColor ItemTooltipDisclosure = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("176C86FF")));
    inline const FLinearColor ItemTooltipDisclosureFlash = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("57BCD5FF")));
    inline const FLinearColor ItemTooltipDisclosureOutline = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("123D4BFF")));

    FPSGAME_API FSlateBrush RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline = Border, float OutlineWidth = 1.0f);
    FPSGAME_API FButtonStyle ButtonStyle(float Scale=1.f);
    // These legacy entry points take Slate points. Screen px -> points: px * .75 / PixelScale.
    FPSGAME_API FSlateFontInfo TextFont(float Size, bool bMedium = false);
    FPSGAME_API FSlateFontInfo NumberFont(float Size, bool bBold = false);
    FPSGAME_API float PixelScale(const UObject* Context);
    // Source cold-steel rarity/processing tokens; keep item semantics shared by UI surfaces.
    FPSGAME_API FLinearColor RarityColor(const FString& Rarity);
    FPSGAME_API FString RarityLabel(const FString& Rarity);
    inline const FLinearColor Enhanced = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E9BF63FF")));
    inline const FLinearColor Crafted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("54D9DCFF")));
    inline const FLinearColor Enchanted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6FA7DEFF")));
}
