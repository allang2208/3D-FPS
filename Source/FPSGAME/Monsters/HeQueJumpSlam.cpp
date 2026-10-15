#include "HeQueMonster.h"
#include "HeQueJumpTiming.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/MagicOcclusion.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"

float AHeQueMonster::JumpAge() const {return FMath::Max(0.f,float(ActionClock()-JumpSlam.StartedAt));}
float AHeQueMonster::JumpClearanceHeight() const
{
    const auto* Capsule=GetCapsuleComponent();
    const FVector Start=GetActorLocation()+FVector(0,0,3);
    const FVector End=Start+FVector(0,0,JumpHeight+20.f);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueJumpClearance),false,this);
    const FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
    FHitResult Hit;
    if(!GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,Capsule->GetCollisionObjectType(),
        FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius()-.5f,Capsule->GetScaledCapsuleHalfHeight()-1.f),Query,Responses))return JumpHeight;
    return Hit.bStartPenetrating?0.f:FMath::Clamp(Hit.Time*(JumpHeight+20.f)-20.f,0.f,JumpHeight);
}
bool AHeQueMonster::CanJumpSlam(APawn* Victim) const
{
    if(Busy()||SweepBlocked()||ActionClock()<NextJumpAt||!JumpChargeClip||!JumpAirClip||!JumpDiveClip||!JumpRecoverClip||
        !JumpWaveMesh||!JumpWaveMaterial||!IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetNavAgentLocation()-GetNavAgentLocation();
    if(Delta.Size2D()>600.f||FMath::Abs(Delta.Z)>100.f)return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueJumpSight),true,this);
    return MagicOcclusion::HasExposure(GetWorld(),Victim,GetActorLocation(),Query,this)&&JumpClearanceHeight()>=70.f;
}
void AHeQueMonster::SetJumpPhase(EHeQueJumpPhase Phase)
{
    JumpSlam.Phase=Phase;JumpSlam.StartedAt=ActionClock();++JumpSlam.Serial;
    OnRep_JumpSlam();ForceNetUpdate();
}
bool AHeQueMonster::StartJumpSlam(APawn* Victim)
{
    CombatTarget=Victim;JumpVictims.Reset();JumpPreviousRadius=0.f;bJumpWaveFinished=false;
    NextJumpAt=ActionClock()+FMath::Max(6.f,JumpCooldown);
    GetCharacterMovement()->StopMovementImmediately();SetJumpPhase(EHeQueJumpPhase::Charge);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AHeQueMonster::CancelJumpSlam()
{
    if(!HasAuthority()||JumpSlam.Phase==EHeQueJumpPhase::None)return;
    JumpVictims.Reset();bJumpWaveFinished=true;SetJumpPhase(EHeQueJumpPhase::None);
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AHeQueMonster::LandJumpSlam(const FHitResult& Hit)
{
    const auto* Contact=Hit.GetComponent();
    if(!Contact||Contact->GetCollisionObjectType()==ECC_Pawn||Hit.ImpactNormal.Z<GetCharacterMovement()->GetWalkableFloorZ())
    {CancelJumpSlam();return;}
    GetCharacterMovement()->StopMovementImmediately();
    JumpSlam.ImpactPoint=Hit.ImpactPoint;JumpSlam.ImpactNormal=Hit.ImpactNormal.GetSafeNormal();
    JumpPreviousRadius=0.f;bJumpWaveFinished=false;
    // Contact creates the replicated audiovisual event before damage callbacks
    // can parry/kill us. No animation timestamp can fabricate a ground impact.
    SetJumpPhase(EHeQueJumpPhase::Recovery);
    const double Ready=ActionClock()+HeQueJumpTiming::Recovery+.4;
    NextClampAt=FMath::Max(NextClampAt,Ready);NextSweepAt=FMath::Max(NextSweepAt,Ready);
    NextRiftAt=FMath::Max(NextRiftAt,Ready);NextPsychicAt=FMath::Max(NextPsychicAt,Ready);
    ApplyJumpWave(JumpImpactRadius,true);
}
UAnimSequence* AHeQueMonster::JumpClip(float& Seconds) const
{
    Seconds=JumpAge();UAnimSequence* Clip=nullptr;
    switch(JumpSlam.Phase)
    {
    case EHeQueJumpPhase::Charge:Clip=JumpChargeClip;break;
    case EHeQueJumpPhase::Rising:Clip=JumpAirClip;break;
    case EHeQueJumpPhase::Falling:Clip=JumpDiveClip;break;
    case EHeQueJumpPhase::Recovery:Clip=JumpRecoverClip;break;
    default:break;
    }
    if(Clip)Seconds=FMath::Clamp(Seconds,0.f,Clip->GetPlayLength());
    return Clip;
}
void AHeQueMonster::ApplyJumpWave(float Radius,bool bImpact)
{
    const FVector Point=JumpSlam.ImpactPoint,Normal=JumpSlam.ImpactNormal;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueGroundShock),true,this);
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(const auto* PC=It->Get())Query.AddIgnoredActor(PC->GetPawn());
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* Player=It->Get()?It->Get()->GetPawn().Get():nullptr;
        if(!Player||JumpVictims.Contains(Player))continue;
        const auto* Vitals=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!Vitals||Vitals->IsDead())continue;
        float BodyRadius=0.f,HalfHeight=0.f;Player->GetSimpleCollisionCylinder(BodyRadius,HalfHeight);
        const FVector Feet=Player->GetActorLocation()-FVector(0,0,HalfHeight),Delta=Feet-Point;
        const float Height=FVector::DotProduct(Delta,Normal);
        if(FMath::Abs(Height)>(bImpact?160.f:HeQueJumpTiming::GroundBandHeight))continue;
        const float Distance=(Delta-Normal*Height).Size();
        if(Distance-BodyRadius>Radius||(!bImpact&&Distance+BodyRadius<JumpPreviousRadius-28.f))continue;
        FHitResult Block;
        if(MagicOcclusion::TraceBlocker(GetWorld(),Point+Normal*15.f,Feet+FVector(0,0,35),Query,Block,this))continue;
        // Impact and expanding ring share this set: no double damage to a
        // player under the body, or re-hit after dodge invulnerability ends.
        JumpVictims.Add(Player);
        const float Before=Vitals->Health;
        UGameplayStatics::ApplyDamage(Player,bImpact?JumpImpactDamage:JumpWaveDamage,GetController(),this,
            bImpact?UEnemyMeleeDamage::StaticClass():UEnemyRangedDamage::StaticClass());
        // The receiver owns armor, dodge, guard and immunity. The raw return
        // value of ApplyDamage alone does not prove that health was lost.
        if(IsValid(Player)&&!Vitals->IsDead()&&Vitals->Health<Before)
            UCombatStatusFormula::GetOrAdd(Player)->AddCripple(5.f);
        if(!IsJumpSlamming()||IsActorBeingDestroyed())return;
    }
}
void AHeQueMonster::TickJumpSlam()
{
    if(JumpSlam.Phase==EHeQueJumpPhase::None)return;
    const float Age=JumpAge();auto* Move=GetCharacterMovement();
    if(HasAuthority())
    {
        const auto* AI=Cast<AMonsterAIController>(GetController());const auto* Status=FindComponentByClass<UCombatStatusFormula>();
        if(Dead()||Controlled()||!AI||!AI->bDecisionEnabled||(Status&&(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned())))
        {CancelJumpSlam();return;}
        if(JumpSlam.Phase==EHeQueJumpPhase::Charge)
        {
            if(!Move->IsMovingOnGround()){CancelJumpSlam();return;}
            if(Age>=HeQueJumpTiming::Charge)
            {
                const float Height=JumpClearanceHeight();
                if(Height<70.f){CancelJumpSlam();return;}
                const float UpSpeed=FMath::Sqrt(2.f*FMath::Abs(Move->GetGravityZ())*Height);
                Move->StopMovementImmediately();Move->ClearAccumulatedForces();Move->SetMovementMode(MOVE_Falling);
                SetJumpPhase(EHeQueJumpPhase::Rising);LaunchCharacter(FVector(0,0,UpSpeed),true,true);
                return;
            }
        }
        else if(JumpSlam.Phase==EHeQueJumpPhase::Rising)
        {
            if(Age>.08f&&Move->Velocity.Z<=35.f)
            {SetJumpPhase(EHeQueJumpPhase::Falling);LaunchCharacter(FVector(0,0,-HeQueJumpTiming::DiveSpeed),true,true);return;}
            if(Age>2.f){CancelJumpSlam();return;}
        }
        else if(JumpSlam.Phase==EHeQueJumpPhase::Falling)
        {
            // If no floor is reached, keep normal gravity and cancel the move;
            // never snap the capsule down or emit a wave in midair.
            if(Age>3.f){CancelJumpSlam();return;}
        }
        else if(JumpSlam.Phase==EHeQueJumpPhase::Recovery)
        {
            if(!Move->IsMovingOnGround()){CancelJumpSlam();return;}
            if(!bJumpWaveFinished)
            {
                const float T=FMath::Clamp(Age/HeQueJumpTiming::WaveSeconds,0.f,1.f);
                const float Radius=JumpWaveRadius*T;ApplyJumpWave(Radius,false);
                if(!IsJumpSlamming()||IsActorBeingDestroyed())return;
                JumpPreviousRadius=Radius;bJumpWaveFinished=T>=1.f;
            }
            if(Age>=HeQueJumpTiming::Recovery){CancelJumpSlam();return;}
        }
    }
    if(GetNetMode()!=NM_DedicatedServer)PresentJumpSlam(JumpAge());
}
