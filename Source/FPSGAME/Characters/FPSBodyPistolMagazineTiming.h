#pragma once

// Native M1911-family reload source seconds (ordinary and empty share the
// insertion keys). Use the owning hand's source clock, never clip percentages.
namespace FPSBodyPistolMagazineTiming
{
inline constexpr float Withdraw=.25f,Release=.3167f,Appear=.78f,Seat=1.05f;
// Begin the free hand's approach before the magazine appears. This preparation
// does not alter release/appearance/seating or the gameplay reload clock.
inline constexpr float HandArrive=.55f,HandRelease=1.20f;
}
