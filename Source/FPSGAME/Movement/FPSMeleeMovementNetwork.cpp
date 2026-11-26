#include "FPSCharacterMovementComponent.h"
#include "../Weapons/PojunGrip.h"
#include "../Skills/LightningHasteSpeed.h"
#include "../Skills/SwordUppercutWeapon.h"
#include "../Skills/ShadowStepWeapon.h"
#include "../Weapons/Staff/StaffOffhandQuickMotion.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Weapons/RuneSwordThrustRhythm.h"
#include "../Weapons/RuneSwordPommelRhythm.h"
#include "../Weapons/RuneSwordUppercutMotion.h"
#include "../Weapons/RuneSwordOverheadRhythm.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "../Weapons/Kukri/KukriAttackTiming.h"
#include "Engine/World.h"

void UFPSCharacterMovementComponent::BeginMeleeLungeRequest(EFPSMeleeMove Kind,const FVector& Direction,uint32 HammerAttackId)
{
    if(!CharacterOwner||CharacterOwner->GetLocalRole()!=ROLE_AutonomousProxy)return;
    const uint32 Next=MeleeRequest.Sequence+1;
    MeleeRequest=FFPSMeleeMoveRequest();MeleeRequest.Sequence=Next?Next:1;
    MeleeRequest.Kind=HammerAttackId?(Kind==EFPSMeleeMove::Dash?EFPSMeleeMove::HammerDash:EFPSMeleeMove::HammerAirMomentum):Kind;
    MeleeRequest.HammerAttackId=HammerAttackId;MeleeRequest.Direction=Direction.GetSafeNormal2D();
    if(!HammerAttackId&&(Kind==EFPSMeleeMove::Thrust||Kind==EFPSMeleeMove::AirMomentum||Kind==EFPSMeleeMove::Dash))
        if(const auto* Kukri=CharacterOwner->FindComponentByClass<UKukriWeaponComponent>();Kukri&&Kukri->IsEquipped())
            MeleeRequest.KukriAttackId=Kukri->NetworkAttackSerial();
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
    const auto* Tool=Profile?Profile->ActiveProductionTool():nullptr;
    // (Main hand empty: the lone off-hand kukri / hatchet owns the uppercut and sprint-attack strides.)
    const auto* Item=Tool?Tool:Profile?Profile->ActiveKukriWeapon():nullptr;
    // Resolve the staff's blade only for its uppercut; other staff movement keeps its own eligibility.
    if(Item&&!Tool&&(R.Kind==EFPSMeleeMove::Uppercut||ColdSteelInventory::IsDualPistol(*Item)))
        Item=SwordUppercutWeapon::Resolve(Profile);
    const bool StaffUppercut=R.Kind==EFPSMeleeMove::Uppercut&&SwordUppercutWeapon::IsStaffBlade(Profile,Item);
    const auto* ToolAction=Player?Player->FindComponentByClass<UProductionToolComponent>():nullptr;
    const bool HammerUppercut=Tool&&PojunGrip::UsesHammerMotion(*Tool)&&R.Kind==EFPSMeleeMove::Uppercut&&
        ToolAction&&ToolAction->IsUppercutActive();
    FVector HammerDirection;float HammerLimit=0.f;
    const bool HammerSprint=Tool&&PojunGrip::UsesHammerMotion(*Tool)&&IsHammerSprintMove(R.Kind)&&ToolAction&&
        ToolAction->GetCommittedSprintMovement(R.HammerAttackId,HammerDirection,Budget,HammerLimit,Recovery);
    // The one-handed kukri only has the uppercut stride (KukriUppercut.cpp); its budget/recovery are the sword uppercut's.
    const bool KukriUppercut=Item&&!Tool&&R.Kind==EFPSMeleeMove::Uppercut&&
        (ColdSteelInventory::IsOneHandedMelee(*Item)||StaffUppercut);
    // ...and the sprint attack's momentum carry (KukriDashAttack.cpp / FirePressed: BeginMeleeDashMomentum), the dash budget.
    const bool KukriDash=Item&&!Tool&&(R.Kind==EFPSMeleeMove::Dash||R.Kind==EFPSMeleeMove::AirMomentum)&&
        ColdSteelInventory::IsOneHandedMelee(*Item);
    const auto ShadowGrip=R.Kind==EFPSMeleeMove::ShadowStep?ShadowStepWeapon::ResolveGrip(Profile):ShadowStepWeapon::FResolvedGrip{};
    const bool bShadowStep=ShadowGrip.IsValid();
    if(bShadowStep)Item=ShadowGrip.Primary;
    // The dual thrust uses the same active pair and authored clock as the owner.
    const auto* KukriOffhand=Item&&!Tool&&R.Kind==EFPSMeleeMove::Thrust&&ColdSteelInventory::IsOneHandedMelee(*Item)?
        ColdSteelMelee::PairedOneHandedWeapon(Item,Profile):nullptr;
    const bool KukriThrust=KukriOffhand!=nullptr;
    if(KukriDash||KukriThrust||R.KukriAttackId)
    {
        const auto* PS=Player?Player->GetPlayerState<AColdSteelPlayerState>():nullptr;
        FVector Direction;float Limit=0.f;
        if(!PS||!PS->GetKukriMovement(R.KukriAttackId,uint8(R.Kind),Direction,Limit,Recovery))return false;
        if(KukriDash&&R.Distance!=0.f)return false;
    }
    if(!Player||!Item||(!HammerUppercut&&!HammerSprint&&!KukriUppercut&&!KukriDash&&!KukriThrust&&!bShadowStep&&(Tool||!ColdSteelInventory::IsTwoHandedSword(*Item)))
        ||Player->IsTraversing()||Player->IsSliding()||IsDodging()||IsBipodMovementLocked())return false;
    if(R.Direction.ContainsNaN()||R.Direction.GetSafeNormal2D().IsNearlyZero()||!FMath::IsFinite(R.Distance)
        ||R.Distance<0.f||R.Momentum.ContainsNaN())return false;
    if(HammerSprint)return R.Kind==EFPSMeleeMove::HammerAirMomentum?
        R.Distance==0.f&&(IsFalling()||PendingLaunchVelocity.Z>0.f):R.Distance<=Budget+1.f;
    const float Rate=FMath::Max(.01f,float(ColdSteelMelee::Evaluate(*Item,Profile).AttackRate));
    const float ActionRate=LightningHaste::ActionSpeed(Player);
    switch(R.Kind)
    {
    case EFPSMeleeMove::Thrust:
    case EFPSMeleeMove::OverheadFinisher:
        if(R.Kind==EFPSMeleeMove::OverheadFinisher&&!ColdSteelModularSword::UsesOverheadFinisher(*Item))return false;
        if(KukriThrust)
        {
            const auto OffhandStats=ColdSteelMelee::Evaluate(*KukriOffhand,Profile);
            Budget=KukriRhythm::DualThrustLungeCM;
            Recovery=KukriAttackTiming::DualThrustRecoverySeconds(KukriAttackTiming::PlayRate(Rate),
                KukriAttackTiming::PlayRate(OffhandStats.AttackRate));
        }
        else
        {
            Budget=RuneSwordThrustRhythm::LungeDistance;
            Recovery=(RuneSwordThrustRhythm::AttackEnd-RuneSwordThrustRhythm::LungeStart)/Rate;
        }
        break;
    case EFPSMeleeMove::Pommel:
        Budget=RuneSwordPommelRhythm::LungeDistance;Recovery=(RuneSwordPommelRhythm::AttackEnd-RuneSwordPommelRhythm::LungeStart)/Rate;break;
    case EFPSMeleeMove::Uppercut:
    case EFPSMeleeMove::RisingDragon:
        if(R.Kind==EFPSMeleeMove::Uppercut&&!(HammerUppercut&&ToolAction->IsPojunUppercutStride())&&Profile->MasteryProgress(TEXT("swordUppercut")).Level<1)return false;
        if(R.Kind==EFPSMeleeMove::RisingDragon&&!ColdSteelModularSword::UsesRisingDragonFinisher(*Item))return false;
        Budget=RuneSwordUppercutMotion::LungeDistance;
        // The kukri (main hand or off hand) ends its faster uppercut on its own clock; holding the sword's longer
        // recovery would refuse the next stride (e.g. a sprint attack) that the client is already allowed to start.
        Recovery=R.Kind==EFPSMeleeMove::Uppercut?(KukriUppercut?
            KukriRhythm::UpperRealSeconds(KukriRhythm::UpperLungeStart,KukriRhythm::Swings[KukriRhythm::UppercutStage].Length):
            RuneSwordUppercutMotion::SkillPlaybackTime(RuneSwordUppercutMotion::End)-RuneSwordUppercutMotion::ReleaseStart)/ActionRate:
            (RuneSwordUppercutMotion::End-RuneSwordUppercutMotion::ReleaseStart)/Rate;
        if(StaffUppercut)Recovery+=StaffOffhandQuickMotion::Return/ActionRate;
        break;
    case EFPSMeleeMove::Dash:
    case EFPSMeleeMove::AirMomentum:
        if(Profile->MasteryProgress(TEXT("dashAttack")).Level<1)return false;
        Budget=Profile->DashAttackStats().DistanceCM;Recovery=.5f/ActionRate;break;
    case EFPSMeleeMove::Zhufeng:
    {
        if(Profile->MasteryProgress(TEXT("dashAttack")).Level<1||!ColdSteelModularSword::UsesZhufengWhirlwind(*Item))return false;
        const auto& W=Profile->MasteryDefinition(TEXT("whirlwind")).Whirlwind;
        const float Speed=Profile->DashAttackStats().DistanceCM/RuneSwordOverheadRhythm::DashWindupSeconds;
        Budget=Speed*(W.ReadySeconds+W.SpinSeconds);Recovery=(W.ReadySeconds+W.SpinSeconds+W.RecoverSeconds)/ActionRate;break;
    }
    case EFPSMeleeMove::ShadowStep:
    {
        if(!bShadowStep||Profile->MasteryProgress(ShadowStep::SkillId).Level<1)return false;
        const auto* PS=Player->GetPlayerState<AColdSteelPlayerState>();
        if(PS&&!PS->IsShadowStepDashOpen(Player))return false;
        Budget=Profile->ShadowStepStats().DashDistanceCM+20.f;
        Recovery=(ShadowStep::Stage1Duration-ShadowStep::Stage1DashStart)/ActionRate;
        break;
    }
    default:return false;
    }
    return R.Distance<=Budget+1.f;
}
bool UFPSCharacterMovementComponent::IsNetworkDashWindowOpen() const
{
    // A sprint attack that carries its momentum (BeginMeleeDashMomentum) commits with an AirMomentum request instead of the
    // fixed Dash stride: the kukri always does, the sword after a slide jump.  AuthorizeMeleeMove gates both on dashAttack.
    return GetOwner()&&GetOwner()->HasAuthority()&&GetWorld()
        &&(ServerMeleeKind==EFPSMeleeMove::Dash||IsMeleeMomentumMove(ServerMeleeKind)||ServerMeleeKind==EFPSMeleeMove::HammerDash)
        &&GetWorld()->GetTimeSeconds()<=ServerMeleeWindowUntil;
}

bool UFPSCharacterMovementComponent::IsNetworkMeleeMoveWindowOpen(EFPSMeleeMove Kind) const
{
    // The dual kukri's double thrust (KukriWeaponComponent::AdvanceDualThrustLunge) pushes its targets back; a remote
    // owner's contacts carry that push only while its authorized Thrust stride is in flight (ColdSteelPlayerState).
    return GetOwner()&&GetOwner()->HasAuthority()&&GetWorld()&&ServerMeleeKind==Kind&&!bServerMeleeBlocked
        &&GetWorld()->GetTimeSeconds()<=ServerMeleeWindowUntil;
}

void UFPSCharacterMovementComponent::ProcessMeleeNetworkMove(const FFPSNetworkMoveData& Data,bool Authority)
{
    const auto& R=Data.MeleeRequest;if(!R.Sequence||!CharacterOwner)return;
    if(!Authority&&IsMeleeMoveRejected(R.Sequence))return;
    auto* Player=Cast<AFPSGAMECharacter>(CharacterOwner);if(!Player)return;
    if(!Authority&&R.KukriAttackId)
    {
        const auto* Action=Player->FindComponentByClass<UKukriWeaponComponent>();
        if(!Action||Action->NetworkAttackSerial()!=R.KukriAttackId)return;
    }
    const auto* Status=Player->FindComponentByClass<UCombatStatusFormula>();
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    if(UBoundCongregateCaptureComponent::IsCaptured(Player)||(Status&&Status->BlocksMovement())||(Health&&Health->IsDead()))return;
    bool MomentumStart=Data.bReplayMeleeMomentumStart;
    float Distance=Data.ReplayMeleeStep;
    FVector Direction=R.Direction;
    if(Authority)
    {
        const bool New=static_cast<int32>(R.Sequence-LastServerMeleeSequence)>0;
        if(!New&&R.Kind!=ServerMeleeKind)return;
        float WhirlwindLimit=0.f,HammerLimit=0.f,KukriLimit=0.f;
        const auto* Profile=Player->GetNetShadowProfile();
        const auto* Held=Profile&&!Profile->ActiveProductionTool()?Profile->Equipped():nullptr;
        const bool KukriMove=R.KukriAttackId||(Held&&ColdSteelInventory::UsesKukriMoveset(*Held)&&
            (R.Kind==EFPSMeleeMove::Thrust||R.Kind==EFPSMeleeMove::AirMomentum||R.Kind==EFPSMeleeMove::Dash));
        if(KukriMove)
        {
            const auto* PS=Player->GetPlayerState<AColdSteelPlayerState>();float Recovery=0.f;
            if(!PS||!PS->GetKukriMovement(R.KukriAttackId,uint8(R.Kind),Direction,KukriLimit,Recovery))
            {
                if(PS&&PS->IsKukriMovementPending(R.KukriAttackId))return;
                if(New){LastServerMeleeSequence=R.Sequence;ServerMeleeKind=R.Kind;bServerMeleeBlocked=true;ClientRejectMeleeMove(R.Sequence);}
                return;
            }
        }
        if(R.Kind==EFPSMeleeMove::Zhufeng)
        {
            const auto* PS=Player->GetPlayerState<AColdSteelPlayerState>();
            // The movement channel can arrive before the reliable cast channel.
            // Retry on the next cumulative move instead of permanently rejecting it.
            if(!PS||!PS->SwordWhirlwindMove(R.Sequence,Direction,WhirlwindLimit))return;
        }
        if(IsHammerSprintMove(R.Kind))
        {
            const auto* Action=Player->FindComponentByClass<UProductionToolComponent>();
            float Budget=0.f,Recovery=0.f;
            if(!Action||!Action->GetCommittedSprintMovement(R.HammerAttackId,Direction,Budget,HammerLimit,Recovery))
            {
                // An unseen attack may still arrive on the reliable channel.
                // Rejected/cancelled/old attacks must never borrow a later cast.
                if(Action&&Action->IsSprintMovementPending(R.HammerAttackId))return;
                if(New){LastServerMeleeSequence=R.Sequence;ServerMeleeKind=R.Kind;bServerMeleeBlocked=true;ClientRejectMeleeMove(R.Sequence);}
                return;
            }
        }
        if(New)
        {
            LastServerMeleeSequence=R.Sequence;ServerMeleeDistance=0.f;ServerMeleeKind=R.Kind;
            float Recovery=0.f;
            const double MoveNow=GetWorld()->GetTimeSeconds();
            bServerMeleeBlocked=MoveNow+.05<ServerMeleeRecoveryUntil||!AuthorizeMeleeMove(R,ServerMeleeBudget,Recovery);
            if(bServerMeleeBlocked){ClientRejectMeleeMove(R.Sequence);return;}
            ServerHammerAttackId=IsHammerSprintMove(R.Kind)?R.HammerAttackId:0;
            ServerKukriAttackId=KukriMove?R.KukriAttackId:0;
            if(R.Kind==EFPSMeleeMove::HammerDash)Player->StopMovementForMeleeSkill();
            ServerMeleeRecoveryUntil=MoveNow+Recovery;
            ServerMeleeWindowUntil=MoveNow+.75;
        }
        if(R.Sequence!=LastServerMeleeSequence||bServerMeleeBlocked||!FMath::IsFinite(R.Distance))return;
        // Cumulative displacement recovers a dropped move without applying an
        // old/pending/new packet more than once. World collision is re-run here.
        if(IsHammerSprintMove(R.Kind)&&ServerHammerAttackId!=R.HammerAttackId)return;
        if(KukriMove&&ServerKukriAttackId!=R.KukriAttackId)return;
        const float Limit=KukriMove?FMath::Min(ServerMeleeBudget,KukriLimit):R.Kind==EFPSMeleeMove::Zhufeng?FMath::Min(ServerMeleeBudget,WhirlwindLimit):
            R.Kind==EFPSMeleeMove::HammerAirMomentum?0.f:IsHammerSprintMove(R.Kind)?FMath::Min(ServerMeleeBudget,HammerLimit):ServerMeleeBudget;
        const float Desired=FMath::Max(ServerMeleeDistance,FMath::Min(R.Distance,Limit));
        Distance=Desired-ServerMeleeDistance;ServerMeleeDistance=Desired;
        MomentumStart=New&&IsMeleeMomentumMove(R.Kind);
    }
    if(MomentumStart)
    {
        FVector Carry=R.Momentum;
        if(Authority)
        {
            // Retain only speed that the server's preceding locomotion earned.
            Carry=R.Kind==EFPSMeleeMove::HammerAirMomentum?FVector(Velocity.X,Velocity.Y,0.f):
                Carry.GetClampedToMaxSize(Velocity.Size2D()+1.f);
            if(R.Kind==EFPSMeleeMove::HammerAirMomentum)Player->StopMovementForMeleeSkill();
        }
        // The sword only carries momentum from the air or a queued slide jump (its grounded dash is the fixed Dash stride);
        // the kukri's sprint attack carries it from the ground too, so the server brakes the same carry as the client.
        // Server: the shadow profile's held item; owning client replaying a correction: its own kukri component.
        const auto* Shadow=Player->GetNetShadowProfile();
        const auto* Held=Shadow&&!Shadow->ActiveProductionTool()?Shadow->Equipped():nullptr;
        const auto* Kukri=Player->FindComponentByClass<UKukriWeaponComponent>();
        const bool bKukri=(Held&&ColdSteelInventory::IsOneHandedMelee(*Held))||(Kukri&&Kukri->IsEquipped());
        if(IsFalling()||PendingLaunchVelocity.Z>0.f||bKukri)BeginMeleeDashMomentum(Carry);
    }
    if(Distance<=0.f||Player->IsTraversing()||IsDodging())return;
    const FVector Before=UpdatedComponent->GetComponentLocation();
    if(R.Kind==EFPSMeleeMove::ShadowStep)ApplyShadowStepDashStep(Direction,Distance,false);
    else if((R.Kind==EFPSMeleeMove::Dash||R.Kind==EFPSMeleeMove::HammerDash||R.Kind==EFPSMeleeMove::Zhufeng)&&IsFalling())
    {
        FHitResult Hit;SafeMoveUpdatedComponent(Direction*Distance,UpdatedComponent->GetComponentQuat(),true,Hit);
        if(Authority&&Hit.bBlockingHit)bServerMeleeBlocked=true;
    }
    else ApplyMeleeLungeStep(Direction,Distance);
    if(Authority&&FVector::DotProduct(UpdatedComponent->GetComponentLocation()-Before,Direction)+.1f<Distance)bServerMeleeBlocked=true;
}
void UFPSCharacterMovementComponent::ClientRejectMeleeMove_Implementation(uint32 Sequence)
{
    if(Sequence!=MeleeRequest.Sequence)return;
    RejectedMeleeSequence=Sequence;PendingMeleeStep=0.f;
    if(IsMeleeMomentumMove(MeleeRequest.Kind))bMeleeDashMomentum=false;
}

void UFPSCharacterMovementComponent::CancelHammerSprintMove(uint32 AttackId)
{
    if(!AttackId)return;
    if(ServerHammerAttackId==AttackId)
    {bServerMeleeBlocked=true;ServerMeleeRecoveryUntil=ServerMeleeWindowUntil=0.;bMeleeDashMomentum=false;}
    if(IsHammerSprintMove(MeleeRequest.Kind)&&MeleeRequest.HammerAttackId==AttackId)
    {RejectedMeleeSequence=MeleeRequest.Sequence;PendingMeleeStep=0.f;bPendingMeleeMomentum=false;bMeleeDashMomentum=false;}
}

void UFPSCharacterMovementComponent::CancelKukriAttackMove(uint32 AttackId)
{
    if(!AttackId)return;
    if(ServerKukriAttackId==AttackId)
    {bServerMeleeBlocked=true;ServerMeleeRecoveryUntil=ServerMeleeWindowUntil=0.;bMeleeDashMomentum=false;}
    if(MeleeRequest.KukriAttackId==AttackId)
    {RejectedMeleeSequence=MeleeRequest.Sequence;PendingMeleeStep=0.f;bPendingMeleeMomentum=false;bMeleeDashMomentum=false;}
}
