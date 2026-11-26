#include "VillageChimneySmoke.h"
#include "FluidPresentationSubsystem.h"
#include "../FPSWeatherManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "NiagaraComponent.h"
#include "Scalability.h"

namespace
{
const FName FlueTag(TEXT("VillageShop.FlueSmoke"));
const FName FuelTag(TEXT("VillageShop.HearthFire"));
}

void VillageChimneySmoke::Apply(AActor& Site, bool bLit)
{
    if (Site.GetNetMode() == NM_DedicatedServer) return;
    if (auto* Fluids = Site.GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
    {
        TInlineComponentArray<UNiagaraComponent*> Effects(&Site);
        for (UNiagaraComponent* Effect : Effects)
            if (Effect->ComponentHasTag(FlueTag) || Effect->ComponentHasTag(FuelTag))
                Fluids->SetVillageHearthLit(Effect, bLit);
    }
}

void UFluidPresentationSubsystem::SetVillageHearthLit(UNiagaraComponent* Effect, bool bLit)
{
    const int32 Index = VillageHearths.IndexOfByPredicate(
        [Effect](const FVillageHearth& Hearth) { return Hearth.Effect.Get() == Effect; });
    if (bLit && Index == INDEX_NONE)
    {
        if (Effect->ComponentHasTag(FuelTag))
        {
            Effect->SetEmitterEnable(TEXT("Smoke"), false);
            Effect->SetEmitterEnable(TEXT("Sparks"), true);
        }
        VillageHearths.Add({Effect, true});
    }
    else if (!bLit)
    {
        if (Index != INDEX_NONE) VillageHearths.RemoveAtSwap(Index);
        if (Effect->IsActive()) Effect->DeactivateImmediate();
    }
    Effect->SetVisibility(bLit);
    Effect->SetHiddenInGame(!bLit);
}

void UFluidPresentationSubsystem::UpdateVillageHearths()
{
    if (VillageHearths.IsEmpty()) return;
    const int32 Quality = Scalability::GetQualityLevels().EffectsQuality;
    for (int32 Index = VillageHearths.Num() - 1; Index >= 0; --Index)
    {
        auto& Hearth = VillageHearths[Index];
        UNiagaraComponent* Effect = Hearth.Effect.Get();
        if (!Effect)
        {
            VillageHearths.RemoveAtSwap(Index);
            continue;
        }
        const bool bFlue = Effect->ComponentHasTag(FlueTag);
        const float Reach = (bFlue ? 6500.f : 2450.f) + (Effect->IsActive() ? 350.f : 0.f);
        const FVector Position = Effect->GetComponentLocation();
        const auto Detail = Effect->IsRegistered() ? FireViews.Classify(*GetWorld(), Position,
            bFlue ? 1050.f : 85.f, bFlue ? 175.f : 25.f, bFlue ? 3000.f : 1450.f, Reach,
            Effect, Hearth.bFull) : EFireParticleDetail::Off;
        if (Detail == EFireParticleDetail::Off)
        {
            if (Effect->IsActive()) Effect->DeactivateImmediate();
            continue;
        }
        const bool bFull = Detail == EFireParticleDetail::Full;
        if (!bFlue && bFull != Hearth.bFull) Effect->SetEmitterEnable(TEXT("Sparks"), bFull);
        Hearth.bFull = bFull;
        if (bFlue)
        {
            // The furnace's local-space particles expect cm/s and a normalized rainfall.
            // Repaired shops use the same wind and gust samples as working smelters.
            const FVector Wind = WindWithGustAt(Position);
            const float Rain = Weather.IsValid() ? FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f) : 0.f;
            Effect->SetVariableVec3(TEXT("User.Wind"), Effect->GetComponentTransform().InverseTransformVector(Wind));
            Effect->SetVariableFloat(TEXT("User.Rainfall"), Rain);
            Effect->SetVariableFloat(TEXT("User.L1Gate"), bFull && Quality >= 1 ? .55f : 0.f);
            Effect->SetVariableFloat(TEXT("User.DetailReduction"), (Quality == 0 ? .20f : 0.f) + (bFull ? 0.f : .50f));
        }
        if (!Effect->IsActive()) Effect->Activate(true);
    }
}
