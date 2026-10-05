#include "SpiralPillarM14.h"
#include "M14MucusProjectile.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "../Skills/IceWallCombat.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

namespace
{
FVector M14SpitIntercept(const FVector& Origin,const FVector& Position,const FVector& Velocity,
    float LaunchDelay,float Speed,float Range)
{
    const FVector AtLaunch=Position+Velocity*FMath::Max(0.f,LaunchDelay);
    const FVector R=AtLaunch-Origin;
    const double A=Velocity.SizeSquared()-FMath::Square(double(Speed));
    const double B=2.*FVector::DotProduct(R,Velocity),C=R.SizeSquared();
    const double MaxTime=Range/FMath::Max(1.f,Speed);
    double Time=FMath::Min(MaxTime,R.Size()/FMath::Max(1.f,Speed));
    if(FMath::Abs(A)<1.e-3)
    {
        if(B<-1.e-3)Time=-C/B;
    }
    else
    {
        const double Discriminant=B*B-4.*A*C;
        if(Discriminant>=0.)
        {
            const double Root=FMath::Sqrt(Discriminant);
            const double T0=(-B-Root)/(2.*A),T1=(-B+Root)/(2.*A);
            if(T0>0.&&T1>0.)Time=FMath::Min(T0,T1);
            else if(T0>0.)Time=T0;
            else if(T1>0.)Time=T1;
        }
    }
    return AtLaunch+Velocity*FMath::Clamp(Time,0.,MaxTime);
}
}

UAnimSequence* ASpiralPillarM14::AttackClip(EM14State Attack) const
{
    if(Attack==EM14State::Spit)return SpitClip;
    if(Attack==EM14State::Whirlwind)return WhirlwindClip;
    if(Attack==EM14State::TrunkSlam)return TrunkSlamClip;
    if(Attack==EM14State::SweepLeft||Attack==EM14State::SweepRight)
    {
        const bool Positive=(Attack==EM14State::SweepRight)==bPositiveXIsRight;
        return Positive?SweepPositiveClip.Get():SweepNegativeClip.Get();
    }
    return BiteClip;
}

EM14State ASpiralPillarM14::ChooseAttack(APawn* Victim) const
{
    if(!IsValid(Victim)||Busy()||CooldownLeft>0.f||!GetCharacterMovement()->IsMovingOnGround())return EM14State::Idle;
    if(const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();Vitals&&Vitals->IsDead())return EM14State::Idle;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    const float Distance=Delta.Size2D();
    const float Angle=FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw,Delta.Rotation().Yaw);
    const float AbsAngle=FMath::Abs(Angle);
    const bool SameFloor=FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<=55.f;
    if(WhirlwindClip&&WhirlwindCooldownLeft<=0.f&&SameFloor)
    {
        if(Distance<=WhirlwindTriggerRange&&
            (CanSee(Victim)||IceWallCombat::BlockingWall(this,Victim,WhirlwindTriggerRange)))return EM14State::Whirlwind;
        // Close the remaining gap for the ready spin instead of repeatedly
        // stopping at bite/slam range. Other attacks resume during its cooldown.
        if(Distance<=FMath::Max(WhirlwindTriggerRange,SlamTriggerRange+35.f)&&CanSee(Victim))return EM14State::Idle;
    }
    // The rejected root sweeps are no longer selected. A forward trunk drop
    // has a visible windup and holds its launch heading throughout recovery.
    if(Distance>=SlamMinRange&&Distance<=SlamTriggerRange&&AbsAngle<20.f&&SlamCooldownLeft<=0.f&&TrunkSlamClip&&
        FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<=55.f)
    {
        if(CanSee(Victim)||IceWallCombat::BlockingWall(this,Victim,SlamTriggerRange))return EM14State::TrunkSlam;
    }
    if(Distance<=BiteTriggerRange&&AbsAngle<25.f&&BiteClip&&
        (CanSee(Victim)||IceWallCombat::BlockingWall(this,Victim,BiteTriggerRange)))return EM14State::Bite;
    if(Distance>=SpitMinRange&&Distance<=SpitMaxRange&&AbsAngle<25.f&&SpitCooldownLeft<=0.f&&
        SpitClip&&MucusMaterial&&MucusCoreMaterial&&CanSee(Victim))return EM14State::Spit;
    return EM14State::Idle;
}

float ASpiralPillarM14::AttackStopRange() const
{
    // Hold at range only while a spit is ready and has a clear launch line.
    // Otherwise the same BT pursuit task closes back to the existing bite stop.
    if(Target.IsValid()&&SpitClip&&MucusMaterial&&MucusCoreMaterial&&SpitCooldownLeft<=0.f&&CooldownLeft<=0.f&&
        FVector::DistSquared2D(GetActorLocation(),Target->GetActorLocation())>=FMath::Square(SpitMinRange)&&CanSee(Target.Get()))
        return FMath::Max(SpitMinRange,SpitMaxRange-50.f);
    if(Target.IsValid()&&WhirlwindClip&&WhirlwindCooldownLeft<=0.f&&CooldownLeft<=0.f&&
        FVector::DistSquared2D(GetActorLocation(),Target->GetActorLocation())<=FMath::Square(FMath::Max(WhirlwindTriggerRange,SlamTriggerRange+35.f))&&
        FMath::Abs(Target->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<=55.f&&CanSee(Target.Get()))
        return FMath::Max(0.f,WhirlwindTriggerRange-15.f);
    if(Target.IsValid()&&TrunkSlamClip&&SlamCooldownLeft<=0.f&&CooldownLeft<=0.f&&
        FVector::DistSquared2D(GetActorLocation(),Target->GetActorLocation())>=FMath::Square(SlamMinRange)&&CanSee(Target.Get()))
        return FMath::Max(SlamMinRange,SlamTriggerRange-15.f);
    return FMath::Max(0.f,BiteTriggerRange-15.f);
}

void ASpiralPillarM14::TickAttack(float Dt)
{
    UAnimSequence* Clip=AttackClip(State);
    const float Duration=Clip?Clip->GetPlayLength():2.4f;
    Sample(FMath::Min(StateSeconds,Duration));
    if(!HasAuthority())return;
    const EM14State StartedState=State;
    if(State==EM14State::Spit&&!bSpitAimLocked)
    {
        if(AttackTarget.IsValid())
        {
            SpitAimPoint=AttackTarget->GetActorLocation();SpitAimVelocity=AttackTarget->GetVelocity();
            SpitAimSampleSeconds=StateSeconds;
        }
        const FVector Aim=M14SpitIntercept(Mouth(),SpitAimPoint,SpitAimVelocity,
            SpitReleaseSeconds-SpitAimSampleSeconds,SpitSpeed,SpitTravelRange);
        const float Desired=(Aim-GetActorLocation()).Rotation().Yaw;
        LockedYaw+=FMath::Clamp(FMath::FindDeltaAngleDegrees(LockedYaw,Desired),-45.f*Dt,45.f*Dt);
        bSpitAimLocked=StateSeconds>=SpitAimLockSeconds;
    }
    SetActorRotation(FRotator(0,LockedYaw,0));
    if(State==EM14State::Whirlwind)TickWhirlwindContact();
    else if(State==EM14State::Bite&&!bConsumed&&StateSeconds>=BiteContactSeconds)
    {
        Sample(BiteContactSeconds);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
        BiteContact();
    }
    else if(State==EM14State::Spit&&!bConsumed&&StateSeconds>=SpitReleaseSeconds)
    {
        Sample(SpitReleaseSeconds);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
        ReleaseSpit();
    }
    else if(State==EM14State::TrunkSlam&&!bConsumed&&StateSeconds>=SlamContactSeconds)
    {
        Sample(SlamContactSeconds);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
        SlamContact();
    }
    else if(IsSweeping())
    {
        // Sample the short contact window on its authored 30 Hz clock, so a
        // long game frame cannot skip the whole strike. Thirteen samples/attack.
        while(NextSweepSample<=FMath::Min(StateSeconds,SweepEndSeconds)+UE_SMALL_NUMBER&&State==StartedState)
        {
            Sample(NextSweepSample);GetMesh()->TickAnimation(0.f,false);GetMesh()->RefreshBoneTransforms();
            NextSweepSample+=1.f/30.f;
            SweepContact();
        }
    }
    // Point damage may synchronously parry, interrupt or kill the attacker.
    if(State!=StartedState)return;
    Sample(FMath::Min(StateSeconds,Duration));
    if(StateSeconds>=Duration)
    {
        AttackTarget.Reset();SweepVictims.Reset();WhirlwindVictims.Reset();SetState(EM14State::Idle);
        if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
    }
}

void ASpiralPillarM14::ReleaseSpit()
{
    if(bConsumed||!HasAuthority()||State!=EM14State::Spit)return;
    bConsumed=true;
    APawn* Victim=AttackTarget.Get();if(!IsValid(Victim))return;
    if(const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();Vitals&&Vitals->IsDead())return;
    const FVector From=Mouth();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14SpitExit),false,this);
    Query.AddIgnoredActor(Victim);
    FHitResult Block;
    if(GetWorld()->LineTraceSingleByChannel(Block,GetMesh()->GetSocketLocation(TEXT("spine_01")),From,ECC_Visibility,Query))return;
    // Retain the readable final windup lock. Extrapolate its motion snapshot
    // to release, then solve travel time from the actual sampled mouth position.
    const FVector Aim=M14SpitIntercept(From,SpitAimPoint,SpitAimVelocity,
        SpitReleaseSeconds-SpitAimSampleSeconds,SpitSpeed,SpitTravelRange);
    const FVector Direction=(Aim-From).GetSafeNormal();
    FActorSpawnParameters Params;Params.Owner=this;Params.Instigator=this;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Shot=GetWorld()->SpawnActor<AM14MucusProjectile>(From,Direction.Rotation(),Params))
    {
        Shot->Launch(this,Direction,SpitSpeed,SpitTravelRange,PhysicalAttack*SpitDamageMultiplier,
            SpitSlowPercent,SpitSlowSeconds,MucusMaterial,MucusCoreMaterial);
        ActiveProjectile=Shot;
    }
}

void ASpiralPillarM14::SweepContact()
{
    if(!HasAuthority()||!IsSweeping())return;
    const EM14State StartedState=State;
    const bool Positive=(State==EM14State::SweepRight)==bPositiveXIsRight;
    const int32 PositiveRoots[3]={7,0,1},NegativeRoots[3]={3,4,5};
    const int32* Roots=Positive?PositiveRoots:NegativeRoots;
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M14RootSweep),false,this);
    for(int32 I=0;I<3&&State==StartedState;++I)
    {
        const int32 Index=Roots[I];
        const FName Fan(*FString::Printf(TEXT("rootfan_%02d"),Index)),Toe(*FString::Printf(TEXT("roottoe_%02d"),Index));
        const FVector From=GetMesh()->GetSocketLocation(Fan);
        const FVector To=GetMesh()->GetSocketTransform(Toe).TransformPosition(SweepTipOffsets[Index]);
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,Objects,FCollisionShape::MakeSphere(SweepRadius),Query);
        Hits.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
        for(const FHitResult& Hit:Hits)
        {
            AActor* Actor=Hit.GetActor();const auto* Component=Hit.GetComponent();
            APawn* Pawn=Cast<APawn>(Actor);
            const bool PlayerBody=Pawn&&Pawn->IsPlayerControlled()&&Component==Pawn->GetRootComponent();
            if(!IsValid(Actor)||!Component||(!PlayerBody&&Component->GetCollisionResponseToChannel(ECC_Visibility)!=ECR_Block))continue;
            if(PlayerBody||Actor->IsA<AFPSIceWall>())
            {
                if(!SweepVictims.Contains(Actor))
                {
                    SweepVictims.Add(Actor);
                    UGameplayStatics::ApplyPointDamage(Actor,PhysicalAttack*SweepDamageMultiplier,
                        (To-From).GetSafeNormal(),Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
                }
            }
            // First solid hit blocks this root, including a player already hit.
            break;
        }
    }
}

void ASpiralPillarM14::CancelProjectile()
{
    if(ActiveProjectile.IsValid())ActiveProjectile->Destroy();
    ActiveProjectile.Reset();
}

void ASpiralPillarM14::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority())CancelProjectile();
    Super::EndPlay(Reason);
}
