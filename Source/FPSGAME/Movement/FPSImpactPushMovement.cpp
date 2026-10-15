#include "FPSCharacterMovementComponent.h"
#include "FPSDodgeRootMotionSource.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"

namespace
{
const FName ImpactPushName(TEXT("HeQueImpactPush"));
constexpr float ImpactPushSeconds=.16f;
double PushClock(const UWorld* World)
{const auto* GS=World->GetGameState();return GS?GS->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
}

bool UFPSCharacterMovementComponent::HasImpactPush() const
{
    const auto Active=[](const auto& Sources)
    {
        for(const auto& Source:Sources)if(Source&&Source->InstanceName==ImpactPushName&&Source->GetTime()<Source->Duration
            &&!Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval))return true;
        return false;
    };
    return Active(CurrentRootMotion.RootMotionSources)||Active(CurrentRootMotion.PendingAddRootMotionSources);
}

void UFPSCharacterMovementComponent::ApplyImpactPush(const FVector& Direction,float DistanceCM)
{
    if(!CharacterOwner||!CharacterOwner->HasAuthority()||!FMath::IsFinite(DistanceCM)||DistanceCM<=0.f
        ||Direction.ContainsNaN()||Direction.GetSafeNormal2D().IsNearlyZero())return;
    StartImpactPush(Direction,DistanceCM,0.f);
    // The owner starts the same source; native root-motion corrections reconcile
    // its elapsed time and position. Simulated proxies use replicated movement.
    if(!CharacterOwner->IsLocallyControlled())ClientImpactPush(Direction.GetSafeNormal2D(),DistanceCM,PushClock(GetWorld()));
    CharacterOwner->ForceNetUpdate();
}

void UFPSCharacterMovementComponent::ClientImpactPush_Implementation(FVector_NetQuantizeNormal Direction,float DistanceCM,double StartedAt)
{
    if(!CharacterOwner||CharacterOwner->HasAuthority()||!CharacterOwner->IsLocallyControlled())return;
    const float Age=FMath::Max(0.f,float(PushClock(GetWorld())-StartedAt));
    // A native correction may have already installed this source before the RPC.
    if(Age>=ImpactPushSeconds||HasImpactPush())return;
    StartImpactPush(Direction,DistanceCM,Age);
}

void UFPSCharacterMovementComponent::StartImpactPush(const FVector& Direction,float DistanceCM,float Age)
{
    if(!UpdatedComponent||MovementMode==MOVE_None)return;
    CancelDodge();RemoveRootMotionSource(ImpactPushName);
    auto Source=MakeShared<FRootMotionSource_FPSDodge>();
    Source->InstanceName=ImpactPushName;Source->Priority=1100;
    Source->AccumulateMode=ERootMotionAccumulateMode::Override;
    Source->Duration=ImpactPushSeconds;Source->SetTime(Age);
    Source->Force=Direction.GetSafeNormal2D()*(DistanceCM/ImpactPushSeconds);
    Source->FinishVelocityParams.Mode=ERootMotionFinishVelocityMode::MaintainLastRootMotionVelocity;
    ApplyRootMotionSource(Source);
    if(auto* Body=CharacterOwner->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RecordKnockback(Direction,DistanceCM,ImpactPushSeconds);
}

float UFPSCharacterMovementComponent::SlideAlongSurface(const FVector& Delta,float Time,const FVector& Normal,FHitResult& Hit,bool bHandleImpact)
{
    if(bExecutingImpactPush&&Hit.bBlockingHit&&!IsWalkable(Hit))
    {
        // First wall contact consumes the push. Never turn its remaining ten
        // metres into a slide along the wall or resume after the obstruction.
        const auto Source=GetRootMotionSource(ImpactPushName);
        const bool FirstContact=Source&&!Source->Status.HasFlag(ERootMotionSourceStatusFlags::MarkedForRemoval);
        RemoveRootMotionSource(ImpactPushName);Velocity.X=Velocity.Y=0.f;
        // Consume the source before applying control: repeated sweeps/replayed
        // owner moves cannot refresh the same kick's collision stun.
        if(FirstContact&&CharacterOwner&&CharacterOwner->HasAuthority())
        {
            const auto* Health=CharacterOwner->FindComponentByClass<UFPSCombatHealthComponent>();
            if(!Health||!Health->IsDead())UCombatStatusFormula::GetOrAdd(CharacterOwner)->AddStun(2.f);
        }
        return 0.f;
    }
    return Super::SlideAlongSurface(Delta,Time,Normal,Hit,bHandleImpact);
}
