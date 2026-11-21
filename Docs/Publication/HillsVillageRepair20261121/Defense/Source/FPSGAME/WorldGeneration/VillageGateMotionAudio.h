#pragma once

#include "Components/AudioComponent.h"
#include "VillageGateMotionAudio.generated.h"

/** Plays the original game-dev cue once at the first accepted movement step. */
UCLASS()
class UVillageGateMotionAudio : public UAudioComponent
{
    GENERATED_BODY()
public:
    UVillageGateMotionAudio();
    void Arm() { bAwaitingStep = true; }
    void Moved();
    void Interrupted();
    void ResetForBreach();
private:
    UFUNCTION(NetMulticast, Reliable) void MulticastGateAudio(bool bStart);
    bool bAwaitingStep = false;
    bool bPlayed = false;
};
