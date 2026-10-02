#pragma once
#include "CoreMinimal.h"

// Native V7 left jab. SourceAssets/StaffQuickCombat20261001/author_punch.py.
namespace StaffQuickCombatMotion
{
    constexpr float Release=.055f,Cock=.115f;
    constexpr float PunchRate=1.5f;
    constexpr float Contact=Cock+(.20f-Cock)/PunchRate;
    constexpr float TimeSaved=.20f-Contact;
    constexpr float Follow=.28f-TimeSaved,Recover=.32f-TimeSaved;
    constexpr float Length=.58f-TimeSaved;
    constexpr float QueryRadiusCM=14.f;
}
