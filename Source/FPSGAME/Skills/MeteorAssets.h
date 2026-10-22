#pragma once

#include "CoreMinimal.h"

// One contract for background preparation, cast readiness and remote strike
// presentation. A visual revision must not leave a second readiness list behind.
namespace MeteorSpellAssets
{
    inline constexpr const TCHAR* Rock = TEXT("/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1/SM_MeteorClosedRock.SM_MeteorClosedRock");
    inline constexpr const TCHAR* RockMaterial = TEXT("/Game/Skills/FireMagic20260921/MeteorClosedVolumeV1/MI_MeteorClosedRock.MI_MeteorClosedRock");
    inline constexpr const TCHAR* Mantle = TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalMantle.NS_MeteorNaturalMantle");
    inline constexpr const TCHAR* Trail = TEXT("/Game/Skills/FireMagic20260921/RealisticV5/NS_MeteorNaturalWake.NS_MeteorNaturalWake");
    inline constexpr const TCHAR* GroundFire = TEXT("/Game/Skills/FireMagic20260921/MeteorImpactLowFireV4/NS_MeteorGroundVolume.NS_MeteorGroundVolume");
    inline constexpr const TCHAR* Impact = TEXT("/Game/Skills/FireMagic20260921/MeteorImpactWeightV5/NS_MeteorImpact.NS_MeteorImpact");
    inline constexpr const TCHAR* Scorch = TEXT("/Game/Skills/FireMagic20260921/MeteorImpactWeightV5/M_MeteorScorch.M_MeteorScorch");
    inline constexpr const TCHAR* LandSound = TEXT("/Game/Skills/FireMagic20260921/MeteorImpactWeightV5/S_MeteorImpact.S_MeteorImpact");
    inline constexpr const TCHAR* BurnSound = TEXT("/Game/Skills/FireMagic20260921/S_MeteorBurn.S_MeteorBurn");
    inline constexpr const TCHAR* HeatMaterial = TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave");
    inline constexpr const TCHAR* CastSound = TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast");
    inline constexpr const TCHAR* Preview = TEXT("/Game/Skills/FireMagic20260921/PreviewSurface20261022/M_MeteorAimPreview.M_MeteorAimPreview");
    inline constexpr const TCHAR* Visuals[] = {
        Rock, RockMaterial, Mantle, Trail, GroundFire, Impact, LandSound, BurnSound, HeatMaterial, Scorch
    };
}
