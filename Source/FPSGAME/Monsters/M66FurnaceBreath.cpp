#include "M66IncineratorMonster.h"
#include "M66BreathTiming.h"
#include "M66FurnaceVisualComponent.h"
#include "MonsterCombatComponent.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "../Skills/FireMagicArea.h"
#include "../Skills/FireMagicDamage.h"
#include "../Skills/MagicOcclusion.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

FVector AM66IncineratorMonster::MouthAtAge(float Age) const
{
    if(BreathMouthSamples.IsEmpty())return GetMesh()->GetSocketTransform(TEXT("Bone_006")).TransformPosition(BreathMouthOffset);
    const float Frame=FMath::Clamp(Age*M66BreathTiming::MouthSampleRate,0.f,float(BreathMouthSamples.Num()-1));
    const int32 A=FMath::FloorToInt(Frame),B=FMath::Min(A+1,BreathMouthSamples.Num()-1);
    const FVector Point=FMath::Lerp(BreathMouthSamples[A],BreathMouthSamples[B],Frame-A);
    return GetMesh()->GetSocketTransform(TEXT("M66_Rig")).TransformPosition(BreathReferenceRoot.InverseTransformPosition(Point));
}
void AM66IncineratorMonster::FurnaceBreathFrame(FVector& Origin,FQuat& Rotation) const
{
    Origin=IsBreathing()?MouthAtAge(SweepAge()):GetMesh()->GetSocketTransform(TEXT("Bone_006")).TransformPosition(BreathMouthOffset);
    Rotation=IsBreathing()?Sweep.BreathAim.Quaternion():GetActorQuat();
    const FVector Inside=GetNavAgentLocation()+FVector(0,0,200);FHitResult Wall;
    if(FireMagic::TraceSurface(const_cast<AM66IncineratorMonster*>(this),Inside,Origin,Wall,true))Origin=Inside;
}
bool AM66IncineratorMonster::CanUseBreath(const APawn* Victim) const
{
    if(!Victim||!BreathClip||!BreathSystem||BreathMouthSamples.IsEmpty()||ActionClock()<NextBreathAt)return false;
    const float Distance=GetHorizontalDistanceTo(Victim);
    if(Distance<BreathMinimumRange||Distance>BreathRange)return false;
    if(GetNetMode()!=NM_DedicatedServer&&(!BreathVisuals||!BreathVisuals->IsReady()))return false;
    FVector Origin;FQuat Rotation;FurnaceBreathFrame(Origin,Rotation);
    const FVector To=Victim->GetActorLocation()-Origin;
    if(To.Size()>BreathRange||FMath::Abs(To.Rotation().Pitch)>30.f)return false;
    FHitResult Hit;return !FireMagic::TraceSurface(const_cast<AM66IncineratorMonster*>(this),Origin,Victim->GetActorLocation(),Hit,true);
}
bool AM66IncineratorMonster::DesiredBreathFacing(float& Yaw) const
{
    if(!IsBreathing()||Sweep.bBreathAimLocked||SweepAge()>=M66BreathTiming::AimLock||!CombatTarget.IsValid())return false;
    Yaw=(CombatTarget->GetActorLocation()-GetActorLocation()).Rotation().Yaw;return true;
}
void AM66IncineratorMonster::TickBreath()
{
    const float Age=SweepAge();
    if(!Sweep.bBreathAimLocked)
    {
        if(!CombatTarget.IsValid()){StopSweep();return;}
        if(const auto* HP=CombatTarget->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead()){StopSweep();return;}
        Sweep.BreathAim=GetActorRotation();
        Sweep.BreathAim.Pitch=FMath::Clamp(float((CombatTarget->GetActorLocation()-MouthAtAge(Age)).Rotation().Pitch),-30.f,20.f);
        Sweep.BreathAim.Roll=0;
        Sweep.bBreathAimLocked=Age>=M66BreathTiming::AimLock;
        if(ActionClock()>=NextBreathAimUpdate||Sweep.bBreathAimLocked){NextBreathAimUpdate=ActionClock()+.10;ForceNetUpdate();}
    }
    while(NextBreathHit<M66BreathTiming::HitCount&&Age+.0001f>=M66BreathTiming::Release+NextBreathHit*M66BreathTiming::Interval)
    {
        ++NextBreathHit;BreathHit();
        if(!IsBreathing()||IsActorBeingDestroyed())return;
    }
    if(Age>=M66BreathTiming::End)StopSweep();
}
void AM66IncineratorMonster::BreathHit()
{
    if(!HasAuthority()||!IsBreathing())return;
    FVector Origin;FQuat Rotation;FurnaceBreathFrame(Origin,Rotation);
    TArray<FOverlapResult> Overlaps;FCollisionQueryParams Query(SCENE_QUERY_STAT(M66FurnaceBreath),false,this);
    GetWorld()->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
        FCollisionShape::MakeSphere(BreathRange+100.f),Query);
    TSet<TWeakObjectPtr<AActor>> Seen;const float Slope=FMath::Tan(FMath::DegreesToRadians(BreathArcDegrees*.5f));
    for(const auto& Overlap:Overlaps)
    {
        AActor* Target=Overlap.GetActor();if(!IsValid(Target)||Seen.Contains(Target)||Target==this||!Target->CanBeDamaged())continue;
        Seen.Add(Target);
        auto* Vitals=Target->FindComponentByClass<UFPSCombatHealthComponent>();auto* Combatant=Target->FindComponentByClass<UMonsterCombatComponent>();
        if((!Vitals&&!Combatant)||(Vitals&&Vitals->IsDead())||(Combatant&&Combatant->IsDead())||RangedAttackQuery::IsFriendlyUnit(this,Target))continue;
        MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Origin,Samples);
        for(const FVector& Point:Samples)
        {
            const FVector Local=Rotation.UnrotateVector(Point-Origin);
            if(Local.X<0||Local.SizeSquared()>FMath::Square(BreathRange)||FMath::Abs(Local.Y)>25.f+Local.X*Slope||FMath::Abs(Local.Z)>30.f+Local.X*.20f)continue;
            FHitResult Block;if(FireMagic::TraceSurface(this,Origin,Point,Block,true))continue;
            auto* Shape=Cast<UPrimitiveComponent>(Target->GetRootComponent());
            FHitResult Hit(Target,Shape,Point,(Origin-Point).GetSafeNormal());Hit.TraceStart=Origin;Hit.TraceEnd=Point;
            UGameplayStatics::ApplyPointDamage(Target,BreathDamage,(Point-Origin).GetSafeNormal(),Hit,GetController(),this,UFireMagicDamage::StaticClass());
            if(!IsBreathing()||IsActorBeingDestroyed())return;
            break;
        }
    }
}
