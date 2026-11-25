#include "StableRidingHorse.h"
#include "HorseRiderComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "TimerManager.h"

namespace HorseFollow
{
    // Existing Hills Recast profile with clearance for the shoulders and head.
    const FNavAgentProperties Agent(62.f,204.f);
    constexpr float StopDistance=162.f,ResumeDistance=212.f;
}

void AStableRidingHorse::ClearFollowRoute()
{
    if(PendingQuery!=INVALID_NAVQUERYID)
        if(auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
            Nav->AbortAsyncFindPathRequest(PendingQuery);
    PendingQuery=INVALID_NAVQUERYID;
    FollowPath.Reset();NextCorner=1;bDirectApproach=false;
}
void AStableRidingHorse::SetLeader(AFPSGAMECharacter* NewLeader)
{
    if(!HasAuthority()||(NewLeader&&(Rider||IsRetreating())))return;
    if(bFollowing)GetCharacterMovement()->bCanWalkOffLedges=bPreviouslyAllowedLedges;
    ClearFollowRoute();
    if(bNavInvoker){UNavigationSystemV1::UnregisterNavigationInvoker(*this);bNavInvoker=false;}
    Leader=NewLeader;bFollowing=NewLeader!=nullptr;bAtHeel=false;
    bNeedsRecall=false;NextFollowFeedback=0.;NoProgressSince=GetWorld()->GetTimeSeconds();
    ProgressLocation=GetActorLocation();
    NextPlanTime=0.;BlockedSeconds=0.f;
    Halt();
    if(bFollowing)
    {
        bPreviouslyAllowedLedges=GetCharacterMovement()->bCanWalkOffLedges;
        GetCharacterMovement()->bCanWalkOffLedges=false;
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        if(auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
        {
            const int32 Profile=Nav->GetSupportedAgentIndex(HorseFollow::Agent);
            if(Profile!=INDEX_NONE)
            {
                FNavAgentSelector Selected;Selected.Empty();Selected.Set(Profile);Selected.MarkInitialized();
                UNavigationSystemV1::RegisterNavigationInvoker(*this,3000.f,4200.f,Selected);
                bNavInvoker=true;
            }
        }
    }
    else if(!Rider)GetCharacterMovement()->DisableMovement();
    ForceNetUpdate();
}
void AStableRidingHorse::EndPlay(EEndPlayReason::Type Reason)
{
    CacheKeeperCondition();
    GetWorldTimerManager().ClearTimer(RestRecoveryTimer);
    if(bFollowing)SetLeader(nullptr);
    Super::EndPlay(Reason);
}
void AStableRidingHorse::PlanFollowPath(const FVector& Goal)
{
    PlannedGoal=Goal;
    const float Distance=FVector::Dist2D(GetNavAgentLocation(),Goal);
    const bool NearEnough=Distance<=(bAtHeel?HorseFollow::ResumeDistance:HorseFollow::StopDistance);
    bDirectApproach=BlockedSeconds<.45f&&WalkableApproach(Goal);
    bAtHeel=NearEnough&&bDirectApproach;
    NextPlanTime=GetWorld()->GetTimeSeconds()+(bAtHeel?.45f:.65f);
    if(bDirectApproach){FollowPath.Reset();return;}
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if(!Nav)return;
    const FVector Feet=GetNavAgentLocation();
    const auto* Data=Nav->GetNavDataForProps(HorseFollow::Agent,Feet);
    if(!Data||!Data->GetConfig().IsEquivalent(HorseFollow::Agent))return;
    const FVector Extent(94,94,65);
    FNavLocation From,To;
    if(!Nav->ProjectPointToNavigation(Feet,From,Extent,Data)||!Nav->ProjectPointToNavigation(Goal,To,Extent,Data))
    {FollowPath.Reset();return;}
    FPathFindingQuery Query(this,*Data,From.Location,To.Location,Data->GetDefaultQueryFilter());
    Query.SetAllowPartialPaths(true);
    PendingQuery=Nav->FindPathAsync(HorseFollow::Agent,Query,
        FNavPathQueryDelegate::CreateUObject(this,&ThisClass::FinishFollowQuery));
}
void AStableRidingHorse::FinishFollowQuery(uint32 Id,ENavigationQueryResult::Type Result,FNavPathSharedPtr Path)
{
    if(Id!=PendingQuery||!bFollowing)return;
    PendingQuery=INVALID_NAVQUERYID;
    NextCorner=1;
    FollowPath=(Result==ENavigationQueryResult::Success&&Path.IsValid()&&Path->IsValid())?MoveTemp(Path):nullptr;
    BlockedSeconds=0.f;
}
void AStableRidingHorse::Follow(float Delta,float MovementScale)
{
    auto* Move=GetCharacterMovement();
    const auto* LeaderHealth=IsValid(Leader)?Leader->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!IsValid(Leader)||!Leader->GetController()||(LeaderHealth&&LeaderHealth->IsDead()))
    {SetLeader(nullptr);return;}
    const FVector Goal=Leader->GetNavAgentLocation(),Feet=GetNavAgentLocation();
    const float Distance=FVector::Dist2D(Feet,Goal);
    const double Now=GetWorld()->GetTimeSeconds();
    const bool GoalMoved=FVector::DistSquared(PlannedGoal,Goal)>FMath::Square(48.f);
    const bool RouteValid=FollowPath.IsValid()&&FollowPath->IsValid();
    const bool Near=Distance<HorseFollow::StopDistance+32.f;
    if(!PendingQuery&&Now>=NextPlanTime&&
        (GoalMoved||(!RouteValid&&!bAtHeel)||(!bAtHeel&&Near)||BlockedSeconds>.45f||
         (bAtHeel&&Distance>HorseFollow::ResumeDistance)))
        PlanFollowPath(Goal);
    if(bAtHeel){Move->StopMovementImmediately();return;}
    FVector Waypoint;
    if(bDirectApproach)
    {
        Waypoint=PlannedGoal;
        if(Near&&Distance<=HorseFollow::StopDistance&&FVector::DistSquared(Goal,PlannedGoal)<FMath::Square(55.f))
        {bAtHeel=true;Move->StopMovementImmediately();return;}
    }
    else if(FollowPath.IsValid()&&FollowPath->IsValid())
    {
        const auto& Points=FollowPath->GetPathPoints();
        while(Points.IsValidIndex(NextCorner)&&FVector::Dist2D(Feet,Points[NextCorner].Location)<32.f)
            ++NextCorner;
        if(!Points.IsValidIndex(NextCorner)){FollowPath.Reset();Move->StopMovementImmediately();return;}
        Waypoint=Points[NextCorner].Location;
    }
    else {Move->StopMovementImmediately();return;}

    const FVector Direction=(Waypoint-Feet).GetSafeNormal2D();
    const float Heading=GetActorRotation().Yaw;
    const float Error=FMath::FindDeltaAngleDegrees(Heading,Direction.Rotation().Yaw);
    // Back out of a tight stall when the next corner lies directly behind the horse.
    const bool Reverse=FMath::Abs(Error)>120.f&&FVector::Dist2D(Feet,Waypoint)<280.f;
    const float Aim=Reverse?FMath::UnwindDegrees(Error+180.f):Error;
    const float TurnStep=105.f*Traits.TurnScale()*Delta*MovementScale;
    const float Turn=FMath::Clamp(Aim,-TurnStep,TurnStep);
    const FRotator Facing(0,Heading+Turn,0);
    const bool CanTurn=FMath::Abs(Turn)<.05f||ClearBody(FVector::ZeroVector,Facing);
    if(CanTurn)SetActorRotation(Facing);
    const float CatchUp=FMath::Clamp(float(Leader->GetVelocity().Size2D())+100.f,520.f,860.f);
    const float Cruise=FMath::Lerp(225.f,CatchUp,FMath::SmoothStep(280.f,680.f,Distance));
    Move->MaxWalkSpeed=(Reverse?125.f:FMath::Min(bExhausted?220.f:Cruise,FMath::Max(90.f,(Distance-105.f)*1.5f)))*Traits.SpeedScale()*MovementScale;
    const FVector Advance=GetActorForwardVector()*(Reverse?-1.f:1.f);
    if(FMath::Abs(Aim)<56.f&&ClearBody(Advance*Move->MaxWalkSpeed*Delta,GetActorRotation()))
    {
        AddMovementInput(Advance,1.f,true);
        BlockedSeconds=0.f;
    }
    else
    {
        Move->StopMovementImmediately();
        if(!CanTurn||FMath::Abs(Aim)<56.f)BlockedSeconds+=Delta;
        // Give the shoulders turning room when the nav corner hugs a jamb.
        if(!CanTurn&&BlockedSeconds>.18f&&ClearBody(-Advance*FMath::Max(8.f,90.f*Delta),GetActorRotation()))
        {Move->MaxWalkSpeed=90.f*MovementScale;AddMovementInput(-Advance,1.f,true);}
    }
}

bool AStableRidingHorse::IsFarFrom(const APawn& Pawn) const
{
    return FVector::DistSquared(GetActorLocation(),Pawn.GetActorLocation())>=FMath::Square(FarDistance);
}
void AStableRidingHorse::UpdateFollowFeedback(double Now,double Distance)
{
    auto* OwnerPawn=KeeperModel.IsValid()?KeeperModel->RuntimePawn():nullptr;
    auto* Ride=OwnerPawn?OwnerPawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    if(!Ride || Ride->GetOwnedHorse()!=this)return;
    const bool FollowingOwner=Leader==OwnerPawn;
    const FVector Here=GetActorLocation();
    const bool Advanced=FVector::DistSquared2D(Here,ProgressLocation)>=FMath::Square(80.);
    if(!FollowingOwner || Advanced || Distance<600.){NoProgressSince=Now;ProgressLocation=Here;}
    const bool Far=Distance>=FarDistance;
    const bool Blocked=FollowingOwner && Distance>=600. && Now-NoProgressSince>=8.;
    if(!bNeedsRecall && (Far||Blocked))
    {
        bNeedsRecall=true;ForceNetUpdate();
        Ride->ClientHorseNotice(Far?TEXT("马匹已远离，按 X 再次召唤"):TEXT("马匹跟随受阻，按 X 再次召唤"));
    }
    else if(bNeedsRecall && !Far && Distance<3000. && (!FollowingOwner || Distance<400. || Advanced))
    {bNeedsRecall=false;ForceNetUpdate();}
}
