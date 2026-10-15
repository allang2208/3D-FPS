#include "M66IncineratorMonster.h"
#include "MonsterCombatComponent.h"
#include "MonsterCorpseRagdollComponent.h"
#include "M66CorpseSyncComponent.h"
#include "M66AudioComponent.h"
#include "MonsterAIController.h"
#include "MonsterReactionTiming.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Engine/DamageEvents.h"
#include "Net/UnrealNetwork.h"

double AM66IncineratorMonster::ActionClock() const
{const auto* State=GetWorld()->GetGameState();return State?State->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();}
float AM66IncineratorMonster::ReactionAge() const{return FMath::Max(0.f,float(ActionClock()-Reaction.StartedAt));}
bool AM66IncineratorMonster::IsKnockedDown() const
{return Reaction.Phase==EM66Reaction::Airborne||Reaction.Phase==EM66Reaction::Landing||Reaction.Phase==EM66Reaction::Down||Reaction.Phase==EM66Reaction::GetUp;}
void AM66IncineratorMonster::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{Super::GetLifetimeReplicatedProps(OutLifetimeProps);DOREPLIFETIME(AM66IncineratorMonster,Health);DOREPLIFETIME(AM66IncineratorMonster,MaxHealth);DOREPLIFETIME(AM66IncineratorMonster,Reaction);DOREPLIFETIME(AM66IncineratorMonster,Sweep);}
void AM66IncineratorMonster::SetReaction(EM66Reaction Phase,float AlreadyElapsed)
{Reaction.Phase=Phase;Reaction.StartedAt=ActionClock()-AlreadyElapsed;Reaction.EndsAt=ControlUntil;++Reaction.Serial;OnRep_Reaction();ForceNetUpdate();}
void AM66IncineratorMonster::OnRep_Reaction()
{
    // Shared perception, wandering and pursuit treat a disabled actor tick as
    // an explicit AI pause. Idle and recovered M66s must remain active too.
    SetActorTickEnabled(!bDeathHandoff);
    RefreshPoseTick();
    if(Reaction.Phase==EM66Reaction::Dying)PresentDeath();
}
void AM66IncineratorMonster::InterruptAttack(float Seconds)
{
    if(!HasAuthority()||Dead()||IsActorBeingDestroyed())return;
    StopSweep();
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.1f,Seconds));
    if(IsKnockedDown()){Reaction.EndsAt=ControlUntil;ForceNetUpdate();return;}
    GetCharacterMovement()->StopMovementImmediately();
    const bool Stunned=Combat->StunSecondsRemaining()>0.f;
    if(Stunned&&Reaction.Phase==EM66Reaction::Stunned)
    {Reaction.EndsAt=ControlUntil;ForceNetUpdate();} // Repeated stuns keep the loop phase.
    else {Reaction.Direction=LastHitDirection;SetReaction(Stunned?EM66Reaction::Stunned:EM66Reaction::Hit);}
    Combat->BeginReaction(float(ControlUntil-ActionClock()));
}
void AM66IncineratorMonster::ExtendControl(float Seconds)
{if(HasAuthority()&&!Dead()){ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(0.f,Seconds));Reaction.EndsAt=ControlUntil;ForceNetUpdate();}}
void AM66IncineratorMonster::FinishHitReaction()
{
    if(!HasAuthority()||Dead()||IsKnockedDown()||Reaction.Phase==EM66Reaction::None||ActionClock()+.001<ControlUntil)return;
    ControlUntil=0.;SetReaction(EM66Reaction::None);
}
bool AM66IncineratorMonster::StartLaunch(APawn* Attacker,const FVector& Velocity,float HoldSeconds)
{
    if(!HasAuthority()||Dead()||!Combat->CanReceiveLaunchOrKnockdown())return false;
    StopSweep();
    ControlUntil=FMath::Max(ControlUntil,ActionClock()+FMath::Max(.7f,HoldSeconds));
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->RememberDamage(Attacker);}
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->ClearAccumulatedForces();
    GetCharacterMovement()->SetMovementMode(MOVE_Falling);
    FVector Impulse=Velocity;Impulse.Z=FMath::Max(80.,Impulse.Z);
    SetReaction(EM66Reaction::Airborne);LaunchCharacter(Impulse,true,true);return true;
}
void AM66IncineratorMonster::Landed(const FHitResult& Hit)
{
    Super::Landed(Hit);
    if(HasAuthority()&&!Dead()&&Reaction.Phase==EM66Reaction::Airborne)
    {GetCharacterMovement()->StopMovementImmediately();SetReaction(EM66Reaction::Landing);BodyAudio->Emit(TEXT("Land"),Hit.ImpactPoint);}
}
UAnimSequence* AM66IncineratorMonster::ReactionClip(float& Seconds,bool& Loop) const
{
    Seconds=ReactionAge();Loop=false;UAnimSequence* Clip=nullptr;
    switch(Reaction.Phase)
    {
    case EM66Reaction::Hit:
        if(HitClips.IsValidIndex(Reaction.Direction))Clip=HitClips[Reaction.Direction];
        if(Clip)Seconds=MonsterReactionTiming::StaggerSample(Seconds,FMath::Max(0.f,float(Reaction.EndsAt-ActionClock())),Clip->GetPlayLength(),.14f,.28f);
        break;
    case EM66Reaction::Stunned:Clip=StunClip;Loop=true;break;
    case EM66Reaction::Airborne:
        Clip=AirClip;if(Clip&&Seconds>.3f)Seconds=.3f+FMath::Fmod(Seconds-.3f,FMath::Max(.01f,Clip->GetPlayLength()-.3f));break;
    case EM66Reaction::Landing:Clip=LandClip;break;
    case EM66Reaction::Down:Clip=LandClip;Seconds=Clip?Clip->GetPlayLength():0.f;break;
    case EM66Reaction::GetUp:Clip=GetUpClip;break;
    case EM66Reaction::Dying:
        Clip=DeathClip;
        // A remote peer holds its last live knockdown pose until CorpseSync
        // arrives. With no pose history (late join/LOD reset), use the downed
        // endpoint, never the standing death lead-in.
        if(Reaction.bFromKnockdown&&(bDeathFallback||!HasAuthority())){Clip=LandClip;Seconds=Clip?Clip->GetPlayLength():0.f;}
        else if(!bDeathFallback)Seconds=FMath::Min(Seconds,Reaction.DeathLead);
        break;
    default:break;
    }
    if(Clip)Seconds=Loop?FMath::Fmod(Seconds,FMath::Max(.01f,Clip->GetPlayLength())):FMath::Clamp(Seconds,0.f,Clip->GetPlayLength());
    return Clip;
}
void AM66IncineratorMonster::Tick(float Dt)
{
    Super::Tick(Dt);
    if(Reaction.Phase!=EM66Reaction::None)TickReaction(Dt);
    if(Sweep.Active)TickSweep();
}
void AM66IncineratorMonster::TickReaction(float Dt)
{
    if(Reaction.Phase==EM66Reaction::Dying)
    {
        if(!bDeathPrepared)PresentDeath();if(bDeathHandoff)return;
        if(!HasAuthority())return; // Wait for the authoritative body pose, never run a second ragdoll.
        if(!bDeathFallback)
        {
            if(Reaction.DeathLead>0)CorpseRagdoll->RecordDeathPose(GetMesh(),Dt);
            if(ReactionAge()>=Reaction.DeathLead)
            {
                bDeathHandoff=CorpseRagdoll->Start(GetMesh(),FVector::ZeroVector,Reaction.DeathLead<=0.f);
                if(bDeathHandoff)return;
                bDeathFallback=true;
            }
        }
        if(bDeathFallback&&((Reaction.bFromKnockdown&&ReactionAge()>=.18f)||ReactionAge()>=(DeathClip?DeathClip->GetPlayLength():2.3f)))
        {GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();CorpseRagdoll->FreezeAnimatedPose(GetMesh());bDeathHandoff=true;}
        return;
    }
    if(!HasAuthority()||Dead())return;
    const float Age=ReactionAge();const bool Stunned=Combat->StunSecondsRemaining()>0.f;
    const bool Held=ActionClock()<ControlUntil||Stunned;
    switch(Reaction.Phase)
    {
    case EM66Reaction::Stunned:
        if(!Stunned&&Held)SetReaction(EM66Reaction::Hit,.18f);
        else if(!Held)Combat->FinishReaction();break;
    case EM66Reaction::Hit:if(!Held)Combat->FinishReaction();break;
    case EM66Reaction::Landing:
        if(Age>=(LandClip?LandClip->GetPlayLength():.9f))SetReaction(Held?EM66Reaction::Down:EM66Reaction::GetUp);break;
    case EM66Reaction::Down:if(!Held)SetReaction(EM66Reaction::GetUp);break;
    case EM66Reaction::GetUp:
        if(Age>=(GetUpClip?GetUpClip->GetPlayLength():3.2f))
        {
            if(Held)SetReaction(Stunned?EM66Reaction::Stunned:EM66Reaction::Hit);
            else{ControlUntil=0.;SetReaction(EM66Reaction::None);Combat->FinishReaction();}
        }break;
    default:break;
    }
}
void AM66IncineratorMonster::BeginDeath()
{
    BodyAudio->Emit(TEXT("Death"),GetActorLocation());
    StopSweep();StopBackSmoke();
    Reaction.bFromKnockdown=IsKnockedDown();
    Reaction.DeathLead=GetCharacterMovement()->IsMovingOnGround()&&!Reaction.bFromKnockdown?.9f:0.f;
    SetReaction(EM66Reaction::Dying);CorpseSync->Wake();SetLifeSpan(CorpseSeconds);
}
void AM66IncineratorMonster::PresentDeath()
{
    if(bDeathPrepared)return;bDeathPrepared=true;ControlUntil=0.;SetCanBeDamaged(false);
    if(HasAuthority())CorpseRagdoll->PrepareDeath(GetMesh());
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    Combat->SetComponentTickEnabled(false);
    // An airborne/downed death keeps its current visible pose through handoff.
    if(HasAuthority()&&Reaction.DeathLead<=0.f)
    {bDeathHandoff=CorpseRagdoll->Start(GetMesh(),FVector::ZeroVector,true);bDeathFallback=!bDeathHandoff;}
    GetCharacterMovement()->StopMovementImmediately();GetCharacterMovement()->DisableMovement();
    // The detached corpse now owns its transform; stop character smoothing too.
    GetCharacterMovement()->SetComponentTickEnabled(false);
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if(!bDeathHandoff)GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AM66IncineratorMonster::AcceptServerCorpse()
{
    if(HasAuthority())return;
    PresentDeath();bDeathHandoff=true;SetActorTickEnabled(false);
}
float AM66IncineratorMonster::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!HasAuthority()||Dead()||!CanBeDamaged()||Damage<=0||!FMath::IsFinite(Damage))return 0;
    const float Reduced=CombatFormulaRuntime::MitigateMonster(this,Damage,Event.DamageTypeClass?Event.DamageTypeClass->GetDefaultObject<UDamageType>():nullptr,Causer);
    const float Applied=UDevelopmentTuningSubsystem::ShouldOneHitKill(this,EventInstigator,Causer)?Health:FMath::Min(Health,Reduced);
    if(Applied<=0)return 0;
    FHitResult Hit;FVector Direction;Event.GetBestHitInfo(this,Causer,Hit,Direction);
    if(Direction.IsNearlyZero())Direction=IsValid(Causer)?GetActorLocation()-Causer->GetActorLocation():-GetActorForwardVector();
    const FVector Local=GetActorTransform().InverseTransformVectorNoScale(-Direction);
    LastHitDirection=FMath::Abs(Local.X)>=FMath::Abs(Local.Y)?(Local.X>=0?0:2):(Local.Y>=0?1:3);
    Health=FMath::Max(0.f,Health-Applied);const bool Killed=Health<=0;
    if(Killed)BeginDeath();else BodyAudio->Emit(TEXT("Hurt"),Hit.ImpactPoint.IsNearlyZero()?GetActorLocation():Hit.ImpactPoint);
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);ForceNetUpdate();
    if(Killed){ColdSteelSkills::NotifyKillByOwner(GetGameInstance(),EventInstigator,this);ColdSteelSkills::AwardKillByOwner(GetGameInstance(),EventInstigator,this,ExperienceReward);}
    else if(!Dead())Combat->ReceiveHit(Applied,EventInstigator?EventInstigator->GetPawn().Get():Cast<APawn>(Causer),MonsterToughness::FormOf(Event.DamageTypeClass));
    return Applied;
}
