#include "FPSTraversalComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"

float UFPSTraversalComponent::NetworkClock() const
{
    if(const auto* State=GetWorld()->GetGameState())return State->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
void UFPSTraversalComponent::ServerRequestTraversal_Implementation(uint32 Request)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player||static_cast<int32>(Request-NetworkRequest)<=0)return;
    if(IsTraversing()){ClientRejectTraversal(Request);return;}
    NetworkRequest=Request;
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    const auto* Status=Player->FindComponentByClass<UCombatStatusFormula>();
    const bool Available=!(Health&&Health->IsDead())&&!(Status&&Status->BlocksMovement())
        &&!UBoundCongregateCaptureComponent::IsCaptured(Player)&&!Player->IsSliding()
        &&!Player->IsMeleeSkillMovementLocked()&&!Player->IsWeaponBusy(true);
    // The client sends no destination or height. Re-probe the real server world.
    if(!TryStart(Available,false)){ClientRejectTraversal(Request);return;}
    auto* Movement=Player->GetCharacterMovement();
    if(!bNetworkCorrectionsHeld)bSavedIgnoreCorrections=Movement->bIgnoreClientMovementErrorChecksAndCorrection;
    bNetworkCorrectionsHeld=true;NetworkCorrectionReleaseAt=0.f;
    // Movement is disabled on both peers while this component executes the
    // approved swept path. Never enable client-authoritative positions.
    Movement->bIgnoreClientMovementErrorChecksAndCorrection=true;
    auto Path=LastJumpTarget;
    // Send geometry only: locally generated supports need not have network GUIDs.
    Path.Obstacle=nullptr;Path.Supports.Reset();Path.Reason.Reset();
    ClientBeginTraversal(Request,Path,StartLocation,EntryVelocity,NetworkClock());
    Player->ForceNetUpdate();
}
void UFPSTraversalComponent::ClientBeginTraversal_Implementation(uint32 Request,const FFPSTraversalTarget& Target,FVector Start,FVector Velocity,float StartedAt)
{
    if(Request!=NetworkRequest||!bAwaitingTraversal)return;
    bAwaitingTraversal=false;
    auto* Player=CastChecked<AFPSGAMECharacter>(GetOwner());
    Player->SetActorLocation(Start,false,nullptr,ETeleportType::TeleportPhysics);
    Player->GetCharacterMovement()->Velocity=Velocity;
    if(!BeginTarget(Target)){bAwaitingTraversalEnd=true;ServerCancelTraversal(Request);return;}
    // Catch up through every swept corner, using the same authored action clock.
    Advance(FMath::Max(0.f,NetworkClock()-StartedAt));
}
void UFPSTraversalComponent::ClientRejectTraversal_Implementation(uint32 Request)
{
    if(Request!=NetworkRequest||!bAwaitingTraversal)return;
    bAwaitingTraversal=false;
    auto* Player=CastChecked<AFPSGAMECharacter>(GetOwner());
    // A rejected wall query should retain the original ordinary-jump intent.
    if(bJumpHeld)Player->Jump();
}
void UFPSTraversalComponent::ClientEndTraversal_Implementation(uint32 Request,bool Success,FVector Location,FVector Velocity,uint8 Mode)
{
    if(Request!=NetworkRequest)return;
    TGuardValue<bool> Applying(bApplyingNetworkEnd,true);
    auto* Player=CastChecked<AFPSGAMECharacter>(GetOwner());
    bAwaitingTraversal=bAwaitingTraversalEnd=false;
    Player->SetActorLocation(Location,false,nullptr,ETeleportType::TeleportPhysics);
    if(bTraversing)Finish(Success);
    bLastTraversalSucceeded=Success;
    auto* Movement=Player->GetCharacterMovement();
    Movement->SetMovementMode(EMovementMode(Mode));Movement->Velocity=Velocity;
    ServerAcknowledgeTraversalEnd(Request);
}
void UFPSTraversalComponent::ServerCancelTraversal_Implementation(uint32 Request)
{
    if(Request==NetworkRequest&&bTraversing)Finish(false);
}
void UFPSTraversalComponent::ServerAcknowledgeTraversalEnd_Implementation(uint32 Request)
{
    if(Request==NetworkRequest&&!bTraversing)RestoreNetworkCorrections();
}
void UFPSTraversalComponent::RestoreNetworkCorrections()
{
    if(!bNetworkCorrectionsHeld)return;
    if(auto* Player=Cast<ACharacter>(GetOwner()))Player->GetCharacterMovement()->bIgnoreClientMovementErrorChecksAndCorrection=bSavedIgnoreCorrections;
    bNetworkCorrectionsHeld=false;NetworkCorrectionReleaseAt=0.f;
}
