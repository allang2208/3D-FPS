#pragma once

#include "CoreMinimal.h"

class AActor;
class APawn;
class APlayerController;
class USkeletalMeshComponent;
class UAnimSequence;
class UResidentTurnAnimInstance;

namespace ResidentConversation
{
    bool IsSpeakerDowned(const AActor* Speaker);
    bool CanReach(const APawn* Pawn, const AActor* Speaker);
}

/** Visual mesh yaw belongs to the viewer's world. The resident's actor transform stays authoritative. */
struct FResidentConversationFacing
{
    static constexpr float RestYaw = -90.f;

    void SetLocalPlayer(APlayerController* Player);
    void StartIdle(USkeletalMeshComponent& Body, UAnimSequence& Idle, float StartSeconds=0.f);

private:
    TWeakObjectPtr<APlayerController> LocalPlayer;
    TWeakObjectPtr<UResidentTurnAnimInstance> Animation;
};
