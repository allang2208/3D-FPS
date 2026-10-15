#include "HeQueMonster.h"
#include "MonsterIdleBreathingMeshComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "MonsterAIController.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/DamageEvents.h"

bool AHeQueMonster::IsKnockedDown() const
{
    return Reaction.Phase==EHeQueReaction::Airborne||Reaction.Phase==EHeQueReaction::Landing
        ||Reaction.Phase==EHeQueReaction::Down||Reaction.Phase==EHeQueReaction::GetUp;
}
float AHeQueMonster::ReactionAge() const{return FMath::Max(0.f,float(ActionClock()-Reaction.StartedAt));}
void AHeQueMonster::SetReaction(EHeQueReaction Phase)
{
    if(Phase!=EHeQueReaction::None)CancelAttack();
    Reaction.Phase=Phase;Reaction.StartedAt=ActionClock();Reaction.EndsAt=ControlUntil;++Reaction.Serial;
    OnRep_Reaction();ForceNetUpdate();
}
void AHeQueMonster::OnRep_Reaction()
{
    if(Reaction.Phase==EHeQueReaction::Dying)PresentDeath();
    // Knockback velocity must not turn the whole creature to face its travel.
    // Both authority and clients keep the struck facing through the recovery.
    if(!Dead())GetCharacterMovement()->bOrientRotationToMovement=!IsKnockedDown();
    RefreshPoseTick();
}
void AHeQueMonster::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead()||IsActorBeingDestroyed())return;
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.1f,Seconds));
    if(IsKnockedDown()){Reaction.EndsAt=ControlUntil;ForceNetUpdate();return;}
    GetCharacterMovement()->StopMovementImmediately();
    Reaction.Direction=LastHitDirection;
    SetReaction(Combat->StunSecondsRemaining()>0.f?EHeQueReaction::Stunned:EHeQueReaction::Hit);
    Combat->BeginReaction(float(ControlUntil-ActionClock()));
}
void AHeQueMonster::FinishHitReaction()
{
    if(!HasAuthority()||Dead()||IsKnockedDown()||Reaction.Phase==EHeQueReaction::None||ActionClock()+.001<ControlUntil)return;
    ControlUntil=0.;SetReaction(EHeQueReaction::None);
}
void AHeQueMonster::ExtendControl(float Seconds)
{
    if(!HasAuthority()||Dead())return;
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(0.f,Seconds));Reaction.EndsAt=ControlUntil;ForceNetUpdate();
}
bool AHeQueMonster::StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds)
{
    if(!HasAuthority()||Dead()||IsActorBeingDestroyed()||!Combat->CanReceiveLaunchOrKnockdown())return false;
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.7f,HoldSeconds));
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->ClearAccumulatedForces();
    GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    FVector Impulse=Velocity;Impulse.Z=FMath::Max(80.,Impulse.Z);
    SetReaction(EHeQueReaction::Airborne);LaunchCharacter(Impulse,true,true);return true;
}
void AHeQueMonster::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if(HasAuthority()&&IsJumpSlamming()&&(JumpSlam.Phase==EHeQueJumpPhase::Rising||JumpSlam.Phase==EHeQueJumpPhase::Falling))
    {LandJumpSlam(Hit);return;}
    if(HasAuthority()&&!Dead()&&Reaction.Phase==EHeQueReaction::Airborne)
    {
        GetCharacterMovement()->StopMovementImmediately();SetReaction(EHeQueReaction::Landing);
    }
}
UAnimSequence* AHeQueMonster::ReactionClip(float& Seconds,bool& Loop) const
{
    Seconds=ReactionAge();Loop=false;
    UAnimSequence* Clip=nullptr;
    switch(Reaction.Phase)
    {
    case EHeQueReaction::Hit:
        if(HitClips.IsValidIndex(Reaction.Direction))Clip=HitClips[Reaction.Direction];
        if(Clip)
        {
            const double End=Reaction.EndsAt;
            const float Duration=FMath::Max(.1f,float(End-Reaction.StartedAt));
            if(Duration<.4f)Seconds=Seconds/Duration*Clip->GetPlayLength();
            else if(Seconds<.12f)Seconds=Seconds/.12f*.18f;
            else if(ActionClock()<End-.25)Seconds=.18f;
            else Seconds=FMath::Lerp(.18f,Clip->GetPlayLength(),1.f-float(End-ActionClock())/.25f);
        }
        break;
    case EHeQueReaction::Stunned:Clip=StunClip;Loop=true;break;
    case EHeQueReaction::Airborne:
        Clip=AirClip;
        if(Clip&&Seconds>.36f)
        {
            // Initial recoil uses real elapsed time. The remaining authored
            // fold/brace follows actual descent instead of freezing midair or
            // cycling back to a standing pose during a longer launch.
            const float Descent=FMath::Clamp(float(-GetVelocity().Z)/650.f,0.f,1.f);
            const float Target=FMath::Lerp(.36f,Clip->GetPlayLength(),Descent);
            Seconds=FMath::Lerp(.36f,Target,FMath::SmoothStep(.36f,.58f,Seconds));
        }
        break;
    case EHeQueReaction::Landing:Clip=LandClip;break;
    case EHeQueReaction::Down:Clip=LandClip;Seconds=Clip?Clip->GetPlayLength():0.f;break;
    case EHeQueReaction::GetUp:Clip=GetUpClip;break;
    case EHeQueReaction::Dying:
        Clip=DeathClip;
        if(!bDeathFallback)Seconds=FMath::Min(Seconds,Reaction.DeathLead);
        break;
    default:break;
    }
    if(Clip)Seconds=Loop?FMath::Fmod(Seconds,FMath::Max(.01f,Clip->GetPlayLength())):FMath::Clamp(Seconds,0.f,Clip->GetPlayLength());
    return Clip;
}
void AHeQueMonster::TickReaction(float Dt)
{
    if(Dead())
    {
        // Health and the reaction record may arrive in either order on a client.
        if(Reaction.Phase!=EHeQueReaction::Dying)return;
        if(!bDeathPrepared)PresentDeath();
        if(bDeathHandoff)return;
        if(ReactionAge()>=Reaction.DeathLead&&!bDeathFallback)
        {
            // Late replicated deaths sample the same handoff instant, instead
            // of jumping to the last frame of a collapse before soft physics.
            if(Reaction.DeathLead>0.f){GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();}
            bDeathHandoff=CorpseRagdoll->TryStartSoftDeath(GetMesh());
            if(bDeathHandoff)return;
            bDeathFallback=true;
        }
        if(bDeathFallback&&ReactionAge()>=(DeathClip?DeathClip->GetPlayLength():1.6f))
        {CorpseRagdoll->FreezeAnimatedPose(GetMesh());bDeathHandoff=true;}
        return;
    }
    if(!HasAuthority())return;
    const float Age=ReactionAge();
    const bool Held=ActionClock()<ControlUntil||Combat->StunSecondsRemaining()>0.f;
    switch(Reaction.Phase)
    {
    case EHeQueReaction::Hit:case EHeQueReaction::Stunned:
        if(!Held)Combat->FinishReaction();break;
    case EHeQueReaction::Airborne:
        // Movement can resolve an immediately blocked launch without issuing
        // another Landed callback. Only a real walking floor allows recovery.
        if(Age>.12f&&GetCharacterMovement()->IsMovingOnGround())SetReaction(EHeQueReaction::Landing);
        break;
    case EHeQueReaction::Landing:
        if(GetCharacterMovement()->IsFalling())SetReaction(EHeQueReaction::Airborne);
        else if(Age>=(LandClip?LandClip->GetPlayLength():.95f))SetReaction(EHeQueReaction::Down);
        break;
    case EHeQueReaction::Down:
        if(GetCharacterMovement()->IsFalling())SetReaction(EHeQueReaction::Airborne);
        else if(Age>=.25f&&!Held&&GetCharacterMovement()->IsMovingOnGround())SetReaction(EHeQueReaction::GetUp);
        break;
    case EHeQueReaction::GetUp:
        if(GetCharacterMovement()->IsFalling()){SetReaction(EHeQueReaction::Airborne);break;}
        if(Age>=(GetUpClip?GetUpClip->GetPlayLength():3.f))
        {
            if(Held)SetReaction(EHeQueReaction::Stunned);
            else {ControlUntil=0.;SetReaction(EHeQueReaction::None);Combat->FinishReaction();}
        }
        break;
    default:break;
    }
}

void AHeQueMonster::PresentDeath()
{
    if(bDeathPrepared)return;
    bDeathPrepared=true;ControlUntil=0.;SetCanBeDamaged(false);
    // Death can replicate before attack cancellation. Remove the local spell
    // before the corpse handoff disables actor ticking on this client.
    if(Psychic.Active){Psychic.Active=false;OnRep_Psychic();}
    if(JumpSlam.Phase!=EHeQueJumpPhase::None){JumpSlam.Phase=EHeQueJumpPhase::None;OnRep_JumpSlam();}
    CorpseRagdoll->PrepareDeath(GetMesh());
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    Combat->SetComponentTickEnabled(false);
    if(Reaction.DeathLead<=0.f)bDeathHandoff=CorpseRagdoll->TryStartSoftDeath(GetMesh());
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->DisableMovement();
    GetCharacterMovement()->SetComponentTickEnabled(false);
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AHeQueMonster::BeginDeath()
{
    // Hand the visible pose directly to the continuous corpse. Sampling a
    // separate forward-collapse clip first discards an ongoing kick/recoil.
    // The full death clip remains the fallback when no soft binding is available.
    Reaction.DeathLead=0.f;
    SetReaction(EHeQueReaction::Dying);SetLifeSpan(CorpseSeconds);
}
float AHeQueMonster::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||Dead()||!CanBeDamaged()||Damage<=0.f||!FMath::IsFinite(Damage))return 0.f;
    const float Reduced=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:FMath::Min(Health,Reduced);
    if(Applied<=0.f)return 0.f;
    FHitResult Hit;FVector Direction=FVector::ZeroVector;Event.GetBestHitInfo(this,Causer,Hit,Direction);
    if(Direction.IsNearlyZero())Direction=IsValid(Causer)?GetActorLocation()-Causer->GetActorLocation():-GetActorForwardVector();
    const FVector Local=GetActorTransform().InverseTransformVectorNoScale(-Direction);
    LastHitDirection=FMath::Abs(Local.X)>=FMath::Abs(Local.Y)?(Local.X>=0?0:2):(Local.Y>=0?1:3);
    Health=FMath::Max(0.f,Health-Applied);
    const bool Killed=Health<=0.f;
    if(Killed)BeginDeath();
    // Commit death before external callbacks; a nested hit must not award this kill twice.
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);ForceNetUpdate();
    if(Killed)
    {
        ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);
        ColdSteelSkills::AwardKillByOwner(GetGameInstance(),EventInstigator,this,ExperienceReward);
    }
    else if(!Dead())Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
