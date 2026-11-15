#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "HillsWildlifeAudio.generated.h"

class UAudioComponent;
class USoundWave;

UENUM()
enum class EHillsAnimalSound : uint8 { Alarm, Hurt, Death, TakeOff };

UCLASS()
class FPSGAME_API UHillsWildlifeAudio : public UActorComponent
{
    GENERATED_BODY()
public:
    UHillsWildlifeAudio();
    void SetSpecies(const FString& Id);
    void Signal(EHillsAnimalSound Event);
    void UpdateHooves(bool bRunningOnGround, float RunPhase, const FVector& Feet);

private:
    UFUNCTION(NetMulticast, Reliable) void MulticastSound(EHillsAnimalSound Event);
    void PlayVoice(USoundWave* Sound);

    UPROPERTY(Transient) TArray<TObjectPtr<USoundWave>> Alarm;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundWave>> Hurt;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundWave>> Death;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundWave>> Hooves;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundWave>> Wings;
    TWeakObjectPtr<UAudioComponent> Voice;
    FTimerHandle PendingAlarm;
    FString Species;
    double NextAlarm = 0.;
    double NextHurt = 0.;
    float LastRunPhase = -1.f;
    int32 LastHoof = INDEX_NONE;
    bool bDeathSent = false;
    bool bDeathHeard = false;
};
