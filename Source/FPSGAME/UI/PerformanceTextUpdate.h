#pragma once
#include "Components/TextBlock.h"

// Avoid invalidating layout for unchanged diagnostic labels and rows.
inline void SetPerformanceText(UTextBlock* Widget, const FText& Text)
{
    if (Widget && !Widget->GetText().ToString().Equals(Text.ToString(), ESearchCase::CaseSensitive))
        Widget->SetText(Text);
}
