#include "MonsterAIController.h"
#include "MonsterNavigationCache.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "Engine/World.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "CoreGlobals.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
bool TakePursuitApproachBudget()
{
    static uint64 Frame=MAX_uint64;
    static uint8 Count=0;
    if(Frame!=GFrameCounter){Frame=GFrameCounter;Count=0;}
    if(Count>=2)return false;
    ++Count;return true;
}
}

bool AMonsterAIController::ShouldAvoidNavigationGoal(const FVector& Goal,float Radius) const
{
    return GetWorld()&&GetWorld()->GetTimeSeconds()<FailedPursuitUntil
        &&FMath::Abs(Goal.Z-FailedPursuitDestination.Z)<75.f
        &&FVector::DistSquared2D(Goal,FailedPursuitDestination)<FMath::Square(Radius);
}

void AMonsterAIController::RememberNavigationFailure(const FVector& Destination)
{
    bNavigationFailed=true;
    FailedPursuitDestination=Destination;
    FailedPursuitUntil=GetWorld()->GetTimeSeconds()+2.;
}

void AMonsterAIController::OnMoveCompleted(FAIRequestID RequestID,const FPathFollowingResult& Result)
{
    if(PursuitRequest.IsValid()&&RequestID==PursuitRequest)
    {
        PursuitRequest=FAIRequestID::InvalidRequest;
        if(Result.Code==EPathFollowingResult::Blocked||Result.Code==EPathFollowingResult::OffPath
            ||Result.Code==EPathFollowingResult::Invalid)RememberNavigationFailure(PursuitDestination);
        else if(Result.IsSuccess())bNavigationFailed=false;
        // Aborted includes attack/control stops and replacement requests, not failed routes.
    }
    Super::OnMoveCompleted(RequestID,Result);
}

void AMonsterAIController::NavigateTo(FVector Destination,float Acceptance,float RepathInterval)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_NavigateAttempt);
    auto* PawnCharacter=Cast<ACharacter>(GetPawn());
    if(!HasAuthority()||!PawnCharacter)return;
    NotePursuitAttempt();
    const float Now=GetWorld()->GetTimeSeconds();
    const bool Following=GetMoveStatus()==EPathFollowingStatus::Moving&&PursuitRequest.IsValid()
        &&PursuitRequest==GetCurrentMoveRequestID();
    const FVector Position=PawnCharacter->GetActorLocation();
    if(!Following||FVector::DistSquared2D(Position,PursuitProgressPosition)>FMath::Square(25.f))
    {PursuitProgressPosition=Position;PursuitProgressTime=Now;}
    const bool Stalled=bHillsPursuitRecovery&&Following&&Now-PursuitProgressTime>=3.;
    if(Now-LastMove<RepathInterval)return;
    Acceptance=FMath::Max(0.f,Acceptance);
    if(Following&&!Stalled
        &&FVector::DistSquared(Destination,LastDestination)<FMath::Square(45.f)
        &&FMath::IsNearlyEqual(Acceptance,LastPursuitAcceptance,5.f))return;
    TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_NavigateAdmitted);
    LastMove=Now;LastDestination=Destination;LastPursuitAcceptance=Acceptance;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto& Agent=GetNavAgentPropertiesRef();
    const FVector Feet=GetNavAgentLocation();
    const auto* Data=Nav?Nav->GetNavDataForProps(Agent,Feet):nullptr;
    auto* Cache=GetWorld()->GetSubsystem<UMonsterNavigationCache>();
    const auto StopFailedMove=[&]()
    {
        PursuitRequest=FAIRequestID::InvalidRequest;
        StopMovement();RememberNavigationFailure(Destination);
    };
    // Shared pursuit also drives shrine objectives (which are not player targets).
    // A valid request can be physically blocked by the exit crowd or a late prop.
    // Retire it and use the existing bounded alternate-approach search instead of
    // waiting forever merely because PathFollowing still reports Moving.
    if(Stalled)
    {
        StopFailedMove();PursuitProgressPosition=Position;PursuitProgressTime=Now;
    }
    if(!Data || (bHillsPursuitRecovery && (Data->GetConfig().AgentRadius+KINDA_SMALL_NUMBER<Agent.AgentRadius
        || Data->GetConfig().AgentHeight+KINDA_SMALL_NUMBER<Agent.AgentHeight)))
    {StopFailedMove();return;}
    const auto Submit=[&](const FVector& Goal,float Reach)
    {
        TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_MoveToLocation);
        // MoveTo may synchronously abort the old request. It must not overwrite this receipt.
        PursuitRequest=FAIRequestID::InvalidRequest;
        ++NavigationRequests;
        const auto Result=MoveToLocation(Goal,Reach,false,true,false,false,nullptr,false);
        if(Result==EPathFollowingRequestResult::RequestSuccessful)
        {
            PursuitRequest=GetCurrentMoveRequestID();PursuitDestination=Destination;
            bNavigationFailed=false;
        }
        return Result;
    };
    FNavLocation Goal;
    const float XY=FMath::Max(100.f,Agent.AgentRadius*2.f+30.f);
    const bool Projected=Cache->Project(Nav,Data,Destination,FVector(XY,XY,100),Goal);
    if(Projected&&!ShouldAvoidNavigationGoal(Destination))
    {
        // The triangle inequality keeps the final stop within the real target's range.
        // A wide-agent projection already displaced toward us cannot add its error to Reach.
        const float Reach=FMath::Max(0.f,Acceptance-float(FVector::Dist2D(Goal.Location,Destination)));
        const auto Result=Submit(Goal.Location,Reach);
        if(Result==EPathFollowingRequestResult::RequestSuccessful)return;
        if(Result==EPathFollowingRequestResult::AlreadyAtGoal
            &&FVector::Dist2D(Feet,Destination)<=Acceptance+5.f&&FMath::Abs(Feet.Z-Destination.Z)<=50.f)
        {bNavigationFailed=false;return;}
    }
    // A projected endpoint outside the real stop range, or an obstructed route,
    // needs another approach. Admit at most two batches/frame and two paths/batch.
    if(!TakePursuitApproachBudget())return;
    TRACE_CPUPROFILER_EVENT_SCOPE(MonsterAI_AlternateApproach);
    FVector NearSide=(Feet-Destination).GetSafeNormal2D();
    if(NearSide.IsNearlyZero())NearSide=PawnCharacter->GetActorForwardVector().GetSafeNormal2D();
    const auto* Capsule=PawnCharacter->GetCapsuleComponent();
    const FVector CenterOffset=PawnCharacter->GetActorLocation()-Feet;
    const float Ring=FMath::Max(0.f,Acceptance-10.f);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterApproachSpace),false,PawnCharacter);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const auto Shape=FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight());
    int32 Paths=0;
    const uint8 Offset=ApproachSearchOffset;
    ApproachSearchOffset=(ApproachSearchOffset+2)%8;
    for(uint8 I=0;I<8&&Paths<2;++I)
    {
        const FVector Desired=Destination+NearSide.RotateAngleAxis(((Offset+I)%8)*45.f,FVector::UpVector)*Ring;
        FNavLocation Point;
        if(!Cache->Project(Nav,Data,Desired,FVector(FMath::Max(45.f,Agent.AgentRadius),FMath::Max(45.f,Agent.AgentRadius),60.f),Point)
            ||FMath::Abs(Point.Location.Z-Destination.Z)>50.f
            ||FVector::Dist2D(Point.Location,Destination)>FMath::Max(0.f,Acceptance-5.f))continue;
        if(GetWorld()->OverlapBlockingTestByChannel(Point.Location+CenterOffset+FVector(0,0,3.f),
            FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Query,Response))continue;
        ++Paths;
        const auto Result=Submit(Point.Location,FMath::Min(5.f,Acceptance));
        if(Result==EPathFollowingRequestResult::RequestSuccessful)return;
        if(Result==EPathFollowingRequestResult::AlreadyAtGoal
            &&FVector::Dist2D(Feet,Destination)<=Acceptance+5.f&&FMath::Abs(Feet.Z-Destination.Z)<=50.f)
        {bNavigationFailed=false;return;}
    }
    StopFailedMove();
}
