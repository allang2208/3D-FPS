#include "M66IncineratorMonster.h"
#include "M66SweepTiming.h"
#include "M66SlamTiming.h"
#include "M66BreathTiming.h"
#include "M66FurnaceVisualComponent.h"
#include "M66AudioComponent.h"
#include "MonsterAIController.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Skills/FPSIceWall.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

float AM66IncineratorMonster::SweepAge() const {return FMath::Max(0.f,float(ActionClock()-Sweep.StartedAt));}
void AM66IncineratorMonster::RefreshPoseTick()
{
    GetMesh()->VisibilityBasedAnimTickOption=Reaction.Phase==EM66Reaction::None&&!Sweep.Active&&(!bEnableBackSmoke||Dead())?
        EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered:EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}
bool AM66IncineratorMonster::HasSweepSight(const APawn* Victim) const
{
    if(!IsValid(Victim))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M66SweepSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Hit;
    return !GetWorld()->LineTraceSingleByChannel(Hit,GetNavAgentLocation()+FVector(0,0,110),
        Victim->GetActorLocation(),ECC_Visibility,Query)||(Hit.GetActor()&&Hit.GetActor()->IsA<AFPSIceWall>());
}
bool AM66IncineratorMonster::DesiredCombatFacing(float& Yaw) const
{
    APawn* Victim=CombatTarget.Get();
    if(Busy()||!IsValid(Victim)||GetHorizontalDistanceTo(Victim)>FMath::Max3(SweepTriggerRange,SlamTriggerRange,BreathRange)||!HasSweepSight(Victim))return false;
    Yaw=(Victim->GetActorLocation()-GetActorLocation()).Rotation().Yaw;return true;
}
bool AM66IncineratorMonster::CanAttack(APawn* Victim) const
{
    if(Busy()||ActionClock()<NextAttackAt||!GetCharacterMovement()->IsMovingOnGround()
        ||!IsValid(Victim)||!Victim->IsPlayerControlled())return false;
    if(Status&&(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned()))return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    if(FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<FMath::Cos(FMath::DegreesToRadians(30.f)))return false;
    if(CanUseBreath(Victim))return true;
    return FMath::Abs(Victim->GetNavAgentLocation().Z-GetNavAgentLocation().Z)<100.f&&HasSweepSight(Victim)
        &&(CanUseAttack(Victim,false)||CanUseAttack(Victim,true));
}
bool AM66IncineratorMonster::CanUseAttack(const APawn* Victim,bool GroundSlam) const
{
    const auto* Clip=GroundSlam?SlamClip.Get():SweepClip.Get();
    const auto& Frames=GroundSlam?SlamFrames:SweepFrames;
    const float Range=GroundSlam?SlamTriggerRange:SweepTriggerRange;
    if(!Clip||Frames.Num()<2||ActionClock()<(GroundSlam?NextSlamAt:NextSweepAt)||GetHorizontalDistanceTo(Victim)>Range)return false;
    if(GroundSlam)
    {
        const FVector Direction=(Victim->GetActorLocation()-GetActorLocation()).GetSafeNormal2D();
        if(FVector::DotProduct(Direction,GetActorForwardVector())<FMath::Cos(FMath::DegreesToRadians(22.f)))return false;
    }
    return GroundSlam?SlamAreaCanReach(Victim):SweepCanReach(Victim);
}
bool AM66IncineratorMonster::StartAttack(APawn* Victim)
{
    if(!HasAuthority()||!CanAttack(Victim))return false;
    const bool UseBreath=CanUseBreath(Victim);
    const bool UseSlam=!UseBreath&&CanUseAttack(Victim,true)&&(bPreferSlam||!CanUseAttack(Victim,false));
    CombatTarget=Victim;SweepVictims.Reset();NextSweepFrame=0;bSlamReleased=false;
    Sweep.Active=true;Sweep.Kind=UseBreath?EM66AttackKind::FurnaceBreath:(UseSlam?EM66AttackKind::GroundSlam:EM66AttackKind::Sweep);Sweep.StartedAt=ActionClock();++Sweep.Serial;
    if(UseBreath)
    {
        NextBreathHit=0;NextBreathAimUpdate=0.;Sweep.bBreathAimLocked=false;
        Sweep.BreathAim=GetActorRotation();
        Sweep.BreathAim.Pitch=FMath::Clamp(float((Victim->GetActorLocation()-MouthAtAge(0)).Rotation().Pitch),-30.f,20.f);
        NextBreathAt=Sweep.StartedAt+FMath::Max(M66BreathTiming::End,BreathCooldown);
        NextAttackAt=Sweep.StartedAt+M66BreathTiming::End;
    }
    else if(UseSlam)
    {
        NextSlamAt=Sweep.StartedAt+FMath::Max(M66SlamTiming::End,SlamCooldown);
        NextAttackAt=Sweep.StartedAt+M66SlamTiming::End+M66SlamTiming::RestAfterEnd;
    }
    else
    {
        NextSweepAt=Sweep.StartedAt+FMath::Max(M66SweepTiming::End,SweepCooldown);
        NextAttackAt=NextSweepAt;
    }
    if(!UseBreath)bPreferSlam=!UseSlam;
    GetCharacterMovement()->StopMovementImmediately();
    OnRep_Sweep();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController())){AI->StopMovement();AI->UpdateKnowledge();}
    return true;
}
void AM66IncineratorMonster::OnRep_Sweep() {RefreshPoseTick();if(BreathVisuals)BreathVisuals->Wake();}
void AM66IncineratorMonster::StopSweep()
{
    if(!HasAuthority()||!Sweep.Active)return;
    Sweep.Active=false;++Sweep.Serial;SweepVictims.Reset();OnRep_Sweep();ForceNetUpdate();
    if(auto* AI=Cast<AMonsterAIController>(GetController()))AI->UpdateKnowledge();
}
void AM66IncineratorMonster::TickSweep()
{
    if(!HasAuthority()||!Sweep.Active)return;
    if(Dead()||Controlled()||!GetCharacterMovement()->IsMovingOnGround()
        ||(Status&&(Status->IsFrozen()||Status->IsPetrified()||Status->IsStunned()))) {StopSweep();return;}
    if(const auto* AI=Cast<AMonsterAIController>(GetController());!AI||!AI->bDecisionEnabled){StopSweep();return;}
    const float Age=SweepAge();
    if(Sweep.Kind==EM66AttackKind::FurnaceBreath){TickBreath();return;}
    const bool GroundSlam=Sweep.Kind==EM66AttackKind::GroundSlam;
    if(GroundSlam)
    {
        // One ground pulse replaces direct fist damage. A delayed server tick
        // still releases once; interruption before impact never creates a wave.
        if(!bSlamReleased&&Age>=M66SlamTiming::Impact)
        {bSlamReleased=true;ReleaseSlamWave();}
        if(Age>=M66SlamTiming::End)StopSweep();
        return;
    }
    const auto& Frames=GroundSlam?SlamFrames:SweepFrames;
    const float ContactEnd=GroundSlam?M66SlamTiming::ContactEnd:M66SweepTiming::ContactEnd;
    // Consume every authored contact interval once, including a slow server frame.
    while(NextSweepFrame<Frames.Num()&&Frames[NextSweepFrame].Time<=FMath::Min(Age,ContactEnd)+.0001f)
    {
        SweepContact(NextSweepFrame++);
        if(!IsSweeping()||IsActorBeingDestroyed())return; // Parry/death may run inside ApplyPointDamage.
    }
    if(Age>=(GroundSlam?M66SlamTiming::End:M66SweepTiming::End))StopSweep();
}
FVector AM66IncineratorMonster::SweepPointWorld(const FVector& Point,bool GroundSlam) const
{
    // The top container carries terrain alignment; its imported 100x scale is retained.
    const FTransform& Reference=GroundSlam?SlamReferenceRoot:SweepReferenceRoot;
    return GetMesh()->GetSocketTransform(TEXT("M66_Rig")).TransformPosition(Reference.InverseTransformPosition(Point));
}
bool AM66IncineratorMonster::SweepCanReach(const APawn* Victim,bool GroundSlam) const
{
    const auto& Frames=GroundSlam?SlamFrames:SweepFrames;
    const float HitRadius=GroundSlam?SlamHitRadius:SweepHitRadius;
    float Radius=0,Half=0;Victim->GetSimpleCollisionCylinder(Radius,Half);
    const FVector Center=Victim->GetActorLocation(),Extent(0,0,FMath::Max(0.f,Half-Radius));
    for(int32 Frame=0;Frame<Frames.Num();++Frame)
    {
        const auto& B=Frames[Frame];const auto& A=Frames[FMath::Max(0,Frame-1)];
        for(int32 I=0;I<FMath::Min(A.Points.Num(),B.Points.Num());++I)
        {
            FVector OnClaw,OnBody;
            FMath::SegmentDistToSegmentSafe(SweepPointWorld(A.Points[I],GroundSlam),SweepPointWorld(B.Points[I],GroundSlam),
                Center-Extent,Center+Extent,OnClaw,OnBody);
            if(FVector::DistSquared(OnClaw,OnBody)<=FMath::Square(Radius+HitRadius))return true;
        }
    }
    return false;
}
void AM66IncineratorMonster::SweepContact(int32 FrameIndex)
{
    const bool GroundSlam=Sweep.Kind==EM66AttackKind::GroundSlam;
    const auto& Frames=GroundSlam?SlamFrames:SweepFrames;
    if(!IsSweeping()||!Frames.IsValidIndex(FrameIndex))return;
    const auto& B=Frames[FrameIndex];const auto& A=Frames[FMath::Max(0,FrameIndex-1)];
    const float ContactStart=GroundSlam?M66SlamTiming::ContactStart:M66SweepTiming::ContactStart;
    const float ContactEnd=GroundSlam?M66SlamTiming::ContactEnd:M66SweepTiming::ContactEnd;
    const float HitRadius=GroundSlam?SlamHitRadius:SweepHitRadius;
    const float Damage=GroundSlam?SlamDamage:SweepDamage;
    if(B.Time<ContactStart||B.Time>ContactEnd+.0001f)return;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M66ClawSweep),false,this);
    for(int32 I=0;I<FMath::Min(A.Points.Num(),B.Points.Num());++I)
    {
        const FVector From=SweepPointWorld(A.Points[I],GroundSlam),To=SweepPointWorld(B.Points[I],GroundSlam);
        TArray<FHitResult> Hits;
        GetWorld()->SweepMultiByObjectType(Hits,From,To,FQuat::Identity,Objects,FCollisionShape::MakeSphere(HitRadius),Query);
        for(const auto& Hit:Hits)
        {
            if(!IsSweeping()||IsActorBeingDestroyed())return;
            AActor* Victim=Hit.GetActor();APawn* Player=Cast<APawn>(Victim);
            if(!IsValid(Victim)||SweepVictims.Contains(Victim)||
                (!(Player&&Player->IsPlayerControlled()&&Hit.GetComponent()==Player->GetRootComponent())&&!Victim->IsA<AFPSIceWall>()))continue;
            const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
            if(Vitals&&(Vitals->IsDead()||Vitals->IsInvulnerable()))continue;
            FHitResult Block;
            const FVector Sight=GetNavAgentLocation()+FVector(0,0,110);
            if(GetWorld()->LineTraceSingleByChannel(Block,Sight,Hit.ImpactPoint,ECC_Visibility,Query)&&Block.GetActor()!=Victim)continue;
            SweepVictims.Add(Victim);
            const FVector Direction=(To-From).GetSafeNormal();
            const float Applied=UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction.IsNearlyZero()?GetActorForwardVector():Direction,
                Hit,GetController(),this,UEnemyMeleeDamage::StaticClass());
            if(Applied>0.f)BodyAudio->Emit(TEXT("SweepImpact"),Hit.ImpactPoint);
            if(!IsSweeping()||IsActorBeingDestroyed())return;
        }
    }
}
