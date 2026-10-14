#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "RootCrownRootField.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "FleshHandMonster.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

double ARootCrownRigPreview::ActionClock() const
{
    const auto* GS=GetWorld()->GetGameState();
    return GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
}
float ARootCrownRigPreview::SlashAge() const {return FMath::Max(0.f,float(ActionClock()-SlashClock.StartedAt));}
void ARootCrownRigPreview::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ARootCrownRigPreview,SlashClock);
    DOREPLIFETIME(ARootCrownRigPreview,Health);DOREPLIFETIME(ARootCrownRigPreview,Reaction);
    DOREPLIFETIME(ARootCrownRigPreview,MaxHealth);DOREPLIFETIME(ARootCrownRigPreview,Level);DOREPLIFETIME(ARootCrownRigPreview,Rank);
}
bool ARootCrownRigPreview::CanSeeTarget(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Block;
    return !GetWorld()->LineTraceSingleByChannel(Block,GetNavAgentLocation()+FVector(0,0,100),Victim->GetActorLocation(),ECC_Visibility,Query)
        || (Block.GetActor() && Block.GetActor()->IsA<AFPSIceWall>());
}
bool ARootCrownRigPreview::CanSlash(APawn* Victim) const
{
    if(Busy() || !SlashClip || SlashFrames.Num()<2 || !GetCharacterMovement()->IsMovingOnGround()
        || ActionClock()<NextSlashAt || !IsValid(Victim) || !Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    return Delta.Size2D()<=SlashTriggerRange && FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<=120.f
        && FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(45.f))
        && CanSeeTarget(Victim) && SlashCanReach(Victim);
}
bool ARootCrownRigPreview::CanAttack(APawn* Victim) const {return CanSlash(Victim)||CanRoots(Victim)||CanNeedle(Victim);}
bool ARootCrownRigPreview::StartAttack(APawn* Victim)
{
    if(!HasAuthority() || !CanAttack(Victim))return false;
    const bool Slash=CanSlash(Victim);
    const bool Roots=!Slash&&CanRoots(Victim)&&PrepareRootField(Victim);
    const bool Needles=!Slash&&!Roots&&CanNeedle(Victim);
    if(!Slash&&!Roots&&!Needles)return false;
    Target=Victim;SlashVictims.Reset();bContactSoundPlayed=false;NextContactFrame=1;
    while(NextContactFrame<SlashFrames.Num() && SlashFrames[NextContactFrame].Time<RootCrownSlashTiming::ContactStart)++NextContactFrame;
    SlashClock.Active=true;++SlashClock.Serial;SlashClock.StartedAt=ActionClock();SlashClock.OpeningYaw=GetActorRotation().Yaw;
    SlashClock.bNeedles=Needles;SlashClock.bRoots=Roots;
    if(Roots)NextRootsAt=SlashClock.StartedAt+FMath::Max(RootCooldown,RootCrownRootTiming::End);
    else if(Needles)
    {
        NextNeedleAt=SlashClock.StartedAt+FMath::Max(NeedleCooldown,RootCrownNeedleTiming::End);
        NextNeedleWave=0;NeedleSalvo=SlashClock.Serial;LockedNeedleAim=FVector::ZeroVector;
        for(auto& Victims:NeedleVictims)Victims.Reset();
    }
    else NextSlashAt=SlashClock.StartedAt+FMath::Max(SlashCooldown,RootCrownSlashTiming::End);
    GetCharacterMovement()->StopMovementImmediately();
    OnRep_Slash();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
bool ARootCrownRigPreview::DesiredFacingYaw(float& Yaw) const
{
    if(Controlled() || !Target.IsValid() || !CanSeeTarget(Target.Get()))return false;
    if(IsAttacking())
    {
        if(IsRootEnclosing())return false; // Three feet and the announced ground layout are planted.
        if(SlashAge()>=(IsNeedleFiring()?RootCrownNeedleTiming::FirstShot:RootCrownSlashTiming::AimLock))return false;
        const float Desired=(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw;
        Yaw=SlashClock.OpeningYaw+FMath::Clamp(FMath::FindDeltaAngleDegrees(SlashClock.OpeningYaw,Desired),-20.f,20.f);
        return true;
    }
    if(GetHorizontalDistanceTo(Target.Get())>NeedleMaxRange)return false;
    Yaw=(Target->GetActorLocation()-GetActorLocation()).Rotation().Yaw;return true;
}
void ARootCrownRigPreview::OnRep_Slash()
{
    // Server contact is authored offline; live grounding still updates the
    // root used to place that same path on the current floor/slope.
    RefreshPoseTick();
    if(GetNetMode()==NM_DedicatedServer)return;
    UpdateSlashArc();
    SlashVoice->Stop();
    USoundBase* Cue=IsRootEnclosing()?RootGestureSound:IsNeedleFiring()?NeedleGestureSound:SlashGestureSound;
    const float Duration=IsRootEnclosing()?RootCrownRootTiming::End:IsNeedleFiring()?RootCrownNeedleTiming::End:RootCrownSlashTiming::End;
    if(IsAttacking() && Cue && SlashAge()<Duration)
    {
        SlashVoice->SetSound(Cue);SlashVoice->SetPitchMultiplier(1.f);SlashVoice->Play(SlashAge());
    }
}
void ARootCrownRigPreview::FinishSlash()
{
    if(!HasAuthority() || !SlashClock.Active)return;
    if(SlashClock.bRoots)if(auto* Field=RootField.Get())Field->FinishCast();
    SlashClock.Active=false;SlashVictims.Reset();OnRep_Slash();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void ARootCrownRigPreview::Tick(float Dt)
{
    Super::Tick(Dt);
    TickReaction(Dt);
    if(Dead())return;
    UpdateSlashArc();
    if(TensionMaterial)
    {
        const float Age=SlashAge();
        const float Tight=IsRootEnclosing()?.65f*FMath::SmoothStep(.15f,1.5f,Age)*(1.f-FMath::SmoothStep(2.7f,3.6f,Age)):
            IsNeedleFiring()?FMath::SmoothStep(.2f,1.15f,Age)*(1.f-FMath::SmoothStep(2.f,2.3f,Age)):
            IsSlashing()?FMath::SmoothStep(.15f,.90f,Age)*(1.f-FMath::SmoothStep(1.f,1.20f,Age)):0.f;
        TensionMaterial->SetScalarParameterValue(TEXT("CrownTension"),Tight);
    }
    if(!HasAuthority())return;
    if(Controlled())
    {
        FinishSlash();
        return;
    }
    if(!IsAttacking())return;
    const auto* AI=Cast<AMonsterAIController>(GetController());
    if(!AI || !AI->bDecisionEnabled || !GetCharacterMovement()->IsMovingOnGround()) {FinishSlash();return;}
    const float Age=SlashAge();
    if(IsRootEnclosing()){if(Age>=RootCrownRootTiming::End)FinishSlash();return;}
    if(IsNeedleFiring()){TickNeedles(Age);return;}
    while(NextContactFrame<SlashFrames.Num() && SlashFrames[NextContactFrame].Time<=FMath::Min(Age,RootCrownSlashTiming::ContactEnd)+.0001f)
    {
        SlashContact(NextContactFrame++);
        // Guard/parry callbacks can synchronously cancel the remaining arc.
        if(!IsSlashing() || Controlled() || IsActorBeingDestroyed())return;
    }
    if(Age>=RootCrownSlashTiming::End)FinishSlash();
}
void ARootCrownRigPreview::SlashContact(int32 Index)
{
    if(!HasAuthority() || !IsSlashing() || Controlled() || Index<=0 || !SlashFrames.IsValidIndex(Index))return;
    const auto& A=SlashFrames[Index-1];const auto& B=SlashFrames[Index];
    const int32 Count=FMath::Min(A.Points.Num(),B.Points.Num());
    const FTransform GroundedRoot=GetMesh()->GetSocketTransform(TEXT("Root"));
    auto World=[&](const FVector& P){return SlashPointWorld(P,true,GroundedRoot);};
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownCrownEdge),false,this);
    auto Sweep=[&](const FVector& From,const FVector& To)
    {
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,Objects,FCollisionShape::MakeSphere(SlashHitRadius),Query);
        for(const auto& Hit:Hits)
        {
            if(!IsSlashing() || Controlled() || IsActorBeingDestroyed())return;
            AActor* Victim=Hit.GetActor();APawn* Pawn=Cast<APawn>(Victim);
            const bool Player=Pawn && Pawn->IsPlayerControlled() && Hit.GetComponent()==Pawn->GetRootComponent();
            if(!IsValid(Victim) || (!Player&&!Victim->IsA<AFPSIceWall>()) || SlashVictims.Contains(Victim))continue;
            const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
            if(Delta.Size2D()>SlashTriggerRange+70.f*SlashReachScale || FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<FMath::Cos(FMath::DegreesToRadians(50.f)))continue;
            auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
            if(Vitals && (Vitals->IsDead()||Vitals->IsInvulnerable()))continue;
            FHitResult Block;
            const FVector Sight=GetNavAgentLocation()+FVector(0,0,100);
            if(GetWorld()->LineTraceSingleByChannel(Block,Sight,Hit.ImpactPoint,ECC_Visibility,Query) && Block.GetActor()!=Victim)continue;
            SlashVictims.Add(Victim);
            const float Before=Vitals?Vitals->Health:0.f;
            const FVector Direction=(To-From).GetSafeNormal();
            UGameplayStatics::ApplyPointDamage(Victim,SlashDamage,Direction.IsNearlyZero()?GetActorForwardVector():Direction,Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
            if(!IsSlashing() || Controlled() || IsActorBeingDestroyed())return;
            if(Player && Vitals && Vitals->Health<Before)
            {
                if(!bContactSoundPlayed){bContactSoundPlayed=true;MulticastSlashContact(Hit.ImpactPoint,ActionClock());}
                if(!Vitals->IsDead())UFleshHandPushComponent::Apply(Cast<ACharacter>(Victim),Delta.GetSafeNormal2D(),SlashKnockback);
            }
        }
    };
    for(int32 I=0;I<Count && IsSlashing() && !Controlled();++I)
    {
        Sweep(World(A.Points[I]),World(B.Points[I]));
        if(I>0 && IsSlashing() && !Controlled())Sweep(World(B.Points[I-1]),World(B.Points[I]));
        if(IsSlashing() && !Controlled())Sweep(SlashPointWorld(B.Points[I],false,GroundedRoot),World(B.Points[I]));
    }
}
FVector ARootCrownRigPreview::SlashPointWorld(const FVector& Point,bool Expanded,const FTransform& GroundedRoot) const
{
    FVector World=GroundedRoot.TransformPosition(ReferenceRoot.InverseTransformPosition(Point));
    if(Expanded)
    {
        const FVector Delta=World-GetActorLocation();
        World=GetActorLocation()+FVector(Delta.X*SlashReachScale,Delta.Y*SlashReachScale,Delta.Z);
    }
    return World;
}
bool ARootCrownRigPreview::SlashCanReach(const APawn* Victim) const
{
    float Radius=0.f,Half=0.f;Victim->GetSimpleCollisionCylinder(Radius,Half);
    const FVector Center=Victim->GetActorLocation(),Extent(0,0,FMath::Max(0.f,Half-Radius));
    const FTransform GroundedRoot=GetMesh()->GetSocketTransform(TEXT("Root"));
    auto Touch=[&](const FVector& A,const FVector& B)
    {
        FVector OnRim,OnBody;FMath::SegmentDistToSegmentSafe(A,B,Center-Extent,Center+Extent,OnRim,OnBody);
        return FVector::DistSquared(OnRim,OnBody)<=FMath::Square(Radius+SlashHitRadius);
    };
    // The starting gate uses the same widened path. A nominal 8 m limit must
    // not make the AI swing at a height/direction its actual volume cannot hit.
    for(int32 Frame=1;Frame<SlashFrames.Num();++Frame)
    {
        const auto& A=SlashFrames[Frame-1];const auto& B=SlashFrames[Frame];
        if(B.Time<RootCrownSlashTiming::ContactStart || B.Time>RootCrownSlashTiming::ContactEnd)continue;
        for(int32 I=0;I<FMath::Min(A.Points.Num(),B.Points.Num());++I)
        {
            const FVector P=SlashPointWorld(B.Points[I],true,GroundedRoot);
            if(Touch(SlashPointWorld(A.Points[I],true,GroundedRoot),P)||Touch(SlashPointWorld(B.Points[I],false,GroundedRoot),P)||
                (I>0&&Touch(SlashPointWorld(B.Points[I-1],true,GroundedRoot),P)))return true;
        }
    }
    return false;
}
void ARootCrownRigPreview::MulticastSlashContact_Implementation(FVector_NetQuantize Location,double At)
{
    const float Age=FMath::Max(0.f,float(ActionClock()-At));
    if(GetNetMode()==NM_DedicatedServer || !SlashContactSound || Age>.4f)return;
    ContactVoice->SetWorldLocation(Location);ContactVoice->SetSound(SlashContactSound);ContactVoice->Play(Age);
}
void ARootCrownRigPreview::EndPlay(const EEndPlayReason::Type Reason)
{
    CancelRootField();
    CancelFlyingNeedles();
    SlashClock.Active=false;SlashVictims.Reset();Target.Reset();
    SlashVoice->Stop();ContactVoice->Stop();ReactionVoice->Stop();Super::EndPlay(Reason);
}
