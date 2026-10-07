#pragma once

// Azure Dragon claw reach (V10.11). While the enchantment is active, slash-type swings (slashes, heavy
// and overhead strokes, uppercut) reach from the player out to the claws' farthest talon point, swept
// along the sword's own path. Thrust, pommel, dash, whirlwind and quick combat keep the x1.5 multiplier.
// The layout values are shared with the claw presentation in RuneSwordAzureDragon.cpp.
namespace AzureDragonReach
{
    inline constexpr float ClawWorldScale=5.f;       // x the Fab claw mesh
    inline constexpr float ClawStationMaxCM=1200.f;  // farthest claw palm station from the eye
    inline constexpr float TalonBeyondPalm=72.f;     // middle talon tip beyond the palm centre (mesh x 80 - 8)
    inline constexpr float ClawReachCM=ClawStationMaxCM+TalonBeyondPalm*ClawWorldScale; // 1560 cm
    inline constexpr float TraceRadiusCM=45.f;       // swept line radius (the claws are metres wide)
    inline constexpr float MinPitch=-3.f,MaxPitch=10.f; // keep the long line off the floor / out of the sky
}
