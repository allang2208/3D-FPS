#include "VillageMillKeeper.h"

#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"

void AVillageMillKeeper::BeginPlay()
{
    Super::BeginPlay();
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    if (GetNetMode() == NM_DedicatedServer) return;

    USkeletalMeshComponent* Body = GetMesh();
    if (auto* Idle = Cast<UAnimSequence>(Body->AnimationData.AnimToPlay))
        Facing.StartIdle(*Body, *Idle, Body->AnimationData.SavedPosition);
}

void AVillageMillKeeper::SetLocalConversation(APlayerController* Player)
{
    Facing.SetLocalPlayer(Player);
}
