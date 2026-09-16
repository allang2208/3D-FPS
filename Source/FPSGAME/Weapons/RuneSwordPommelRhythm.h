#pragma once
#include "CoreMinimal.h"

// Fourth normal attack: the counterweight behind the guard (柄尾配重) is driven
// forward. Source seconds match
// SourceAssets/MeleePommelAttack20260916/pommel_motion.py; attack speed scales
// the animation, contact window, the small step and the camera together. The
// strike gets no reach bonus and only a 24 cm step, because the counterweight is
// one pommel-length past the hands: a close-range finisher, not a second thrust.
namespace RuneSwordPommelRhythm
{
    // Not a uniform playback rate: turnover, draw-back, the raised-arm charge beat
    // and the aim hold take 0.84 s, the strike spends 0.26 m of counterweight travel
    // in 0.08 s, then the weight draws back over 0.62 s.
    inline constexpr float TurnEnd=.40f, DrawEnd=.58f, RaiseEnd=.72f;
    inline constexpr float ContactStart=.84f, ExtensionEnd=.92f, ContactEnd=.92f;
    inline constexpr float ArrestEnd=.98f, ReturnCorner=1.30f, AttackEnd=1.60f;
    // The strike steps in only far enough to put its short reach on the target:
    // 24 cm against the thrust's metre, on the same ground-swept path.
    inline constexpr float LungeStart=.82f, LungeEnd=.98f, LungeDistance=24.f;
    inline float LungeAlpha(float Time) { return FMath::SmoothStep(LungeStart,LungeEnd,Time); }
    // Blunt head inside a narrow forward corridor; one target per swing.
    inline constexpr float HeadRadius=6.f, CorridorRadius=20.f;
    // Blade_Base sits this far in front of the guard; the counterweight face this
    // far behind it on the hilt axis (rune sword mesh; the modular frost sword
    // reads its own pommel depth from the installed assembly).
    inline constexpr float BladeBaseCM=2.4f, CounterweightCM=27.f;
    inline constexpr float SampleRate=480.f;
}
