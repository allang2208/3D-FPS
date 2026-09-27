#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "GrassDeformSettings.generated.h"

/** Shared runtime/authoring defaults. Override in [/Script/FPSGAME.GrassDeformSettings]
 * in DefaultGame.ini. Loaded once per world; no config reads on the frame path. */
UCLASS(Config=Game, DefaultConfig)
class FPSGAME_API UGrassDeformSettings : public UObject
{
    GENERATED_BODY()
public:
    UGrassDeformSettings();

    UPROPERTY(EditAnywhere, Config, Category="Response") float BodyRadiusCm = 80.f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float CoreFraction = 0.68f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float BodyStrength = 1.f;
    // v13: target stem inclination from instance up, not an extra rotation of a tilted blade.
    UPROPERTY(EditAnywhere, Config, Category="Response") float BendAngleDegrees = 74.f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float PressSeconds = 0.15f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float HoldSeconds = 0.6f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float RecoverSeconds = 1.8f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float FlatWindScale = 0.03f;
    UPROPERTY(EditAnywhere, Config, Category="Response") float ForwardBias = 0.97f;
    UPROPERTY(EditAnywhere, Config, Category="Footstep") float FootstepRadiusCm = 26.f;
    UPROPERTY(EditAnywhere, Config, Category="Footstep") float FootstepStrength = 0.85f;
    UPROPERTY(EditAnywhere, Config, Category="Footstep") float FootstepCoreFraction = 0.35f;
};
