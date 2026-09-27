#pragma once

#include "CoreMinimal.h"

/** Infrastructure and explosion-source constants. Visual response defaults now live in
 * GrassDeformSettings (shared by runtime and asset authoring). Each stamp/recenter has two
 * draws for the mask/time pair; recovery has no periodic draw. Legacy constants below are
 * retained for old diagnostics only and do not drive v12 hold/recovery or body strength.
 */
namespace GrassDeformTuning
{
    // ---------------------------------------------------------------------------------------
    // Render target window
    // ---------------------------------------------------------------------------------------

    /** World window covered by one RT edge, in cm. 48 m at 1024 texels is about 4.7 cm/texel. */
    constexpr float WindowSizeCm = 4800.f;

    /** Approximate snap grid; runtime quantizes to whole RT texels (398.4375 cm at 1024)
     *  so recenter never repeatedly filters and blurs the persistent trail. */
    constexpr float SnapGridCm = 400.f;

    /** Supported RT sizes. r.GrassDeform.RTSize outside this set is clamped to the nearest entry. */
    constexpr int32 DefaultRTSize = 1024;
    constexpr int32 MinRTSize = 512;
    constexpr int32 MaxRTSize = 2048;

    /** Fallback world window when the MPC vector parameter is read back (cm). Kept in sync with
     *  WindowSizeCm so the materials get the same number the CPU uses. */
    constexpr float FallsBackWindowSizeCm = WindowSizeCm;

    // ---------------------------------------------------------------------------------------
    // Channel contract (RGBA16F)
    //   R = retained peak flatten 0..1 (evaluate using the paired R32F contact time)
    //   G/B = 0.5 + 0.5 * flatten * bend direction XY (premultiplied for filtering)
    //   A = unused (opaque emissive writes RGB). The latest impulse travels in the MPC.
    // ---------------------------------------------------------------------------------------

    /** Timestamp written for a persistent-only stamp. Any value > 0 would start a wavefront,
     *  so the fade / stamp pair must treat exactly 0 as "none". */
    constexpr float NoImpulseTimestamp = 0.f;

    // ---------------------------------------------------------------------------------------
    // Fade / regrowth
    // ---------------------------------------------------------------------------------------

    /** Seconds for a fully flattened texel to return to zero. Exposed to materials through the
     *  MPC RegrowthSeconds parameter so the shader fades the wavefront on the same clock. */
    constexpr float RegrowthSeconds = 2.4f; // Legacy diagnostics only; use GrassDeformSettings at runtime.

    /** Age past RegrowthSeconds after which the fade pass zeroes channel A outright. */
    constexpr float ImpulseExpirySeconds = 30.f;

    /** Fade frequency clamp for r.GrassDeform.FadeHz. Below 1 Hz the regrowth reads as stepping;
     *  above 12 Hz the 1024^2 pass stops being free for no visible gain. */
    constexpr float MinFadeHz = 1.f;
    constexpr float MaxFadeHz = 12.f;

    /** A stamp always runs the fade pass on the next update anyway, so the fade only needs its
     *  own timer while flattened texels are still regrowing. */
    constexpr float FadeIdleSeconds = 0.25f;

    // ---------------------------------------------------------------------------------------
    // Stamps
    // ---------------------------------------------------------------------------------------

    /** Hard clamp on any incoming radius (cm). A radius larger than the window would splat the
     *  whole RT and read as a global colour change rather than a local interaction. */
    constexpr float MaxStampRadiusCm = 2000.f;
    constexpr float MinStampRadiusCm = 2.f;

    /** Clamp on stamp strength. R is a 0..1 flatten mask; >1 would clip into the bend encoding. */
    constexpr float MaxStampStrength = 1.f;

    /** Includes the displaced blades beside the capsule, not only the boot soles. */
    constexpr float TrampleRadiusScale = 1.8f;
    constexpr float TrampleMinRadiusCm = 80.f; // Legacy; runtime uses GrassDeformSettings.

    /** Trample strength range, scaled by how fast the player is actually moving. */
    constexpr float TrampleMinStrength = 0.75f;
    constexpr float TrampleMaxStrength = 1.0f;

    /** Reference speed (cm/s) at which a trample stamp reaches TrampleMaxStrength.
     *  450 cm/s is a brisk walk in this project's movement tuning. */
    constexpr float TrampleFullStrengthSpeed = 450.f;

    /** Wave front speed (cm/s) used when a caller does not supply one. */
    constexpr float DefaultWaveSpeed = 1800.f;

    // ---------------------------------------------------------------------------------------
    // Explosion impulses (M2, plan section 6)
    //
    // Four C++ explosion sites feed the system, and each one owns a different notion of
    // "radius": the fireball uses the single radius its damage shares, the meteor uses the
    // impact radius while its burning field keeps a separate aura radius, the witch bottle
    // uses the poison pool radius, and the crater uses the radius it already scaled up from
    // the effect radius. The coefficients below normalise all four onto the same baseline -
    // "the radius of the effect that actually happens in the world" - instead of each call
    // site inventing its own multiplier inline.
    //
    // The WaveSpeed values are per source on purpose. The wave swept into channel A is read
    // from a single global MPC value (plan section 10.5), so a slow, heavy impact and a light
    // one cannot be distinguished spatially - but they can still read differently in time
    // when only one wave is alive at once, which is the single-explosion case M2 ships.
    // ---------------------------------------------------------------------------------------

    /** Fireball (Skills/FPSFireballProjectile.cpp): the cast radius is the exact extent of
     *  both the damage sphere and the shockwave ring, so the grass reads best just inside it. */
    constexpr float FireballRadiusMultiplier = 1.0f;

    /** Meteor (Skills/FPSMeteorStrike.cpp): the impact radius under-reports the spray that the
     *  1.5x-scaled impact FX and the 12 flying fragments actually cover, so push it outward.
     *  Upper end of the 0.8..1.2 band in the plan. */
    constexpr float MeteorRadiusMultiplier = 1.2f;

    /** Witch bottle (Monsters/WitchProjectile.cpp): the venom pool reaches only as far as its
     *  sloped footprint (PoolBoundary), and the landed bottle is a heavy glass impact rather
     *  than a blast, so a slightly tighter, softer stamp is correct. Lower end of the band. */
    constexpr float WitchRadiusMultiplier = 0.8f;

    /** Crater (WorldGeneration/TerrainDestruction.cpp): this site is handed the crater radius
     *  itself (already the effect radius times fps.Hills.CraterRadiusScale), so the coefficient
     *  stays at 1 and the grass footprint tracks the bowl exactly. Change this one only if a
     *  crater should scorch the grass wider or narrower than the hole it digs. */
    constexpr float CraterRadiusMultiplier = 1.0f;

    /** Post-impact flatten strength per source, 0..1 on channel R. A fireball and a meteor dig
     *  a full flatten into the turf; a bottle only knocks the grass down and lets it come back
     *  faster, so it does not read as a scorch mark next to a real explosion. */
    constexpr float FireballImpulseStrength = 1.f;
    constexpr float MeteorImpulseStrength = 1.f;
    constexpr float WitchImpulseStrength = 0.55f;
    constexpr float CraterImpulseStrength = 1.f;

    /** Wave front speed per source (cm/s), measured against the same radius it was stamped
     *  with, so the ring needs roughly Radius / WaveSpeed seconds to leave the flatten zone.
     *  The meteor is the fastest and loudest, the bottle the softest. */
    constexpr float FireballImpulseWaveSpeed = 1800.f;
    constexpr float MeteorImpulseWaveSpeed = 2600.f;
    constexpr float WitchImpulseWaveSpeed = 900.f;
    constexpr float CraterImpulseWaveSpeed = 1500.f;

    // ---------------------------------------------------------------------------------------
    // Player trample source
    // ---------------------------------------------------------------------------------------

    /** The trample source runs at 10 Hz (plan section 3.1). The accumulator below only advances
     *  on those ticks, so the cost is independent of frame rate. */
    constexpr float TrampleCheckHz = 10.f;

    /** Horizontal distance the capsule-bottom projection must accumulate before a stamp. */
    constexpr float TrampleMinTravelCm = 20.f;

    /** Discontinuous moves are not swept into the terrain mask. */
    constexpr float TrampleMaxSegmentCm = 300.f;

    /** Below this speed the player is standing still; no stamp, and the accumulator keeps its
     *  value so a slow shuffle still eventually leaves a mark. */
    constexpr float TrampleMinSpeed = 60.f;

    /** Capsule-bottom projection offset. The player pawn is a capsule whose origin sits at its
     *  centre, so the ground contact point is origin - (half height - radius). The half height is
     *  queried from the character; this is only the extra probe below the contact point that
     *  keeps the stamp on the terrain when the sole floats by a centimetre. No trace is used. */
    constexpr float TrampleGroundProbeCm = 6.f;

    /** Slack for the "did the player actually move" test, in cm, to reject capsule jitter. */
    constexpr float TrampleDeadZoneCm = 1.f;

    // ---------------------------------------------------------------------------------------
    // Scalability gate (M4)
    // ---------------------------------------------------------------------------------------

    /** sg.FoliageQuality level that forces the deform off. Level 0 is "Low" in the engine's
     *  scalability ladder (valid levels are 0..4) and is the only level at which foliage is meant
     *  to disappear, so the deform follows it. Levels 1 and above leave r.GrassDeform in charge. */
    constexpr int32 DisabledFoliageQualityLevel = 0;

    // ---------------------------------------------------------------------------------------
    // Diagnostics
    // ---------------------------------------------------------------------------------------

    /** Log category used by the subsystem (declared in the .cpp). */
    constexpr int32 MaxMissingAssetWarnings = 1;

    /** DumpRT writes to Saved/GrassDeform/. */
    const TCHAR* const DumpDirectory = TEXT("GrassDeform");
    const TCHAR* const DumpFilePrefix = TEXT("GrassDeformRT");
}
