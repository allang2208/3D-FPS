// Copyright Metaseven. All Rights Reserved.

#include "AutoFootstepEffectContext.h"

#include "Engine/AssetManager.h"
#include "Engine/World.h"
#include "Chaos/ChaosEngineInterface.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"

FAutoFootstepPlayed UAutoFootstepEffectContext::OnFootstepPlayed;

void UAutoFootstepEffectContext::PlayEffectBySurfaceType(const UObject* WorldContextObject, const EPhysicalSurface SurfaceType, const FVector& Location, const FRotator& Rotation, const FAutoFootstepNiagaraParams& NiagaraParams, const FAutoFootstepSoundParams& SoundParams)
{
	// The one choke point every footstep goes through, so listeners (grass deform feedback, impact
	// systems, analytics) do not have to duplicate the trace or hook each notify individually. It is
	// broadcast before the effects and outside the surface lookup: a listener is told about the step
	// whether or not this context happens to have an effect configured for that surface.
	UWorld* World=IsValid(WorldContextObject)?WorldContextObject->GetWorld():nullptr;
	if(!World||World->bIsTearingDown||World->GetNetMode()==NM_DedicatedServer)return;
	OnFootstepPlayed.Broadcast(WorldContextObject, SurfaceType, Location, Rotation);

	if (const FAutoFootstepEffect* Effect = EffectsBySurfaceType.Find(SurfaceType))
	{
		TArray<FSoftObjectPath> EffectPaths;

		if (!Effect->Niagara.IsValid() && !Effect->Niagara.IsNull())
		{
			EffectPaths.Emplace(Effect->Niagara.ToSoftObjectPath());
		}

		if (!Effect->Sound.IsValid() && !Effect->Sound.IsNull())
		{
			EffectPaths.Emplace(Effect->Sound.ToSoftObjectPath());
		}

		if (EffectPaths.IsEmpty())
		{
			UNiagaraFunctionLibrary::SpawnSystemAtLocation(WorldContextObject, Effect->Niagara.Get(), Location + NiagaraParams.LocationOffset, Rotation + NiagaraParams.RotationOffset, NiagaraParams.Scale, true, true, NiagaraParams.PoolingMethod);
			UGameplayStatics::PlaySoundAtLocation(WorldContextObject, Effect->Sound.Get(), Location + SoundParams.LocationOffset, Rotation + SoundParams.RotationOffset, SoundParams.VolumeMultiplier, SoundParams.PitchMultiplier);
			return;
		}

        // Streaming may complete after disconnect/travel or after the surface map changes.
        const TWeakObjectPtr<const UObject> Source(WorldContextObject);
        const TWeakObjectPtr<UWorld> SourceWorld(World);
        const FAutoFootstepEffect PendingEffect=*Effect;
        UAssetManager::GetStreamableManager().RequestAsyncLoad(EffectPaths, [Source, SourceWorld, PendingEffect, Location, Rotation, NiagaraParams, SoundParams]()
        {
            const UObject* Context=Source.Get();UWorld* LoadedWorld=SourceWorld.Get();
            if(!Context||!LoadedWorld||LoadedWorld->bIsTearingDown||Context->GetWorld()!=LoadedWorld)return;
            UNiagaraFunctionLibrary::SpawnSystemAtLocation(Context, PendingEffect.Niagara.Get(), Location + NiagaraParams.LocationOffset, Rotation + NiagaraParams.RotationOffset, NiagaraParams.Scale, true, true, NiagaraParams.PoolingMethod);
            UGameplayStatics::PlaySoundAtLocation(Context, PendingEffect.Sound.Get(), Location + SoundParams.LocationOffset, Rotation + SoundParams.RotationOffset, SoundParams.VolumeMultiplier, SoundParams.PitchMultiplier);
        });
	}
}

#if WITH_EDITOR
void UAutoFootstepEffectContext::AddAllSurfaceTypeElements()
{
	for (int32 SurfaceType = SurfaceType_Default; SurfaceType < SurfaceType_Max; ++SurfaceType)
	{
		if (StaticEnum<EPhysicalSurface>()->HasMetaData(TEXT("Hidden"), SurfaceType))
		{
			continue;
		}

		if (EffectsBySurfaceType.Contains(StaticCast<EPhysicalSurface>(SurfaceType)))
		{
			continue;
		}

		EffectsBySurfaceType.Add(StaticCast<EPhysicalSurface>(SurfaceType));
	}
}
#endif
