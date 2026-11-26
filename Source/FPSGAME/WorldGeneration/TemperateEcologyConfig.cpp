#include "TemperateEcologyConfig.h"
#include "Misc/ConfigCacheIni.h"

namespace TemperateEcology
{
namespace
{
constexpr const TCHAR* Section = TEXT("TemperateHills.Ecology");

void Read(const TCHAR* Key, double& Value, double Min, double Max)
{
    double Configured = Value;
    if (GConfig->GetDouble(Section, Key, Configured, GGameIni) && FMath::IsFinite(Configured))
        Value = FMath::Clamp(Configured, Min, Max);
}

void ReadLayer(const TCHAR* Prefix, FLayer& Layer)
{
    Read(*(FString(Prefix) + TEXT("Density")), Layer.Density, 0.0, 2.0);
    Read(*(FString(Prefix) + TEXT("MinNormalZ")), Layer.MinNormalZ, 0.0, 1.0);
    Read(*(FString(Prefix) + TEXT("FullNormalZ")), Layer.FullNormalZ, Layer.MinNormalZ, 1.0);
    Layer.FullNormalZ = FMath::Max(Layer.MinNormalZ, Layer.FullNormalZ);
}

void ReadTransition(const TCHAR* Prefix, FTransition& Transition)
{
    Read(*(FString(Prefix) + TEXT("Start")), Transition.Start, 0.0, .9999);
    Read(*(FString(Prefix) + TEXT("End")), Transition.End, Transition.Start + .0001, 1.0);
    Transition.End = FMath::Max(Transition.Start + .0001, Transition.End);
}

FProfile Load()
{
    FProfile P;
    // The owning world primes this on the game thread before any terrain jobs.
    check(IsInGameThread());
    if (!GConfig) return P;
    Read(TEXT("PoplarShareMin"), P.PoplarShareMin, 0.0, 1.0);
    Read(TEXT("PoplarShareMax"), P.PoplarShareMax, P.PoplarShareMin, 1.0);
    P.PoplarShareMax = FMath::Max(P.PoplarShareMin, P.PoplarShareMax);
    ReadLayer(TEXT("Trees"), P.Trees);
    ReadLayer(TEXT("Shrubs"), P.Shrubs);
    ReadLayer(TEXT("Saplings"), P.Saplings);
    ReadLayer(TEXT("Hazel"), P.Hazel);
    ReadLayer(TEXT("Ferns"), P.Ferns);
    ReadLayer(TEXT("Grass"), P.Grass);
    ReadLayer(TEXT("GrassAccents"), P.GrassAccents);
    ReadLayer(TEXT("MeadowFlowers"), P.MeadowFlowers);
    ReadLayer(TEXT("RiverGroundCover"), P.RiverGroundCover);
    ReadLayer(TEXT("RiverReeds"), P.RiverReeds);
    ReadLayer(TEXT("RiverGrass"), P.RiverGrass);
    ReadLayer(TEXT("RiverUnderstory"), P.RiverUnderstory);
    ReadLayer(TEXT("RiverShrubs"), P.RiverShrubs);
    ReadTransition(TEXT("Woodland"), P.Woodland);
    ReadTransition(TEXT("Gaps"), P.Gaps);
    ReadTransition(TEXT("EdgeEnter"), P.EdgeEnter);
    ReadTransition(TEXT("EdgeLeave"), P.EdgeLeave);
    ReadTransition(TEXT("Shade"), P.Shade);
    ReadTransition(TEXT("GrassShade"), P.GrassShade);
    Read(TEXT("GapScaleCm"), P.GapScaleCm, 100.0, 100000.0);
    Read(TEXT("GapStrength"), P.GapStrength, 0.0, 1.0);
    Read(TEXT("GrassShadeSuppression"), P.GrassShadeSuppression, 0.0, 1.0);
    Read(TEXT("AccentShadeSuppression"), P.AccentShadeSuppression, 0.0, 1.0);
    Read(TEXT("FlowerShadeSuppression"), P.FlowerShadeSuppression, 0.0, 1.0);
    Read(TEXT("MoistureScaleCm"), P.MoistureScaleCm, 100.0, 100000.0);
    Read(TEXT("UnderstoryPatchScaleCm"), P.UnderstoryPatchScaleCm, 100.0, 100000.0);
    Read(TEXT("CohortScaleCm"), P.CohortScaleCm, 100.0, 100000.0);
    Read(TEXT("UplandMeadowStrength"), P.UplandMeadowStrength, 0.0, 1.0);
    Read(TEXT("UplandStoneStrength"), P.UplandStoneStrength, 0.0, 1.0);
    Read(TEXT("UplandShelterStrength"), P.UplandShelterStrength, 0.0, 1.0);
    Read(TEXT("NurseLogDensity"), P.NurseLogDensity, 0.0, 1.0);
    Read(TEXT("EdgeDebrisStrength"), P.EdgeDebrisStrength, 0.0, 1.0);
    auto& R = P.Rainforest;
    Read(TEXT("RainforestStrength"), R.Strength, 0.0, 1.0);
    Read(TEXT("RainforestAreaFraction"), R.AreaFraction, 0., .50);
    Read(TEXT("RainforestCenterX"), R.CenterX, -50000.0, 50000.0);
    Read(TEXT("RainforestNorthOfValleyCm"), R.NorthOfValleyCm, -40000.0, 40000.0);
    Read(TEXT("RainforestRadiusXCm"), R.RadiusXCm, 1000.0, 20000.0);
    Read(TEXT("RainforestRadiusYCm"), R.RadiusYCm, 1000.0, 20000.0);
    Read(TEXT("RainforestEdgeBlend"), R.EdgeBlend, .10, .80);
    Read(TEXT("RainforestCanopy"), R.Canopy, .50, 1.0);
    Read(TEXT("RainforestMoisture"), R.Moisture, 0.0, 1.0);
    Read(TEXT("RainforestClearingScaleCm"), R.ClearingScaleCm, 1000.0, 6000.0);
    Read(TEXT("RainforestTreeDensityMultiplier"), R.TreeDensityMultiplier, 1.0, 3.0);
    Read(TEXT("RainforestTreeScaleMultiplier"), R.TreeScaleMultiplier, 1.0, 1.25);
    Read(TEXT("RainforestSaplingDensityMultiplier"), R.SaplingDensityMultiplier, 1.0, 3.0);
    Read(TEXT("RainforestShrubDensityMultiplier"), R.ShrubDensityMultiplier, 1.0, 3.0);
    Read(TEXT("RainforestFernDensityMultiplier"), R.FernDensityMultiplier, 1.0, 3.0);
    Read(TEXT("RainforestGrassDensityMultiplier"), R.GrassDensityMultiplier, 1.0, 2.0);
    Read(TEXT("RainforestFlowerDensityMultiplier"), R.FlowerDensityMultiplier, 1.0, 4.0);
    Read(TEXT("RainforestGrassShadeSuppression"), R.GrassShadeSuppression, 0.0, 1.0);
    return P;
}
}

const FProfile& Get()
{
    static const FProfile Profile = Load();
    return Profile;
}
}
