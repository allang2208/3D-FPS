#pragma once
#include "FPSPlayerBodyTypes.h"
#include "../Items/PotionEquipmentHandoff.h"

namespace FPSBodyConsumeMotion
{
inline void Advance(FFPSBodyState& State,float SampleAge)
{
    if(State.Action!=EFPSBodyAction::Consume||!State.ConsumeHands||
        State.ActionProgressRate<=0.f||State.ActionDuration<=UE_SMALL_NUMBER)return;
    const float Rate=State.ActionProgressRate*State.ActionDuration;
    const float SourceAge=(State.PresentationSampledAt-State.ActionStartedAt+SampleAge)*Rate;
    // Progress was clamped to zero during entry. Advancing that zero linearly
    // would start drinking while the hand is still lowering. Use the origin.
    if(State.bHasActionProgress)State.ActionProgress=FMath::Clamp(SourceAge/State.ActionDuration,0.f,1.f);
    // The first zero-weight entry sample can wait for the next snapshot. Bow
    // support transfers and empty offhands must not acquire a stow of their own.
    if(State.ConsumeStowWeight<=0.f&&!State.bConsumeWeaponsHidden)return;
    State.ConsumeStowWeight=PotionEquipmentHandoff::Weight(SourceAge,State.ActionDuration);
}
}
