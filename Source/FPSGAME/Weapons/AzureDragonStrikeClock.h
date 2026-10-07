#pragma once
#include <algorithm>

// Source-animation seconds, never a second wall-clock playback timer.
// Phase runs 0..1 lead (draw back to the windup), 1..2 sweep, 2..3 recovery.
// The claw gesture is authored on the same thirds (frames 0/12/24/36, talon snap at 18).
namespace AzureDragonStrikeClock
{
// V10.5 readable horizontal sweep (2026-10-06): the sweep lasts 0.6 s of the sword's attack time and
// crosses the target at the contact-window midpoint; the lead uses the sword's windup, the recovery
// its follow-through.
inline constexpr float SweepLead=.45f,SweepBefore=.27f,SweepAfter=.33f,SweepTail=.35f;
inline constexpr float SweepImpact=SweepBefore/(SweepBefore+SweepAfter);
// V10.12: attacks that enter late (heavy release at contact, finishers, skipped windups) keep at least
// this much sweep before the crossing, which then lands slightly after the contact midpoint, instead
// of the claw jumping part-way into its sweep.
inline constexpr float SweepMinBefore=.12f;
struct Pose { float Sweep=0.f,Grab=0.f,Reveal=0.f,Phase=0.f,Impact=SweepImpact; bool Visible=false; };
inline float Unit(float V){return std::clamp(V,0.f,1.f);}
inline float Ease(float V){V=Unit(V);return V*V*(3.f-2.f*V);}
// Entry = source time at which this attack began (unknown: leave the default).
inline Pose Sweep(float Source,float Start,float End,float Entry=-1.e3f)
{
    Pose P;
    const float Cross=std::max(.5f*(Start+End),Entry+SweepMinBefore);
    const float Before=std::clamp(Cross-Entry,SweepMinBefore,SweepBefore);
    const float S0=Cross-Before,S1=Cross+SweepAfter;
    const float L0=std::max(std::max(0.f,Entry),S0-SweepLead);
    if(Source<L0||Source>=S1+SweepTail)return P;
    P.Visible=true;P.Impact=Before/(Before+SweepAfter);
    if(Source<S0)
    {
        const float U=Unit((Source-L0)/std::max(.001f,S0-L0));
        P.Phase=U;P.Reveal=Ease(U/.35f);
    }
    else if(Source<=S1)
    {
        P.Sweep=Unit((Source-S0)/(S1-S0));
        P.Phase=1.f+P.Sweep;P.Reveal=1.f;
    }
    else
    {
        const float U=Unit((Source-S1)/SweepTail);
        P.Phase=2.f+U;P.Reveal=1.f-Ease((U-.6f)/.4f);
    }
    P.Grab=P.Phase/3.f;
    return P;
}
// Heavy charge: the claw draws back to its windup and holds there until the release sweeps.
inline Pose Windup(float HeldSeconds)
{
    Pose P;P.Visible=true;P.Reveal=1.f;
    P.Phase=std::min(.999f,std::max(0.f,HeldSeconds)/SweepLead);P.Grab=P.Phase/3.f;
    return P;
}
}
