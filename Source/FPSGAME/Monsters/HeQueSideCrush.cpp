#include "HeQueMonster.h"
#include "HeQueSweepTiming.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "FleshHandMonster.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/AudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

float AHeQueMonster::SweepAge() const {return FMath::Max(0.f,float(ActionClock()-Sweep.StartedAt));}
bool AHeQueMonster::SweepBlocked() const
{
    const auto* Status=FindComponentByClass<UCombatStatusFormula>();
    return Dead()||Controlled()||!GetCharacterMovement()->IsMovingOnGround()||
        (Status&&(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned()));
}
bool AHeQueMonster::HasSweepSight(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueSweepSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,GetNavAgentLocation()+FVector(0,0,100),
        Victim->GetActorLocation(),ECC_Visibility,Query)||(Hit.GetActor()&&Hit.GetActor()->IsA<AFPSIceWall>());
}
bool AHeQueMonster::DesiredCombatFacing(float& Yaw) const
{
    const APawn* Victim=CombatTarget.Get();
    // Align before planting. The entire attack keeps its original world heading.
    if(Busy()||!IsValid(Victim)||GetHorizontalDistanceTo(Victim)>RiftRange)return false;
    if(!HasRiftSight(Victim)&&!HasSweepSight(Victim))return false;
    Yaw=(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw;return true;
}
bool AHeQueMonster::CanSweep(APawn* Victim) const
{
    if(Busy()||SweepBlocked()||!SweepClip||SweepFrames.Num()<2||ActionClock()<NextSweepAt||
        !IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    return Delta.Size2D()<=SweepTriggerRange&&FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<100.f&&
        FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())>=FMath::Cos(FMath::DegreesToRadians(25.f))&&
        HasSweepSight(Victim);
}
bool AHeQueMonster::StartSweep(APawn* Victim)
{
    CombatTarget=Victim;SweepVictims.Reset();NextSweepFrame=0;
    Sweep.Active=true;Sweep.StartedAt=ActionClock();++Sweep.Serial;
    NextSweepAt=Sweep.StartedAt+FMath::Max(HeQueSweepTiming::End,SweepCooldown);
    NextRiftAt=FMath::Max(NextRiftAt,Sweep.StartedAt+HeQueSweepTiming::End+.4);
    NextClampAt=FMath::Max(NextClampAt,Sweep.StartedAt+HeQueSweepTiming::End+.4);
    NextPsychicAt=FMath::Max(NextPsychicAt,Sweep.StartedAt+HeQueSweepTiming::End+.4);
    NextJumpAt=FMath::Max(NextJumpAt,Sweep.StartedAt+HeQueSweepTiming::End+.4);
    GetCharacterMovement()->StopMovementImmediately();
    OnRep_Sweep();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AHeQueMonster::OnRep_Sweep()
{
    RefreshPoseTick();
    if(GetNetMode()==NM_DedicatedServer||PresentedSweepSerial==Sweep.Serial)return;
    PresentedSweepSerial=Sweep.Serial;SweepVoice->Stop();
    if(Sweep.Active&&SweepSound&&SweepAge()<HeQueSweepTiming::End)
    {
        SweepVoice->SetSound(SweepSound);SweepVoice->AttenuationSettings=SweepAttenuation;SweepVoice->Play(SweepAge());
    }
}
void AHeQueMonster::CancelAttack()
{
    CancelJumpSlam();
    CancelPsychic();
    CancelRift();
    CancelClamp();
    if(!HasAuthority()||!Sweep.Active)return;
    Sweep.Active=false;++Sweep.Serial;SweepVictims.Reset();OnRep_Sweep();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AHeQueMonster::TickSweep()
{
    if(!HasAuthority()||!Sweep.Active)return;
    const auto* AI=Cast<AMonsterAIController>(GetController());
    if(SweepBlocked()||!AI||!AI->bDecisionEnabled){CancelAttack();return;}
    const float Age=SweepAge();
    // Consume authored intervals exactly once, even when a server tick spans
    // multiple samples. ApplyPointDamage can synchronously parry or kill us.
    while(NextSweepFrame<SweepFrames.Num()&&SweepFrames[NextSweepFrame].Time<=FMath::Min(Age,HeQueSweepTiming::ContactEnd)+.0001f)
    {
        SweepContact(NextSweepFrame++);
        if(!IsSweeping()||IsActorBeingDestroyed())return;
    }
    if(Age>=HeQueSweepTiming::End)CancelAttack();
}
FVector AHeQueMonster::SweepPointWorld(const FVector& Point) const
{
    // Saved points are imported skeletal component space, including FBX units.
    return GetMesh()->GetComponentTransform().TransformPosition(Point);
}
void AHeQueMonster::SweepContact(int32 Index)
{
    const auto& B=SweepFrames[Index];
    if(B.Time<HeQueSweepTiming::ContactStart||B.Time>HeQueSweepTiming::ContactEnd+.0001f)return;
    MeleeContact(SweepFrames,Index,SweepHitRadius,SweepDamage,SweepPushDistance,SweepVictims,false);
}
void AHeQueMonster::MeleeContact(const TArray<FHeQueSweepFrame>& Frames,int32 Index,float Radius,float Damage,float PushDistance,
    TSet<TWeakObjectPtr<AActor>>& Victims,bool bClamp)
{
    const auto& B=Frames[Index];const auto& A=Frames[FMath::Max(0,Index-1)];
    const auto Active=[this,bClamp](){return (bClamp?IsClamping():IsSweeping())&&!SweepBlocked()&&!IsActorBeingDestroyed();};
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HeQueSideCrush),false,this);
    FCollisionQueryParams Occlusion=Query;
    FBox BoundsA(ForceInit),BoundsB(ForceInit);
    if(!bClamp)
    {
        if(A.Points.IsEmpty()||B.Points.IsEmpty())return;
        for(const FVector& Point:A.Points)BoundsA+=Point;
        for(const FVector& Point:B.Points)BoundsB+=Point;
        // Every player in the kick volume is a recipient, not cover for the
        // next player. World cover still receives an independent LOS query.
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        {
            const auto* PC=It->Get();APawn* Pawn=PC?PC->GetPawn():nullptr;
            if(!Pawn)continue;
            Occlusion.AddIgnoredActor(Pawn);
            TArray<AActor*> Equipment;Pawn->GetAttachedActors(Equipment,true,true);
            Occlusion.AddIgnoredActors(Equipment);
        }
    }
    const int32 Queries=bClamp?FMath::Min(A.Points.Num(),B.Points.Num()):1;
    for(int32 I=0;I<Queries;++I)
    {
        const FVector From=SweepPointWorld(bClamp?A.Points[I]:BoundsA.GetCenter());
        const FVector To=SweepPointWorld(bClamp?B.Points[I]:BoundsB.GetCenter());
        TArray<FHitResult> Hits;
        if(bClamp)
            GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius),Query);
        else
        {
            // A filled volume around the complete lower limb / foot, swept
            // between 120Hz authored samples. Fast kicks cannot tunnel between
            // server ticks or leave holes between individual surface probes.
            // Mesh X is lateral, Y is forward; the mesh quaternion supplies yaw.
            const FVector HalfSize=BoundsA.GetExtent().ComponentMax(BoundsB.GetExtent())*GetMesh()->GetComponentScale().GetAbs()+FVector(Radius,20.f,15.f);
            GetWorld()->SweepMultiByObjectType(Hits,From,To,GetMesh()->GetComponentQuat(),Objects,FCollisionShape::MakeBox(HalfSize),Query);
        }
        for(const auto& Hit:Hits)
        {
            if(!Active())return;
            AActor* Victim=Hit.GetActor();APawn* Player=Cast<APawn>(Victim);
            if(!IsValid(Victim)||Victims.Contains(Victim)||
                (!(Player&&Player->IsPlayerControlled()&&Hit.GetComponent()==Player->GetRootComponent())&&!Victim->IsA<AFPSIceWall>()))continue;
            const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
            if(Vitals&&(Vitals->IsDead()||Vitals->IsInvulnerable()))continue;
            if(!bClamp&&FVector::DotProduct(Victim->GetActorLocation()-GetActorLocation(),GetActorForwardVector())<0.f)continue;
            FHitResult Block;
            const FVector CoverPoint=!bClamp&&Player?Player->GetActorLocation():FVector(Hit.ImpactPoint);
            if(GetWorld()->LineTraceSingleByChannel(Block,GetNavAgentLocation()+FVector(0,0,100),CoverPoint,ECC_Visibility,Occlusion)&&Block.GetActor()!=Victim)continue;
            Victims.Add(Victim);
            const FVector Direction=bClamp?(To-From).GetSafeNormal():GetActorForwardVector();
            const float Before=Vitals?Vitals->Health:0.f;
            UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction.IsNearlyZero()?GetActorForwardVector():Direction,
                Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
            // Guard/parry is resolved by the damage receiver first. Only an
            // actual damaging hit can stun or push a surviving player.
            if(Player&&IsValid(Victim)&&Vitals&&Vitals->Health<Before&&!Vitals->IsDead())
            {
                if(bClamp)UCombatStatusFormula::GetOrAdd(Player)->AddStun(2.f);
                else if(PushDistance>0.f)
                {
                    FVector Push=Direction.GetSafeNormal2D();
                    if(Push.IsNearlyZero())Push=(Victim->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
                    // The existing swept displacement stops on its first
                    // blocking hit; it never teleports through a wall.
                    if(auto* Move=Player->FindComponentByClass<UFPSCharacterMovementComponent>())Move->ApplyImpactPush(Push,PushDistance);
                    else UFleshHandPushComponent::Apply(Cast<ACharacter>(Player),Push,PushDistance);
                }
            }
            if(!Active())return;
        }
    }
}
