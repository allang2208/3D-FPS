#pragma once
#include "CoreMinimal.h"

// Sprint overhead chop: the accepted heavy attack's raise and slam retimed, so
// no pose is re-solved.  See Docs/Weapons/runesword-overhead-20260916.md and
// SourceAssets/RuneSword20260913/InspectGripArcV46/author_overhead_v49.py.
namespace RuneSwordOverheadRhythm
{
    // V52 clock (2.60 s): the blade enters the visible sweep at about 1.15 s and
    // reaches full reach pointing down-forward at 1.30 s, carrying past at 1.40 s.
    // The window below is that sweep only, so every sampled hit frame has the
    // blade in front of the camera.
    inline constexpr float ContactStart=1.22f;
    inline constexpr float ContactEnd=1.40f;
    // Dash-only carry-to-strike transition, played before the shared hit window.
    inline constexpr float DashWindupSeconds=.25f;
    // The slam is the heavy release slowed 2x; sample it at the release's own
    // density rather than the slash's 240 Hz.
    inline constexpr float SampleRate=480.f;
}
