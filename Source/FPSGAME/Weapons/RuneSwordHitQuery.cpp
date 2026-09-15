#include "RuneSwordHitQuery.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

namespace
{
bool RuneSwordWorldOccludes(UWorld* World,AActor* Owner,AActor* Target,const FVector& Eye,const FVector& Point,bool bCleavePawns)
{
    FCollisionQueryParams Q(SCENE_QUERY_STAT(RuneSwordCover),false,Owner);
    FHitResult Cover;
    while(World->LineTraceSingleByChannel(Cover,Eye,Point,ECC_Visibility,Q))
    {
        AActor* Blocker=Cover.GetActor();
        if(Blocker==Target)return false;
        // A cleave can reach another body; walls and other solid cover still stop it.
        if(!bCleavePawns || !Blocker || !Blocker->IsA<APawn>())return true;
        Q.AddIgnoredActor(Blocker);
    }
    return false;
}
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
