#include "TerrainDestruction.h"

#include "TemperateHillsWorld.h"
#include "GrassDeform/GrassDeformSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

namespace TerrainDestruction
{
    // Crater geometry relative to the effect radius. Sizes are game values, tuned for the
    // 2 m terrain vertex spacing of the hills world.
    static TAutoConsoleVariable<float> CraterRadiusScale(
        TEXT("fps.Hills.CraterRadiusScale"), 1.5f,
        TEXT("Explosion crater radius = effect radius * this."));
    static TAutoConsoleVariable<float> CraterDepthScale(
        TEXT("fps.Hills.CraterDepthScale"), .4f,
        TEXT("Crater depth = crater radius * this."));
    static TAutoConsoleVariable<float> CraterRimScale(
        TEXT("fps.Hills.CraterRimScale"), .12f,
        TEXT("Crater rim height = crater radius * this (raised lip)."));
    static TAutoConsoleVariable<int32> DebugLog(
        TEXT("fps.Hills.CraterDebugLog"), 0,
        TEXT("Log rejected explosion craters (1/0)."));

    bool CarveCrater(const UObject* WorldContext, const FVector& Contact, const FVector& Normal, float EffectRadiusCm)
    {
        if (!WorldContext || EffectRadiusCm <= 0.f || !GEngine) return false;
        UWorld* World = GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull);
        if (!World) return false;
        for (TActorIterator<ATemperateHillsWorld> It(World); It; ++It)
        {
            const double Radius = EffectRadiusCm * CraterRadiusScale.GetValueOnGameThread();
            if (Radius <= 0) return false;
            const double Depth = Radius * CraterDepthScale.GetValueOnGameThread();
            const double Rim = Radius * CraterRimScale.GetValueOnGameThread();
            const bool bApplied = It->ApplyCrater(Contact, Radius, Depth, Rim);
            // Grass within the same footprint as the bowl. ClearCoverForEdit only removes the
            // tufts PCG already instanced inside 1.15x this radius, and nothing regenerates
            // them afterwards (ActivateVegetationLayer runs once at entry), so this stamp adds
            // the bent tufts between the crater rim and the cleared zone instead of duplicating
            // the removal. Radius is the crater radius itself, so the multiplier stays at 1.
            // Call sites reach here once per impact, unlike the bottle, so no double stamp.
            if (UGrassDeformSubsystem* GrassDeform = World->GetSubsystem<UGrassDeformSubsystem>())
                GrassDeform->AddImpulse(Contact, float(Radius) * GrassDeformTuning::CraterRadiusMultiplier,
                    GrassDeformTuning::CraterImpulseStrength, GrassDeformTuning::CraterImpulseWaveSpeed);
            if (!bApplied && DebugLog.GetValueOnGameThread() != 0)
                UE_LOG(LogTemp, Display, TEXT("HILLS_CRATER rejected x=%.1f y=%.1f radius=%.1f (depth limit)"),
                    Contact.X, Contact.Y, Radius);
            return bApplied;
        }
        return false;
    }
}
