#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSFootstepAudioComponent.generated.h"

class USoundBase;
class UAutoFootstepEffectContext;
class ATemperateHillsWorld;
class ACharacter;
USTRUCT(BlueprintType)
struct FFPSFootstepBank
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) TArray<TObjectPtr<USoundBase>> Sounds;
    int32 Last = INDEX_NONE;
};

/** Local first-person foley. Uses distance, not viewmodel animation notifies. */
UCLASS(ClassGroup=(Audio), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSFootstepAudioComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSFootstepAudioComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    // Two consecutive contacts form one left/right cycle. Includes travel since
    // the 30 Hz audio tick so a viewmodel can follow this clock at render rate.
    float GetStridePhaseRadians() const;
    UPROPERTY(EditAnywhere, Category="Footsteps") float Volume = .38f;
    UPROPERTY(EditAnywhere, Category="Footsteps") float WalkStrideCm = 150.f;
    UPROPERTY(EditAnywhere, Category="Footsteps") float RunStrideCm = 205.f;
    UPROPERTY(EditAnywhere, Category="Footsteps") float CrouchStrideCm = 95.f;
    UPROPERTY(EditAnywhere, Category="Footsteps") TMap<FName, FFPSFootstepBank> Banks;
private:
    void Play(FName Bank, const FVector& Position, float Gain);
    FName GroundBank(const FHitResult& Hit) const;
    float GetStepDistanceCm(const ACharacter* Pawn) const;
    UPROPERTY() TObjectPtr<UAutoFootstepEffectContext> Context;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    FVector Previous = FVector::ZeroVector;
    float Distance = 0;
    float LastVerticalSpeed = 0;
    float FindWorldCountdown = 0;
    bool bInitialized = false;
    bool bWasGrounded = false;
    bool bWasWet = false;
    bool bAlternateStep = false;
};
