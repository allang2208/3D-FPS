#include "RuneSwordHitQuery.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Character.h"
#include "Components/CapsuleComponent.h"
#include "Engine/OverlapResult.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "../Monsters/MonsterCombatComponent.h"

namespace
{
bool RuneSwordWorldOccludes(UWorld* World,AActor* Owner,AActor* Target,const FVector& Eye,const FVector& Point,bool bCleavePawns,
    const FCollisionQueryParams* SectorCover=nullptr)
{
    const FCollisionQueryParams Initial(SCENE_QUERY_STAT(RuneSwordCover),false,Owner);
    const FCollisionQueryParams& FirstQuery=SectorCover?*SectorCover:Initial;
    FHitResult Cover;
    if(!World->LineTraceSingleByChannel(Cover,Eye,Point,ECC_Visibility,FirstQuery))return false;
    if(Cover.GetActor()==Target)return false;
    if(!bCleavePawns||!Cover.GetActor()||!Cover.GetActor()->IsA<APawn>())return true;
    // Only an extra Pawn outside the broad-phase set needs a private retry list.
    // The common sector path reuses one immutable ignore list for every target.
    FCollisionQueryParams Q=FirstQuery;
    do
    {
        AActor* Blocker=Cover.GetActor();
        if(Blocker==Target)return false;
        // A cleave can reach another body; walls and other solid cover still stop it.
        if(!bCleavePawns || !Blocker || !Blocker->IsA<APawn>())return true;
        Q.AddIgnoredActor(Blocker);
    }while(World->LineTraceSingleByChannel(Cover,Eye,Point,ECC_Visibility,Q));
    return false;
}
}

TArray<FHitResult> RuneSwordCombat::QuerySector(UWorld* World,AActor* Owner,const FVector& Origin,const FVector& Forward,
    float Radius,float ArcDegrees,const TSet<TWeakObjectPtr<AActor>>& AlreadyHit)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(DashAttack_SectorQuery);
    TArray<FHitResult> Result;
    const auto* Character=Cast<ACharacter>(Owner);
    const float HalfHeight=Character?Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight():90.f;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(DashAttackSector),false,Owner);
    TArray<FOverlapResult> Overlaps;
    World->OverlapMultiByObjectType(Overlaps,Origin,FQuat::Identity,FCollisionObjectQueryParams::AllDynamicObjects,
        FCollisionShape::MakeBox(FVector(Radius,Radius,HalfHeight)),Q);
    // 扇区横扫本就允许穿过敌人。一次收集可穿透的Pawn，避免每个目标的
    // 遮挡射线都从第一只怪物起逐只重试（密集目标时接近N平方条射线）。
    TSet<AActor*> PawnSet;
    for(const auto& Overlap:Overlaps)
        if(auto* Pawn=Cast<APawn>(Overlap.GetActor()))PawnSet.Add(Pawn);
    const TArray<AActor*> SectorPawns=PawnSet.Array();
    FCollisionQueryParams SectorCover(SCENE_QUERY_STAT(DashAttackCover),false,Owner);
    SectorCover.AddIgnoredActors(SectorPawns);
    TSet<TWeakObjectPtr<AActor>> Found;
    for(const auto& Overlap:Overlaps)
    {
        auto* Target=Overlap.GetActor();auto* Shape=Overlap.GetComponent();
        if(!IsValid(Target)||!Shape||Target==Owner||!Target->CanBeDamaged()||AlreadyHit.Contains(Target)||Found.Contains(Target))continue;
        // 尸体不会进入下劈结算，不再为其做骨骼碰撞最近点与遮挡查询。
        if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&Combat->IsDead())continue;
        const auto Bounds=Shape->Bounds;
        const FVector Delta=Bounds.Origin-Origin;
        const float R=FMath::Max(Bounds.BoxExtent.X,Bounds.BoxExtent.Y),Distance=Delta.Size2D();
        if(Distance>Radius+R||FMath::Abs(Delta.Z)>HalfHeight+Bounds.BoxExtent.Z)continue;
        const float Angle=FMath::Acos(FMath::Clamp(float(FVector::DotProduct(Delta.GetSafeNormal2D(),Forward)),-1.f,1.f));
        const float FootprintAngle=FMath::Asin(FMath::Clamp(R/FMath::Max(Distance,1.f),0.f,1.f));
        if(Distance>R&&Angle>FMath::DegreesToRadians(ArcDegrees*.5f)+FootprintAngle)continue;
        FVector Point;
        if(Shape->GetClosestPointOnCollision(Origin,Point)<0.f)Point=Bounds.GetBox().GetClosestPointTo(Origin);
        if(RuneSwordWorldOccludes(World,Owner,Target,Origin,Point,true,&SectorCover))continue;
        FHitResult Hit(Target,Shape,Point,(Origin-Point).GetSafeNormal());
        Hit.ImpactPoint=Hit.Location=Point;Hit.TraceStart=Origin;Hit.TraceEnd=Point;
        Found.Add(Target);Result.Add(Hit);
    }
    return Result;
}

TArray<FHitResult> RuneSwordCombat::Query(UWorld* World,AActor* Owner,const FRuneSwordBladeSample& From,
    const FRuneSwordBladeSample& To,float Reach,const TSet<TWeakObjectPtr<AActor>>& AlreadyHit,
    const FRuneSwordTraceSettings& Settings)
{
    TArray<FHitResult> Result;
    TSet<TWeakObjectPtr<AActor>> Found;
    FCollisionQueryParams Initial(SCENE_QUERY_STAT(RuneSwordBlade),false,Owner);
    if(Settings.bCleavePawns)
        for(const auto& Weak:AlreadyHit)if(auto* Actor=Weak.Get();Actor && Actor->IsA<APawn>())Initial.AddIgnoredActor(Actor);
    // Overlapping lanes cover the complete blade, including short tip/root contacts.
    const int32 Lanes=FMath::Max(1,FMath::CeilToInt(FMath::Max((From.Tip-From.Base).Length(),(To.Tip-To.Base).Length())/Settings.Radius));
    for(int32 I=0;I<=Lanes;++I)
    {
        const float U=float(I)/Lanes;
        const FVector Start=FMath::Lerp(From.Base,From.Tip,U),End=FMath::Lerp(To.Base,To.Tip,U);
        FCollisionQueryParams Q=Initial;
        for(;;)
        {
            TArray<FHitResult> Hits;
            World->SweepMultiByChannel(Hits,Start,End,FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(Settings.Radius),Q);
            bool ContinuePastPawn=false;
            for(const auto& Hit:Hits)
            {
                AActor* Target=Hit.GetActor();
                if(!IsValid(Target) || Target==Owner)continue;
                if(Settings.bCleavePawns && Target->IsA<APawn>())
                {
                    Q.AddIgnoredActor(Target);
                    ContinuePastPawn|=Hit.bBlockingHit;
                }
                if(AlreadyHit.Contains(Target) || Found.Contains(Target) || !Target->CanBeDamaged())continue;
                const FVector Relative=Hit.ImpactPoint-To.Origin;
                const float Along=FVector::DotProduct(Relative,To.Forward);
                if(Relative.SizeSquared()>FMath::Square(Reach) || Along<0.f)continue;
                if(Settings.ForwardCorridorRadius>0.f &&
                    (Relative-To.Forward*Along).SizeSquared()>FMath::Square(Settings.ForwardCorridorRadius))continue;
                if(RuneSwordWorldOccludes(World,Owner,Target,To.Origin,Hit.ImpactPoint,Settings.bCleavePawns))continue;
                Found.Add(Target);Result.Add(Hit);
            }
            // Channel sweeps stop at the first blocking hit. Continue through a body,
            // with that pawn ignored, while retaining solid geometry as the stop.
            if(!ContinuePastPawn)break;
        }
    }
    if(!Settings.bCleavePawns && Result.Num()>1)
    {
        Result.Sort([&](const FHitResult& A,const FHitResult& B)
        {
            return FVector::DotProduct(A.ImpactPoint-To.Origin,To.Forward)<
                FVector::DotProduct(B.ImpactPoint-To.Origin,To.Forward);
        });
        Result.SetNum(1);
    }
    return Result;
}
