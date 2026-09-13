#pragma once
#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "ColdSteelUIStyle.h"

// Pixel-based compatibility entry points for the shared cold-steel design system.
namespace GunsmithUI
{
    using ColdSteelUI::Gray;
    inline const FLinearColor Text=ColdSteelUI::TextPrimary,Secondary=ColdSteelUI::TextSecondary,Muted=ColdSteelUI::TextTertiary,Silver=ColdSteelUI::Accent;
    inline const FLinearColor Glass=ColdSteelUI::GlassTint,Edge=ColdSteelUI::Border,Row=ColdSteelUI::AttributeRow;
    FSlateFontInfo TextFont(float Size,bool Medium=false);
    FSlateFontInfo NumberFont(float Size,bool Medium=false);
}
