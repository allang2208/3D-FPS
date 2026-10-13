#include "FPSCharacterMovementComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordPommelRhythm.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/World.h"

void UFPSCharacterMovementComponent::BeginMeleeLungeRequest(EFPSMeleeMove Kind,const FVector& Direction)
{
    if(!CharacterOwner||CharacterOwner->GetLocalRole()!=ROLE_AutonomousProxy)return;
    const uint32 Next=MeleeRequest.Sequence+1;
    MeleeRequest=FFPSMeleeMoveRequest();MeleeRequest.Sequence=Next?Next:1;
    MeleeRequest.Kind=Kind;MeleeRequest.Direction=Direction.GetSafeNormal2D();
}
void UFPSCharacterMovementComponent::RecordMeleeLungeStep(float Distance)
{
    if(!CharacterOwner||CharacterOwner->GetLocalRole()!=ROLE_AutonomousProxy||!MeleeRequest.Sequence)return;
    MeleeRequest.Distance+=Distance;PendingMeleeStep+=Distance;
}
bool UFPSCharacterMovementComponent::AuthorizeMeleeMove(const FFPSMeleeMoveRequest& R,float& Budget,float& Recovery) const
{
    const auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);
    const auto* Profile=Player?Player->GetNetShadowProfile():nullptr;
    const auto* Item=Profile?Profile->Equipped():nullptr;
    if(!Player||!Item||!ColdSteelInventory::IsTwoHandedSword(*Item)||Profile->ActiveProductionTool()
        ||Player->IsTraversing()||Player->IsSliding()||IsDodging()||IsBipodMovementLocked())return false;
    if(R.Direction.ContainsNaN()||R.Direction.GetSafeNormal2D().IsNearlyZero()||!FMath::IsFinite(R.Distance)
        ||R.Distance<0.f||R.Momentum.ContainsNaN())return false;
    const float Rate=FMath::Max(.01f,float(ColdSteelMelee::Evaluate(*Item,Profile).AttackRate));
    switch(R.Kind)
    {
    case EFPSMeleeMove::Thrust:
    case EFPSMeleeMove::OverheadFinisher:
        if(R.Kind==EFPSMeleeMove::OverheadFinisher&&!ColdSteelModularSword::UsesOverheadFinisher(*Item))return false;
        Budget=RuneSwordThrustRhythm::LungeDistance;Recovery=(RuneSwordThrustRhythm::AttackEnd-RuneSwordThrustRhythm::LungeStart)/Rate;break;
    case EFPSMeleeMove::Pommel:
        Budget=RuneSwordPommelRhythm::LungeDistance;Recovery=(RuneSwordPommelRhythm::AttackEnd-RuneSwordPommelRhythm::LungeStart)/Rate;break;
    case EFPSMeleeMove::Uppercut:
    case EFPSMeleeMove::RisingDragon:
        if(R.Kind==EFPSMeleeMove::Uppercut&&Profile->MasteryProgress(TEXT("swordUppercut")).Level<1)return false;
        if(R.Kind==EFPSMeleeMove::RisingDragon&&!ColdSteelModularSword::UsesRisingDragonFinisher(*Item))return false;
        Budget=RuneSwordUppercutMotion::LungeDistance;
        Recovery=R.Kind==EFPSMeleeMove::Uppercut?
            RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart:
            (RuneSwordUppercutMotion::End-RuneSwordUppercutMotion::ReleaseStart)/Rate;break;
    case EFPSMeleeMove::Dash:
    case EFPSMeleeMove::AirMomentum:
        if(Profile->MasteryProgress(TEXT("dashAttack")).Level<1)return false;
        Budget=Profile->DashAttackStats().DistanceCM;Recovery=.5f;break;
    default:return false;
    }
    return R.Distance<=Budget+1.f;
}
void UFPSCharacterMovementComponent::ProcessMeleeNetworkMove(const FFPSNetworkMoveData& Data,bool Authority)
{
    const auto& R=Data.MeleeRequest;if(!R.Sequence||!CharacterOwner)return;
    auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);if(!Player)return;
    const auto* Status=Player->FindComponentByClass<UCombatStatusFormula>();
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    if(UBoundCongregateCaptureComponent::IsCaptured(Player)||(Status&&Status->BlocksMovement())||(Health&&Health->IsDead()))return;
    bool MomentumStart=Data.bReplayMeleeMomentumStart;
    float Distance=Data.ReplayMeleeStep;
    if(Authority)
    {
        const bool New=static_cast<int32>(R.Sequence-LastServerMeleeSequence)>0;
        if(New)
        {
            LastServerMeleeSequence=R.Sequence;ServerMeleeDistance=0.f;
            float Recovery=0.f;
            bServerMeleeBlocked=GetWorld()->GetTimeSeconds()+.05<ServerMeleeRecoveryUntil||!AuthorizeMeleeMove(R,ServerMeleeBudget,Recovery);
            if(bServerMeleeBlocked){ClientRejectMeleeMove(R.Sequence);return;}
            ServerMeleeRecoveryUntil=GetWorld()->GetTimeSeconds()+Recovery;
        }
        if(R.Sequence!=LastServerMeleeSequence||bServerMeleeBlocked||!FMath::IsFinite(R.Distance))return;
        // Cumulative displacement recovers a dropped move without applying an
        // old/pending/new packet more than once. World collision is re-run here.
        const float Desired=FMath::Clamp(R.Distance,ServerMeleeDistance,ServerMeleeBudget);
        Distance=Desired-ServerMeleeDistance;ServerMeleeDistance=Desired;
        MomentumStart=New&&R.Kind==EFPSMeleeMove::AirMomentum;
    }
    if(MomentumStart)
    {
        FVector Carry=R.Momentum;
        if(Authority)
        {
            // Retain only speed that the server's preceding locomotion earned.
            Carry=Carry.GetClampedToMaxSize(Velocity.Size2D()+1.f);
        }
        if(IsFalling()||PendingLaunchVelocity.Z>0.f)BeginMeleeDashMomentum(Carry);
    }
    if(Distance<=0.f||Player->IsTraversing()||IsDodging())return;
    const FVector Before=UpdatedComponent->GetComponentLocation();
    if(R.Kind==EFPSMeleeMove::Dash&&IsFalling())
    {
        FHitResult Hit;SafeMoveUpdatedComponent(R.Direction*Distance,UpdatedComponent->GetComponentQuat(),true,Hit);
        if(Authority&&Hit.bBlockingHit)bServerMeleeBlocked=true;
    }
    else ApplyMeleeLungeStep(R.Direction,Distance);
    if(Authority&&FVector::DotProduct(UpdatedComponent->GetComponentLocation()-Before,R.Direction)+.1f<Distance)bServerMeleeBlocked=true;
}
void UFPSCharacterMovementComponent::ClientRejectMeleeMove_Implementation(uint32 Sequence)
{
    if(Sequence!=MeleeRequest.Sequence)return;
    RejectedMeleeSequence=Sequence;PendingMeleeStep=0.f;
    if(MeleeRequest.Kind==EFPSMeleeMove::AirMomentum)bMeleeDashMomentum=false;
}
