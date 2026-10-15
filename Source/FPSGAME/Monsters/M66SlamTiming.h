#pragma once
namespace M66SlamTiming
{
    // V16 baked source-time curve: fast 0.15 s downstroke, then planted hold.
    inline constexpr float StrikeStart=1.35f;
    inline constexpr float ContactStart=1.42f;
    inline constexpr float Impact=1.5f;
    inline constexpr float ContactEnd=Impact;
    inline constexpr float GroundHoldSeconds=.5f;
    inline constexpr float GroundHoldEnd=Impact+GroundHoldSeconds;
    inline constexpr float End=232.f/60.f;
    inline constexpr float RestAfterEnd=1.f;
}
