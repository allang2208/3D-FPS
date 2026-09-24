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
    // 工具提示「特殊性质」段：按性质类别上色，而不是按正负。
    // 与上面的正/负/中性三色分开，避免影响现有参数行配色。
    inline const FLinearColor ItemTraitSpecial  = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("176C86FF"))); // 特殊攻击模式
    inline const FLinearColor ItemTraitMagic    = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6B4FA8FF"))); // 魔法伤害与冷却
    inline const FLinearColor ItemTraitMechanic = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("0F7B6CFF"))); // 供弹、后坐、开镜
    inline const FLinearColor ItemTraitDrawback = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("B82020FF"))); // 代价
    inline const FLinearColor ItemTraitNeutral  = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("697278FF"))); // 其余

    FPSGAME_API FSlateBrush RoundedBrush(const FLinearColor& Fill, float Radius, const FLinearColor& Outline = Border, float OutlineWidth = 1.0f);
    /** 逐角半径版（X=左上 Y=右上 Z=右下 W=左下）：贴缝凸舌只圆外侧两角，圆接缝侧会咬出背景缺口。 */
    FPSGAME_API FSlateBrush RoundedBrushCorners(const FLinearColor& Fill, const FVector4& CornerRadii, const FLinearColor& Outline = FLinearColor::Transparent, float OutlineWidth = 0.f);
    FPSGAME_API FButtonStyle ButtonStyle(float Scale=1.f);
    // These legacy entry points take Slate points. Screen px -> points: px * .75 / PixelScale.
    FPSGAME_API FSlateFontInfo TextFont(float Size, bool bMedium = false);
    FPSGAME_API FSlateFontInfo NumberFont(float Size, bool bBold = false);
    FPSGAME_API float PixelScale(const UObject* Context);
    /** 滑移动画统一缓动（2026-09-24 用户"高帧率平滑过渡"）：进度变量仍由 FInterpConstantTo
     *  驱动（固定时长、帧率无关），渲染位移/透明度按 smoothstep T²(3−2T) 走——起步收尾皆静止、
     *  中段最快；抽屉、冶炼面板、升级弹层三层共用同一条曲线，骑乘收回仍保持同一取值＝刚体。 */
    inline float EaseSmooth(float T)
    {   const float X=FMath::Clamp(T,0.f,1.f);return X*X*(3.f-2.f*X);   }
    // Source cold-steel rarity/processing tokens; keep item semantics shared by UI surfaces.
    FPSGAME_API FLinearColor RarityColor(const FString& Rarity);
    FPSGAME_API FString RarityLabel(const FString& Rarity);
    inline const FLinearColor Enhanced = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("E9BF63FF")));
    inline const FLinearColor Crafted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("54D9DCFF")));
    inline const FLinearColor Enchanted = FLinearColor::FromSRGBColor(FColor::FromHex(TEXT("6FA7DEFF")));
}
