// Copyright Metaseven. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "NiagaraCommon.h"
#include "AutoFootstepEffectContext.generated.h"

class UNiagaraSystem;
class USoundBase;
enum EPhysicalSurface : int;

/**
 * Broadcast by UAutoFootstepEffectContext::PlayEffectBySurfaceType for every footstep it plays,
 * whatever the surface, the caller or the effect configuration.
 *
 * This is the plugin's single gameplay-facing hook: other systems (the GPU grass footstep feedback
 * component, for example) subscribe to it instead of duplicating the footstep trace. It is a static
 * multicast delegate, so subscribers outlive the effect context instances - which is what lets a
 * component subscribe once in BeginPlay without owning the context.
 *
 * SourceContext identifies the emitting actor/component and its world, including multi-world PIE.
 * Location/Rotation are the *effect* transform: the caller's location/rotation before the
 * per-effect offsets of FAutoFootstepNiagaraParams / FAutoFootstepSoundParams are applied, so a
 * listener sees the same contact point on both the synchronous and the async-load path.
 * The delegate is game-thread only, like everything else on this path.
 */
DECLARE_MULTICAST_DELEGATE_FourParams(FAutoFootstepPlayed, const UObject* /*SourceContext*/, EPhysicalSurface /*Surface*/,
	const FVector& /*Location*/, const FRotator& /*Rotation*/);

USTRUCT(BlueprintType)
struct FAutoFootstepNiagaraParams
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	FVector LocationOffset = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	FRotator RotationOffset = FRotator::ZeroRotator;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	FVector Scale = FVector::OneVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	ENCPoolMethod PoolingMethod = ENCPoolMethod::AutoRelease;
};

USTRUCT(BlueprintType)
struct FAutoFootstepSoundParams
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	FVector LocationOffset = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	FRotator RotationOffset = FRotator::ZeroRotator;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	float VolumeMultiplier = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	float PitchMultiplier = 1.0f;
};

USTRUCT(BlueprintType)
struct FAutoFootstepEffect
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	TSoftObjectPtr<UNiagaraSystem> Niagara;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "AutoFootstep")
	TSoftObjectPtr<USoundBase> Sound;
};

UCLASS()
class AUTOFOOTSTEP_API UAutoFootstepEffectContext : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "AutoFootstep", meta = (WorldContext = "WorldContextObject", AutoCreateRefTerm = "NiagaraParams, SoundParams", AdvancedDisplay = 4))
	void PlayEffectBySurfaceType(
		const UObject* WorldContextObject,
		const EPhysicalSurface SurfaceType,
		const FVector& Location,
		const FRotator& Rotation,
		const FAutoFootstepNiagaraParams& NiagaraParams = FAutoFootstepNiagaraParams(),
		const FAutoFootstepSoundParams& SoundParams = FAutoFootstepSoundParams()
	);

#if WITH_EDITOR
	UFUNCTION(CallInEditor, Category = "AutoFootstep")
	void AddAllSurfaceTypeElements();
#endif

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "AutoFootstep")
	TMap<TEnumAsByte<EPhysicalSurface>, FAutoFootstepEffect> EffectsBySurfaceType;

	/**
	 * Raised once per PlayEffectBySurfaceType call, before the effect is spawned. Static because the
	 * contexts themselves are transient (UFPSFootstepAudioComponent creates one per component and
	 * mutates it at runtime), so listeners must not depend on a particular instance surviving.
	 */
	static FAutoFootstepPlayed OnFootstepPlayed;
};
