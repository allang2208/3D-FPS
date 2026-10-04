#include "MeleeSmallTargetQuery.h"
#include "../Skills/FPSIceWall.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../Monsters/FleshHandMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
AFleshHandMonster* LivingSmallHand(AActor* Actor)
{
    auto* Hand=Cast<AFleshHandMonster>(Actor);
    return IsValid(Hand)&&Hand->bMinion&&!Hand->Dead()&&Hand->CanBeDamaged()
        &&Hand->Combat&&!Hand->Combat->IsDead()?Hand:nullptr;
}

bool Covered(UWorld* World,const FVector& Start,const FVector& Point,const FCollisionQueryParams& Params)
{
    FHitResult Hit;
    return World->LineTraceSingleByChannel(Hit,Start,Point,ECC_Visibility,Params);
}
}

TArray<FHitResult> MeleeSmallTargets::QueryLowSector(UWorld* World,ACharacter* Owner,const FTransform& Aim,
    float Reach,const TSet<TWeakObjectPtr<AActor>>& AlreadyHit,bool bCleave,float ArcDegrees,float MaxLowReachCM)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(Melee_LowSmallTargets);
    TArray<FHitResult> Result;
    if(!World||!Owner||Reach<=0.f||Aim.GetUnitAxis(EAxis::X).Z>0.35f)return Result;
    const float Range=FMath::Min(Reach,MaxLowReachCM);
    const float FeetZ=Owner->GetActorLocation().Z-Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const FVector Origin(Aim.GetLocation().X,Aim.GetLocation().Y,FeetZ+50.f);
    const FVector Forward=FRotator(0.f,Aim.Rotator().Yaw,0.f).Vector();
    const float MinDot=FMath::Cos(FMath::DegreesToRadians(FMath::Clamp(ArcDegrees,1.f,LowArcDegrees)*.5f));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MeleeLowOverlap),false,Owner);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FOverlapResult> Overlaps;
    World->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,Objects,
        FCollisionShape::MakeBox(FVector(Range,Range,100.f)),Query);
    TArray<AFleshHandMonster*> Candidates;
    FCollisionQueryParams Cover(SCENE_QUERY_STAT(MeleeLowCover),false,Owner);
    for(const auto& Overlap:Overlaps)
    {
        // Cleaving ignores nearby bodies once, without per-target retry traces.
        if(bCleave&&Cast<APawn>(Overlap.GetActor()))Cover.AddIgnoredActor(Overlap.GetActor());
        auto* Hand=LivingSmallHand(Overlap.GetActor());
        if(!Hand||AlreadyHit.Contains(Hand)||Overlap.GetComponent()!=Hand->GetCapsuleComponent())continue;
        const FVector Center=Hand->GetCapsuleComponent()->GetComponentLocation();
        const float TargetFeet=Center.Z-Hand->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
        const FVector Delta=Center-Origin;
        if(FMath::Abs(TargetFeet-FeetZ)>MaxFloorDifferenceCM||Delta.SizeSquared2D()>FMath::Square(Range))continue;
        if(FVector::DotProduct(Delta.GetSafeNormal2D(),Forward)<MinDot)continue;
        Candidates.AddUnique(Hand);
    }
    Candidates.Sort([&](const AFleshHandMonster& A,const AFleshHandMonster& B)
    {
        return FVector::DistSquared2D(A.GetActorLocation(),Origin)<FVector::DistSquared2D(B.GetActorLocation(),Origin);
    });
    // Bounded detailed work even in a crowded spawn: at most two cover rays per
    // candidate. Already-hit bodies leave the candidate list on the next frame.
    const int32 Count=FMath::Min(Candidates.Num(),MaxCoverCandidates);
    for(int32 I=0;I<Count;++I)
    {
        auto* Target=Candidates[I];auto* Capsule=Target->GetCapsuleComponent();
        FVector LowStart=Origin;LowStart.Z=Capsule->GetComponentLocation().Z;
        FVector Point;
        if(Capsule->GetClosestPointOnCollision(LowStart,Point)<0.f)Point=Capsule->GetComponentLocation();
        FCollisionQueryParams TargetCover=Cover;TargetCover.AddIgnoredActor(Target);
        // Eye visibility alone could look over a low wall. Require a clear path
        // at hand height too; floors and scenery remain real blockers.
        if(Covered(World,Aim.GetLocation(),Point,TargetCover)||Covered(World,LowStart,Point,TargetCover))continue;
        FHitResult Hit(Target,Capsule,Point,(LowStart-Point).GetSafeNormal());
        Hit.bBlockingHit=true;Hit.ImpactPoint=Hit.Location=Point;
        Hit.TraceStart=LowStart;Hit.TraceEnd=Point;Hit.Distance=FVector::Distance(LowStart,Point);
        Result.Add(Hit);
        if(!bCleave)break;
    }
    return Result;
}

bool MeleeSmallTargets::QueryQuickContact(UWorld* World,ACharacter* Owner,const FTransform& Aim,
    const FVector& Start,float Reach,float Radius,FHitResult& OutHit)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(Melee_QuickContact);
    if(!World||!Owner||Reach<=0.f)return false;
    const FVector End=Start+Aim.GetUnitAxis(EAxis::X)*Reach;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickMeleeContact),false,Owner);
    const auto Shape=FCollisionShape::MakeSphere(Radius);
    bool bHit=World->SweepSingleByChannel(OutHit,Start,End,FQuat::Identity,ECC_Pawn,Shape,Params);
    // An opening leaf temporarily ignores Pawn for anti-crush. Attacks still
    // strike its intact glass through the same visibility channel as bullets.
    FHitResult GlassHit;
    if(World->SweepSingleByChannel(GlassHit,Start,End,FQuat::Identity,ECC_Visibility,Shape,Params)
        && Cast<UWardBreakableGlass>(GlassHit.GetComponent()) && (!bHit || GlassHit.Time<=OutHit.Time))
    {OutHit=GlassHit;bHit=true;}
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> SmallHits;
    World->SweepMultiByObjectType(SmallHits,Start,End,FQuat::Identity,Objects,Shape,Params);
    SmallHits.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});
    int32 CoverCandidates=0;
    for(const auto& Hit:SmallHits)
    {
        if(bHit&&Hit.Time>OutHit.Time)break;
        auto* Hand=LivingSmallHand(Hit.GetActor());
        if(!Hand||Hit.GetComponent()!=Hand->GetCapsuleComponent())continue;
        if(CoverCandidates++>=MaxCoverCandidates)break;
        FCollisionQueryParams Cover=Params;Cover.AddIgnoredActor(Hand);
        if(Covered(World,Start,Hit.ImpactPoint,Cover)||Covered(World,Aim.GetLocation(),Hit.ImpactPoint,Cover))continue;
        OutHit=Hit;bHit=true;break;
    }
    // A valid physical contact wins. The low sector supplies a miss, and still
    // returns at most one hit through the caller's existing damage pipeline.
    if(bHit && Cast<UWardBreakableGlass>(OutHit.GetComponent()))return true;
    if(bHit)
        if(const auto* Combat=OutHit.GetActor()?OutHit.GetActor()->FindComponentByClass<UMonsterCombatComponent>():nullptr;
            Combat&&!Combat->IsDead())return true;
    const TSet<TWeakObjectPtr<AActor>> AlreadyHit;
    const auto LowHits=QueryLowSector(World,Owner,Aim,Reach,AlreadyHit,false);
    if(!LowHits.IsEmpty()){OutHit=LowHits[0];return true;}
    return bHit;
}

TArray<FHitResult> MeleeSmallTargets::QueryQuickAreaContacts(UWorld* World,ACharacter* Owner,
    const FTransform& Aim,const FVector& Start,float Reach,float Radius)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(Melee_QuickAreaContact);
    TArray<FHitResult> Result;
    if(!World||!Owner||Reach<=0.f)return Result;
    const FVector End=Start+Aim.GetUnitAxis(EAxis::X)*Reach;
    const auto Shape=FCollisionShape::MakeSphere(Radius);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickMeleeAreaContact),false,Owner);
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_Pawn);
    TArray<FHitResult> Contacts;
    World->SweepMultiByObjectType(Contacts,Start,End,FQuat::Identity,Objects,Shape,Params);
    Contacts.Sort([](const FHitResult& A,const FHitResult& B){return A.Time<B.Time;});

    // Ignore bodies, not scenery: the original sphere still stops at the first world blocker.
    FCollisionQueryParams Cover=Params;
    for(const auto& Hit:Contacts)
        if(Cast<APawn>(Hit.GetActor()))Cover.AddIgnoredActor(Hit.GetActor());
    FHitResult Blocker;
    const bool bBlocked=World->SweepSingleByChannel(Blocker,Start,End,FQuat::Identity,ECC_Pawn,Shape,Cover);
    if(bBlocked && (Cast<UWardBreakableGlass>(Blocker.GetComponent())||Cast<AFPSIceWall>(Blocker.GetActor())))Result.Add(Blocker);
    TSet<TWeakObjectPtr<AActor>> Seen;
    for(const auto& Hit:Contacts)
    {
        if(bBlocked&&Hit.Time>Blocker.Time)break;
        auto* Target=Hit.GetActor();
        auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
        if(!Combat||Combat->IsDead()||!Target->CanBeDamaged()||Seen.Contains(Target))continue;
        if(const auto* Hand=LivingSmallHand(Target);Hand&&Hit.GetComponent()!=Hand->GetCapsuleComponent())continue;
        Seen.Add(Target);
        FCollisionQueryParams TargetCover=Cover;TargetCover.AddIgnoredActor(Target);
        if(Covered(World,Start,Hit.ImpactPoint,TargetCover)||Covered(World,Aim.GetLocation(),Hit.ImpactPoint,TargetCover))continue;
        Result.Add(Hit);
    }
    // Preserve the existing fallback condition and its range/arc; no new explosion radius.
    if(Result.IsEmpty())Result=QueryLowSector(World,Owner,Aim,Reach,{},true);
    return Result;
}
