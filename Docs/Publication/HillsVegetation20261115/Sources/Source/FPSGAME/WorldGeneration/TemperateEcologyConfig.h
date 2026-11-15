#pragma once

#include "CoreMinimal.h"
#include "TemperateEcologyConfig.generated.h"


// Density scales the existing seeded habitat probability; it never changes
// candidate coordinates, salts, enumeration spacing or harvest identity.
USTRUCT()
struct FTemperateEcologyLayer
{
    GENERATED_BODY()
    UPROPERTY() double Density = 1.;
    UPROPERTY() double MinNormalZ = 0.;
    UPROPERTY() double FullNormalZ = 1.;

    double SlopeWeight(double NormalZ) const
    {
        if (NormalZ < MinNormalZ) return 0.0;
        return FullNormalZ <= MinNormalZ ? 1.0 : FMath::SmoothStep(MinNormalZ, FullNormalZ, NormalZ);
    }
};

USTRUCT()
struct FTemperateEcologyTransition
{
    GENERATED_BODY()
    UPROPERTY() double Start = 0.;
    UPROPERTY() double End = 1.;
    double Weight(double Value) const { return FMath::SmoothStep(Start, End, Value); }
};

USTRUCT()
struct FTemperateRainforestRegion
{
    GENERATED_BODY()
    UPROPERTY() double Strength = 1.0;
    UPROPERTY() double AreaFraction = .30;
    UPROPERTY() double CenterX = -12000.0;
    UPROPERTY() double NorthOfValleyCm = 10000.0;
    UPROPERTY() double RadiusXCm = 11000.0;
    UPROPERTY() double RadiusYCm = 8500.0;
    UPROPERTY() double EdgeBlend = .35;
    UPROPERTY() double Canopy = .92;
    UPROPERTY() double Moisture = .85;
    UPROPERTY() double ClearingScaleCm = 2400.0;
    UPROPERTY() double TreeDensityMultiplier = 2.2;
    UPROPERTY() double TreeScaleMultiplier = 1.12;
    UPROPERTY() double SaplingDensityMultiplier = 2.0;
    UPROPERTY() double ShrubDensityMultiplier = 1.65;
    UPROPERTY() double FernDensityMultiplier = 1.60;
    UPROPERTY() double GrassDensityMultiplier = 1.95;
    UPROPERTY() double FlowerDensityMultiplier = 3.0;
    UPROPERTY() double GrassShadeSuppression = .20;
};

// Plain immutable values: terrain workers and PCG use the same project profile.
// Model references and candidate spacing remain in the existing asset/layout.
USTRUCT()
struct FTemperateEcologyProfile
{
    GENERATED_BODY()
    UPROPERTY() double PoplarShareMin = .10;
    UPROPERTY() double PoplarShareMax = .20;
    UPROPERTY() FTemperateEcologyLayer Trees{1.0, .87, .87};
    UPROPERTY() FTemperateEcologyLayer Shrubs{1.0, .83, .95};
    UPROPERTY() FTemperateEcologyLayer Saplings{1.0, .90, .97};
    UPROPERTY() FTemperateEcologyLayer Hazel{.45, .90, .97};
    UPROPERTY() FTemperateEcologyLayer Ferns{.88, .86, .97};
    UPROPERTY() FTemperateEcologyLayer Grass{.94, .83, .93};
    UPROPERTY() FTemperateEcologyLayer GrassAccents{.50, .83, .93};
    UPROPERTY() FTemperateEcologyLayer MeadowFlowers{.40, .83, .93};
    UPROPERTY() FTemperateEcologyLayer RiverGroundCover{.96, .78, .90};
    UPROPERTY() FTemperateEcologyLayer RiverReeds{.95, .86, .98};
    UPROPERTY() FTemperateEcologyLayer RiverGrass{.95, .78, .90};
    UPROPERTY() FTemperateEcologyLayer RiverUnderstory{.95, .78, .90};
    UPROPERTY() FTemperateEcologyLayer RiverShrubs{.95, .84, .84};

    UPROPERTY() FTemperateEcologyTransition Woodland{.18, .78};
    UPROPERTY() FTemperateEcologyTransition Gaps{.60, .88};
    UPROPERTY() double GapScaleCm = 2600.0;
    UPROPERTY() double GapStrength = .72;
    UPROPERTY() FTemperateEcologyTransition EdgeEnter{.06, .40};
    UPROPERTY() FTemperateEcologyTransition EdgeLeave{.60, .93};
    UPROPERTY() FTemperateEcologyTransition Shade{.30, .82};
    UPROPERTY() FTemperateEcologyTransition GrassShade{.18, .83};
    UPROPERTY() double GrassShadeSuppression = .86;
    UPROPERTY() double AccentShadeSuppression = .91;
    UPROPERTY() double FlowerShadeSuppression = .99;
    UPROPERTY() double MoistureScaleCm = 10500.0;
    UPROPERTY() double UnderstoryPatchScaleCm = 1450.0;
    UPROPERTY() double CohortScaleCm = 2200.0;
    UPROPERTY() double UplandMeadowStrength = 1.0;
    UPROPERTY() double UplandStoneStrength = 1.0;
    UPROPERTY() double UplandShelterStrength = 1.0;
    UPROPERTY() double NurseLogDensity = .85;
    UPROPERTY() double EdgeDebrisStrength = .65;
    UPROPERTY() FTemperateRainforestRegion Rainforest;
};

// One immutable, initial-only snapshot per world. Never overwrite process globals:
// multiple worlds (including a listen host and client PIE) can coexist.
USTRUCT()
struct FTemperateEcologySnapshot
{
    GENERATED_BODY()
    UPROPERTY() bool Ready = false;
    UPROPERTY() FTemperateEcologyProfile Profile;
};

namespace TemperateEcology
{
using FLayer = FTemperateEcologyLayer;
using FTransition = FTemperateEcologyTransition;
using FRainforestRegion = FTemperateRainforestRegion;
using FProfile = FTemperateEcologyProfile;
// Local defaults are read only by authority or offline authoring tools.
const FProfile& Get();
}
