#include "RootCrownRigPreview.h"
#include "RootCrownNeedleProjectile.h"
#include "RootCrownHitComponent.h"
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
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/DamageEvents.h"
#include "Sound/SoundBase.h"

bool ARootCrownRigPreview::IsKnockedDown() const
{
    return Reaction.Phase==ERootCrownReaction::Airborne||Reaction.Phase==ERootCrownReaction::Landing
        ||Reaction.Phase==ERootCrownReaction::Down||Reaction.Phase==ERootCrownReaction::GetUp;
}
float ARootCrownRigPreview::ReactionAge() const{return FMath::Max(0.f,float(ActionClock()-Reaction.StartedAt));}
void ARootCrownRigPreview::SetReaction(ERootCrownReaction Phase)
{
    Reaction.Phase=Phase;Reaction.StartedAt=ActionClock();Reaction.EndsAt=ControlUntil;++Reaction.Serial;
    OnRep_Reaction();ForceNetUpdate();
}
void ARootCrownRigPreview::OnRep_Reaction()
{
    if(Reaction.Phase==ERootCrownReaction::Dying)PresentDeath();
    RefreshPoseTick();
    if(Reaction.Phase!=ERootCrownReaction::None){SlashVoice->Stop();UpdateSlashArc();}
    if(PresentedReactionSerial==Reaction.Serial)return;
    PresentedReactionSerial=Reaction.Serial;
    if(Reaction.Phase==ERootCrownReaction::None)OnRep_Slash();
    if(GetNetMode()==NM_DedicatedServer)return;
    ReactionVoice->Stop();
    USoundBase* Sound=Reaction.Phase==ERootCrownReaction::Dying?DeathSound.Get():
        Reaction.Phase==ERootCrownReaction::Landing?LandSound.Get():
        Reaction.Phase==ERootCrownReaction::Hit||Reaction.Phase==ERootCrownReaction::Stunned?HitSound.Get():nullptr;
    if(Sound&&ReactionAge()<Sound->GetDuration())
    {ReactionVoice->SetSound(Sound);ReactionVoice->Play(ReactionAge());}
}
void ARootCrownRigPreview::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead()||IsActorBeingDestroyed())return;
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.1f,Seconds));
    FinishSlash();
    if(IsKnockedDown()){Reaction.EndsAt=ControlUntil;ForceNetUpdate();return;}
    GetCharacterMovement()->StopMovementImmediately();
    Reaction.Direction=LastHitDirection;
    SetReaction(Combat->StunSecondsRemaining()>0.f?ERootCrownReaction::Stunned:ERootCrownReaction::Hit);
    Combat->BeginReaction(float(ControlUntil-ActionClock()));
}
void ARootCrownRigPreview::FinishHitReaction()
{
    if(!HasAuthority()||Dead()||IsKnockedDown()||Reaction.Phase==ERootCrownReaction::None||ActionClock()+.001<ControlUntil)return;
    ControlUntil=0.;SetReaction(ERootCrownReaction::None);
}
void ARootCrownRigPreview::ExtendControl(float Seconds)
{
    if(!HasAuthority()||Dead())return;
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(0.f,Seconds));Reaction.EndsAt=ControlUntil;ForceNetUpdate();
}
bool ARootCrownRigPreview::StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds)
{
    if(!HasAuthority()||Dead()||IsActorBeingDestroyed()||!Combat->CanReceiveLaunchOrKnockdown())return false;
    FinishSlash();
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.7f,HoldSeconds));
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->ClearAccumulatedForces();
    GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    FVector Impulse=Velocity;Impulse.Z=FMath::Max(80.,Impulse.Z);
    SetReaction(ERootCrownReaction::Airborne);LaunchCharacter(Impulse,true,true);return true;
}
void ARootCrownRigPreview::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if(HasAuthority()&&!Dead()&&Reaction.Phase==ERootCrownReaction::Airborne)
    {
        GetCharacterMovement()->StopMovementImmediately();SetReaction(ERootCrownReaction::Landing);
    }
}
UAnimSequence* ARootCrownRigPreview::ReactionClip(float& Seconds,bool& Loop) const
{
    Seconds=ReactionAge();Loop=false;
    UAnimSequence* Clip=nullptr;
    switch(Reaction.Phase)
    {
    case ERootCrownReaction::Hit:
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
    case ERootCrownReaction::Stunned:Clip=StunClip;Loop=true;break;
    case ERootCrownReaction::Airborne:
        Clip=AirClip;
        if(Clip&&Seconds>.25f)Seconds=.25f+FMath::Fmod(Seconds-.25f,FMath::Max(.01f,Clip->GetPlayLength()-.25f));
        break;
    case ERootCrownReaction::Landing:Clip=LandClip;break;
    case ERootCrownReaction::Down:Clip=LandClip;Seconds=Clip?Clip->GetPlayLength():0.f;break;
    case ERootCrownReaction::GetUp:Clip=GetUpClip;break;
    case ERootCrownReaction::Dying:
        Clip=DeathClip;
        if(!bDeathFallback)Seconds=FMath::Min(Seconds,Reaction.DeathLead);
        break;
    default:break;
    }
    if(Clip)Seconds=Loop?FMath::Fmod(Seconds,FMath::Max(.01f,Clip->GetPlayLength())):FMath::Clamp(Seconds,0.f,Clip->GetPlayLength());
    return Clip;
}
void ARootCrownRigPreview::TickReaction(float Dt)
{
    if(Dead())
    {
        // Health and the reaction record may arrive in either order on a client.
        if(Reaction.Phase!=ERootCrownReaction::Dying)return;
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
    case ERootCrownReaction::Hit:case ERootCrownReaction::Stunned:
        if(!Held)Combat->FinishReaction();break;
    case ERootCrownReaction::Landing:
        if(Age>=(LandClip?LandClip->GetPlayLength():.65f))SetReaction(Held?ERootCrownReaction::Down:ERootCrownReaction::GetUp);
        break;
    case ERootCrownReaction::Down:if(!Held)SetReaction(ERootCrownReaction::GetUp);break;
    case ERootCrownReaction::GetUp:
        if(Age>=(GetUpClip?GetUpClip->GetPlayLength():1.3f))
        {
            if(Held)SetReaction(ERootCrownReaction::Stunned);
            else {ControlUntil=0.;SetReaction(ERootCrownReaction::None);Combat->FinishReaction();}
        }
        break;
    default:break;
    }
}
void ARootCrownRigPreview::CancelFlyingNeedles()
{
    if(HasAuthority())for(const auto& Weak:FlyingNeedles)if(auto* Needle=Weak.Get())Needle->Destroy();
    FlyingNeedles.Reset();
}
void ARootCrownRigPreview::PresentDeath()
{
    if(bDeathPrepared)return;
    bDeathPrepared=true;ControlUntil=0.;
    CorpseRagdoll->PrepareDeath(GetMesh());
    SlashClock.Active=false;Target.Reset();SlashVictims.Reset();
    CancelRootField();CancelFlyingNeedles();UpdateSlashArc();
    SlashVoice->Stop();ContactVoice->Stop();
    if(TensionMaterial)TensionMaterial->SetScalarParameterValue(TEXT("CrownTension"),0.f);
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    Combat->SetComponentTickEnabled(false);
    HitDetection->SetComponentTickEnabled(false);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(Reaction.DeathLead<=0.f)bDeathHandoff=CorpseRagdoll->TryStartSoftDeath(GetMesh());
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void ARootCrownRigPreview::BeginDeath()
{
    Reaction.DeathLead=GetCharacterMovement()->IsMovingOnGround()?.65f:0.f;
    SetReaction(ERootCrownReaction::Dying);SetLifeSpan(CorpseSeconds);
}
float ARootCrownRigPreview::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
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

void ARootCrownRigPreview::PresentGunContact(const FHitResult& Hit,const FVector& Direction,float Damage)
{
    if(!HasAuthority()||Dead()||ActionClock()-LastGunContactAt<.07)return;
    LastGunContactAt=ActionClock();
    MulticastGunContact(Hit.ImpactPoint,Direction.GetSafeNormal(),Hit.BoneName,Damage,LastGunContactAt);
}
void ARootCrownRigPreview::MulticastGunContact_Implementation(FVector_NetQuantize Location,FVector_NetQuantizeNormal Direction,FName Bone,float Damage,double At)
{
    if(Dead()||GetNetMode()==NM_DedicatedServer||ActionClock()-At>.35)return;
    FHitResult Hit;Hit.ImpactPoint=Hit.Location=Location;Hit.BoneName=Bone;
    Hit.Component=GetMesh();Hit.HitObjectHandle=FActorInstanceHandle(this);
    if(auto* Body=Cast<UMonsterIdleBreathingMeshComponent>(GetMesh()))Body->AddGunHitFeedback(Hit,Direction,Damage);
}
