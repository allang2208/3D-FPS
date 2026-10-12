#pragma once
#include "SpellbookAuthoredStrike.h"
#include "../Staff/StaffQuickCombatMotion.h"

// The unarmed jab uses StaffQuickCombatMotion. Keep the authored book grip
// and trajectory, and map each phase onto that same live action clock.
namespace SpellbookQuickCombatMotion
{
inline constexpr float Length=StaffQuickCombatMotion::Length;
inline constexpr float PlaybackTimes[]={0.f,StaffQuickCombatMotion::Release,StaffQuickCombatMotion::Cock,
    StaffQuickCombatMotion::Contact,StaffQuickCombatMotion::Follow,StaffQuickCombatMotion::Recover,Length};
inline constexpr float SourceTimes[]={0.f,SpellbookAuthoredStrike::Release,SpellbookAuthoredStrike::Cock,
    SpellbookAuthoredStrike::Contact,SpellbookAuthoredStrike::Follow,SpellbookAuthoredStrike::Recover,SpellbookAuthoredStrike::Length};
inline float SourceTime(float Age)
{
    Age=FMath::Clamp(Age,0.f,Length);
    int32 Phase=0;while(Phase<5&&Age>=PlaybackTimes[Phase+1])++Phase;
    const float Alpha=(Age-PlaybackTimes[Phase])/(PlaybackTimes[Phase+1]-PlaybackTimes[Phase]);
    return FMath::Lerp(SourceTimes[Phase],SourceTimes[Phase+1],Alpha);
}
inline float SourceProgress(float Progress)
{
    return SourceTime(Progress*Length)/SpellbookAuthoredStrike::Length;
}
}
