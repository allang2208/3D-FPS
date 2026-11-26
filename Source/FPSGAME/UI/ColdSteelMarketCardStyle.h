#pragma once

#include "ColdSteelUIStyle.h"

namespace ColdSteelMarketCard
{
inline FButtonStyle CardStyle(bool Selected)
{
    using namespace ColdSteelUI;
    FButtonStyle Style=ButtonStyle();
    const FLinearColor RestFill=Selected?FLinearColor::FromSRGBColor(FColor(38,35,29,242)):FLinearColor::FromSRGBColor(FColor(28,28,31,238));
    const FLinearColor HoverFill=Selected?FLinearColor::FromSRGBColor(FColor(44,40,33,248)):FLinearColor::FromSRGBColor(FColor(35,35,39,246));
    const FLinearColor PressFill=FLinearColor::FromSRGBColor(FColor(24,24,27,248));
    const FLinearColor RestEdge=Selected?FLinearColor(HUDGold.R,HUDGold.G,HUDGold.B,.82f):Border;
    const FLinearColor HoverEdge=Selected?HUDGoldLight:FLinearColor(222.f/255.f,222.f/255.f,222.f/255.f,.36f);
    Style.SetNormal(RoundedBrush(RestFill,6,RestEdge,Selected?1.5f:1.f));
    Style.SetHovered(RoundedBrush(HoverFill,6,HoverEdge,1.5f));
    Style.SetPressed(RoundedBrush(PressFill,6,HUDGold,1.5f));
    return Style.SetNormalPadding(0).SetPressedPadding(0);
}

inline const FButtonStyle& CardFrame(bool Selected)
{
    static const FButtonStyle Active=CardStyle(true), Rest=CardStyle(false);
    return Selected?Active:Rest;
}

inline const FButtonStyle& PurchaseStyle()
{
    using namespace ColdSteelUI;
    static const FButtonStyle Style=[]
    {
        FButtonStyle Result=ButtonStyle();
        Result.SetNormal(RoundedBrush(FLinearColor::FromSRGBColor(FColor(62,53,36,232)),5,HUDGold,1.2f));
        Result.SetHovered(RoundedBrush(FLinearColor::FromSRGBColor(FColor(78,66,43,244)),5,HUDGoldLight,1.4f));
        Result.SetPressed(RoundedBrush(FLinearColor::FromSRGBColor(FColor(42,36,25,244)),5,HUDGold,1.4f));
        Result.SetDisabled(RoundedBrush(Gray(30,200),5,HUDGoldDim,1.f));
        return Result.SetNormalPadding(0).SetPressedPadding(0);
    }();
    return Style;
}

inline const FButtonStyle& SecondaryActionStyle()
{
    using namespace ColdSteelUI;
    static const FButtonStyle Style=[]
    {
        FButtonStyle Result=ButtonStyle();
        Result.SetNormal(RoundedBrush(Gray(38,218),5,Border,1.f));
        Result.SetHovered(RoundedBrush(Gray(54,236),5,FLinearColor(222.f/255.f,222.f/255.f,222.f/255.f,.42f),1.f));
        Result.SetPressed(RoundedBrush(Gray(26,236),5,HUDGoldDim,1.f));
        Result.SetDisabled(RoundedBrush(Gray(24,160),5,FLinearColor(222.f/255.f,222.f/255.f,222.f/255.f,.10f),1.f));
        return Result.SetNormalPadding(0).SetPressedPadding(0);
    }();
    return Style;
}
}
