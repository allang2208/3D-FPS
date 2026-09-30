#pragma once
#include "CoreMinimal.h"
#include "ColdSteelUIStyle.h"

// Physical pixels. UMG and immediate HUD paint both consume this same placement.
struct FColdSteelHUDLayout
{
    float CornerWidth,CornerHeight,ClockLeft,EventLeft,CornerTop;
    float CompassTop,CompassWidth,TargetTop;
    explicit FColdSteelHUDLayout(float Width)
    {
        const float Gap=ColdSteelUI::HUDGap;
        CornerWidth=FMath::Min(ColdSteelUI::HUDCornerWidth,FMath::Max(1.f,(Width-3*Gap)*.5f));
        CornerHeight=ColdSteelUI::HUDCornerHeight;
        ClockLeft=Width-Gap-CornerWidth;
        EventLeft=ClockLeft-Gap-CornerWidth;
        CornerTop=Gap;
        const float CenterSpace=2*(EventLeft-Gap-Width*.5f);
        const bool SeparateRow=CenterSpace<360.f;
        CompassTop=SeparateRow?CornerTop+CornerHeight+32.f:Gap;
        CompassWidth=FMath::Min(640.f,SeparateRow?FMath::Max(1.f,Width-2*Gap):CenterSpace);
        TargetTop=CompassTop+94.f;
    }
};
