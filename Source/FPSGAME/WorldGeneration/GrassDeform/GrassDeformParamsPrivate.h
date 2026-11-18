#pragma once
#include "CoreMinimal.h"
namespace GrassDeformParams
{
    // Material parameters on the three pass materials. Names must match setup_assets_m1.py, which
    // authors those graphs; keep the two files in sync when either side changes.
    inline const FName CenterUV(TEXT("CenterUV"));
    inline const FName StartUV(TEXT("StartUV"));
    inline const FName IsSweep(TEXT("IsSweep"));
    inline const FName RadiusUV(TEXT("RadiusUV"));
    inline const FName Strength(TEXT("Strength"));

    // Fade pass.
    inline const FName FadeRate(TEXT("FadeRate"));

    // Recenter pass.
    inline const FName ShiftUV(TEXT("ShiftUV"));

    // Deform parameters published on the pack wind collection (see GrassDeformAssets::CollectionPath).
    inline const FName MpcCenter(TEXT("Center"));
    inline const FName MpcWindowSize(TEXT("WindowSize"));
    inline const FName MpcWorldTime(TEXT("WorldTime"));
    inline const FName MpcRegrowthSeconds(TEXT("RegrowthSeconds"));
    inline const FName MpcEnabled(TEXT("bEnabled"));
    // Wavefront speed is consumed by MF_GrassDeform at render time, so it lives in the collection
    // rather than on the stamp material.
    inline const FName MpcWaveSpeed(TEXT("WaveSpeed"));
    // Origin (window UV) of the most recent impulse. MF_GrassDeform measures the expanding ring
    // from this point, so the wave sweeps out from the impact, not from the window centre.
    inline const FName MpcWaveOrigin(TEXT("WaveOrigin"));
    inline const FName MpcWaveStartTime(TEXT("GrassWaveStartTime"));
    inline const FName MpcWaveRadius(TEXT("GrassWaveRadius"));
    inline const FName MpcWaveStrength(TEXT("GrassWaveStrength"));
    // Selects which RT asset is the current read side inside MF_GrassDeform: both assets are wired
    // as texture-parameter defaults, and this scalar (0 = A, 1 = B) picks between them with a
    // uniform branch. Published on every ping-pong flip.
    inline const FName MpcReadIsB(TEXT("ReadIsB"));

    // Source texture of the three pass materials: the read side of the ping-pong pair. All three
    // passes read the previous contents through this one parameter name, so the pass contract is
    // uniform and every pass material samples exactly the texture it does not write.
    inline const FName PassSource(TEXT("Old"));
}
