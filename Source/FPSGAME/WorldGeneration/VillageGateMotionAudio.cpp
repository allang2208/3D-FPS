#include "VillageGateMotionAudio.h"
#include "Engine/World.h"

UVillageGateMotionAudio::UVillageGateMotionAudio()
{
    bAutoActivate = false;
    SetIsReplicatedByDefault(true);
    SetRelativeLocation(FVector(0, 0, 135));
}

void UVillageGateMotionAudio::Moved()
{
    if (!bAwaitingStep) return;
    bAwaitingStep = false;
    bPlayed = true;
    MulticastGateAudio(true);
}

void UVillageGateMotionAudio::Interrupted()
{
    bAwaitingStep = false;
    if (bPlayed) MulticastGateAudio(false);
    bPlayed = false;
}

void UVillageGateMotionAudio::ResetForBreach()
{
    bAwaitingStep = bPlayed = false;
    if (IsPlaying()) Stop();
}

void UVillageGateMotionAudio::MulticastGateAudio_Implementation(bool bStart)
{
    if (GetWorld()->GetNetMode() == NM_DedicatedServer) return;
    // A change of direction replaces the previous mechanical stroke at the same emitter.
    if (bStart) Play();
    else if (IsPlaying()) FadeOut(.06f, 0.f);
}
