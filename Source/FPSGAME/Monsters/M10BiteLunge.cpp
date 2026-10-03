#include "M10Mawcrawler.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"

void AM10Mawcrawler::AdvanceBiteLunge(float Seconds)
{
    if(!HasAuthority()||State!=EM10State::Bite)return;
    const float T=FMath::Clamp((Seconds-.52f)/.18f,0.f,1.f),Progress=1.f-FMath::Square(1.f-T);
    const float Distance=FMath::Max(0.f,Progress-BiteLungeProgress)*BiteLungeDistance;
    BiteLungeProgress=Progress;
    auto* Move=GetCharacterMovement();if(Distance<=0.f||!Target.IsValid()||!Move->IsMovingOnGround())return;
    const FVector Delta=GetActorForwardVector()*Distance;
    const FVector Feet=GetActorLocation()-FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M10LungeSupport),false,this);Query.AddIgnoredActor(Target.Get());
    FHitResult Support;
    const FVector NextFeet=Feet+Delta;
    if(!GetWorld()->LineTraceSingleByChannel(Support,NextFeet+FVector(0,0,Move->MaxStepHeight+5.f),
        NextFeet-FVector(0,0,Move->MaxStepHeight+8.f),ECC_Visibility,Query)||!Move->IsWalkable(Support))return;
    FHitResult Block;
    // Swept translation stops at characters/walls; no teleport or return snap.
    Move->SafeMoveUpdatedComponent(Delta,GetActorQuat(),true,Block);
}
