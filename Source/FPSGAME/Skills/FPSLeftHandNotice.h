#pragma once

#include "CoreMinimal.h"

/**
 * Left-hand spells reject a request outright when the hand is held by equipment
 * that only a loadout change can release - currently the off-hand pistol of an
 * akimbo pair. Queueing there would silently fire the spell once akimbo ends, so
 * the quick slot blinks "left hand occupied" in place for a fixed window and the
 * request is dropped instead.
 */
namespace FPSLeftHandNotice
{
    constexpr float Duration=3.f;   // Total time the prompt stays on the slot.
    constexpr float FadeOut=.35f;   // Final opacity ramp.
    constexpr float HopPeriod=.4f;  // One blink plus one hop.
    constexpr float HopPixels=5.f;  // Peak upward travel of the hop.
}

/** Transient left-hand notice, driven from world seconds. */
struct FFPSLeftHandNotice
{
    void Show(float Now) { Until=Now+FPSLeftHandNotice::Duration; }
    void Clear() { Until=-1.f; }
    bool Active(float Now) const { return Now<Until; }
    float Elapsed(float Now) const { return FPSLeftHandNotice::Duration-(Until-Now); }
    /** Blink envelope: 1 at each hop start, .35 at its midpoint, 0 after the window. */
    float Alpha(float Now) const
    {
        if(!Active(Now))return 0.f;
        const float Pulse=.5f+.5f*FMath::Cos(2.f*PI*HopPhase(Now));
        return FMath::Lerp(.35f,1.f,Pulse)*FMath::Clamp((Until-Now)/FPSLeftHandNotice::FadeOut,0.f,1.f);
    }
    /** Upward travel in slate pixels for the current hop, so the prompt reads as jumping. */
    float Rise(float Now) const
    {
        if(!Active(Now))return 0.f;
        return FPSLeftHandNotice::HopPixels*FMath::Sin(PI*HopPhase(Now));
    }
private:
    float HopPhase(float Now) const
    { return FMath::Fmod(Elapsed(Now),FPSLeftHandNotice::HopPeriod)/FPSLeftHandNotice::HopPeriod; }
    float Until=-1.f;
};
