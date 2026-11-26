#include "UnknownHumanoid.h"
#include "MonsterAIController.h"
#include "../Skills/MagicOcclusion.h"
#include "Components/CapsuleComponent.h"
#include "CoreGlobals.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "MonsterCombatComponent.h"

namespace
{
bool TakeCrowdBudget(bool Yield)
{
    static uint64 Frame=MAX_uint64;
    static uint8 Queries=0, Steps=0;
    if(Frame!=GFrameCounter){Frame=GFrameCounter;Queries=Steps=0;}
    uint8& Count=Yield?Steps:Queries;
    if(Count>=(Yield?2:4))return false;
    ++Count;return true;
}
bool NearFloor(FVector A,FVector B) { return FMath::Abs(A.Z-B.Z)<75.f; }
}

void AUnknownHumanoid::GatherCrowd(FVector Center,float Radius,TArray<AUnknownHumanoid*>& Out) const
{
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByObjectType(Hits,Center,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeSphere(Radius),FCollisionQueryParams(SCENE_QUERY_STAT(UnknownCrowd),false,this));
    for(const auto& Hit:Hits)
    {
        auto* Ally=Cast<AUnknownHumanoid>(Hit.GetActor());
        if(Ally && Ally!=this && !Ally->Dead() && Hit.GetComponent()==Ally->GetCapsuleComponent())Out.AddUnique(Ally);
    }
    Out.Sort([&](const AUnknownHumanoid& A,const AUnknownHumanoid& B)
        {return FVector::DistSquared(A.GetNavAgentLocation(),Center)<FVector::DistSquared(B.GetNavAgentLocation(),Center);});
    if(Out.Num()>48)Out.SetNum(48,EAllowShrinking::No);
}

float AUnknownHumanoid::CrowdSpaceCost(FVector Point,const TArray<AUnknownHumanoid*>& Allies) const
{
    const double Now=ServerTime();
    float Cost=0.f;
    for(const auto* Ally:Allies)
    {
        const float Radii=GetCapsuleComponent()->GetScaledCapsuleRadius()+Ally->GetCapsuleComponent()->GetScaledCapsuleRadius();
        const auto Space=[&](FVector Other,float Clearance)
        {
            if(!NearFloor(Point,Other))return true;
            const float Distance=FVector::Dist2D(Point,Other);
            if(Distance<Radii+Clearance)return false;
            Cost=FMath::Max(Cost,FMath::Max(0.f,Radii+180.f-Distance)*2.f);
            return true;
        };
        if(!Space(Ally->GetNavAgentLocation(),18.f))return MAX_flt;
        // Existing plans are local reservations, even before their owners arrive.
        if(Ally->TacticalTarget.IsValid() && Ally->Position!=EUnknownPosition::Open &&
            (!Space(Ally->FiringPoint,45.f) || (Ally->bHasCover&&!Space(Ally->CoverPoint,45.f))))return MAX_flt;
        if(Now<Ally->CrowdYieldUntil && !Space(Ally->CrowdYieldPoint,35.f))return MAX_flt;
        if(Now<Ally->BypassUntil && !Space(Ally->BypassPoint,30.f))return MAX_flt;
        if(Ally->bSearchingPoint && !Space(Ally->SearchPoint,25.f))return MAX_flt;
    }
    return Cost;
}

bool AUnknownHumanoid::CanYieldToCrowd() const
{
    const auto* AI=Cast<AMonsterAIController>(GetController());
    return AI && AI->bDecisionEnabled && IsActorTickEnabled() && !Dead() && !Controlled() &&
        (!Busy() || CanPursueDuringAction(TacticalTarget.Get(),bTacticalTargetVisible));
}

bool AUnknownHumanoid::FindCrowdYield(AUnknownHumanoid& Passer,FVector Direction,FVector& Point)
{
    if(!Direction.Normalize())return false;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Feet=GetNavAgentLocation();
    const auto* Data=Nav?Nav->GetNavDataForProps(GetNavAgentPropertiesRef(),Feet):nullptr;
    if(!Data)return false;
    const auto* AI=Cast<AMonsterAIController>(GetController());
    const auto* Capsule=GetCapsuleComponent();
    const float HomeDistance=FVector::Dist2D(Home,Feet);
    // An encounter may legally retain combat outside the ordinary home leash.
    // Still allow its local doorway sidestep without authorising a new chase.
    const float HomeLimit=HomeDistance>Combat->LeashRange()?HomeDistance+300.f:Combat->LeashRange()-40.f;
    const float Radius=Capsule->GetScaledCapsuleRadius(),Half=Capsule->GetScaledCapsuleHalfHeight();
    const float Step=GetCharacterMovement()->MaxStepHeight;
    const auto TravelShape=FCollisionShape::MakeCapsule(Radius,FMath::Max(Radius,Half-Step*.5f));
    const FVector Lift(0,0,Step+TravelShape.GetCapsuleHalfHeight()+3.f);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(UnknownYieldSpace),false,this);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const FVector Across=FVector::CrossProduct(FVector::UpVector,Direction);
    const float Offset=FVector::DotProduct(Feet-Passer.GetNavAgentLocation(),Across);
    const float Side=FMath::Abs(Offset)>10.f?(Offset>0?1.f:-1.f):((GetUniqueID()&1)?1.f:-1.f);
    const FVector Offsets[]={Across*Side*120.f,Across*Side*200.f,Across*-Side*120.f,
        Across*-Side*200.f,Direction*170.f,Direction*300.f};
    TArray<AUnknownHumanoid*> Allies;
    GatherCrowd(Feet,750.f,Allies);
    float Best=MAX_flt;
    for(int32 I=0;I<UE_ARRAY_COUNT(Offsets);++I)
    {
        FNavLocation OnNav;
        const FVector Desired=Feet+Offsets[I];
        if(!Nav->ProjectPointToNavigation(Desired,OnNav,FVector(35,35,55),Data) ||
            !NearFloor(Feet,OnNav.Location) || FVector::Dist2D(Feet,OnNav.Location)<75.f ||
            FVector::Dist2D(Home,OnNav.Location)>HomeLimit || ShouldAvoidTravelPoint(OnNav.Location) ||
            (AI&&AI->ShouldAvoidNavigationGoal(OnNav.Location)))continue;
        const float Space=CrowdSpaceCost(OnNav.Location,Allies);
        if(Space==MAX_flt)continue;
        FVector Edge;
        if(Data->Raycast(Feet,OnNav.Location,Edge,Data->GetDefaultQueryFilter(),GetController()) ||
            GetWorld()->SweepTestByChannel(Feet+Lift,OnNav.Location+Lift,FQuat::Identity,
                Capsule->GetCollisionObjectType(),TravelShape,Query,Response) ||
            GetWorld()->OverlapBlockingTestByChannel(OnNav.Location+FVector(0,0,Half+3.f),FQuat::Identity,
                Capsule->GetCollisionObjectType(),FCollisionShape::MakeCapsule(Radius,Half),Query,Response))continue;
        if((bRetreating||bBowBlades) && TacticalTarget.IsValid())
        {
            const FVector Enemy=bTacticalTargetVisible?TacticalTarget->GetNavAgentLocation():PlannedTarget;
            if(FMath::PointDistToSegment(Enemy,Feet,OnNav.Location)<FMath::Min(float(FVector::Dist2D(Feet,Enemy))*.8f,350.f))continue;
        }
        // Prefer a stable side pocket. Backing up is reserved for a doorway
        // too narrow to pass shoulder to shoulder; all steps stay on navmesh.
        const float Score=FVector::Dist2D(Feet,OnNav.Location)+Space+(I>=4?160.f:I>=2?45.f:0.f);
        if(Score<Best){Best=Score;Point=OnNav.Location;}
    }
    return Best<MAX_flt;
}

void AUnknownHumanoid::HoldForCrowd(AMonsterAIController& AI)
{
    if(AI.GetMoveStatus()==EPathFollowingStatus::Moving)
    {
        CrowdPausedRequest=AI.GetCurrentMoveRequestID();
        AI.PauseMove(CrowdPausedRequest);
    }
    bSprintIntent=false;
    // Waiting for a teammate is not a failed wall route. Keep the exact
    // paused request so opening the doorway does not rebuild the path.
    LastTravelSample=LastTravelCall=ServerTime();
    TravelSample=GetNavAgentLocation(); RemainingTravel=MAX_flt;
}

bool AUnknownHumanoid::HandleCrowdTraffic(AMonsterAIController& AI,FVector Goal,bool bTravel)
{
    const double Now=ServerTime();
    const FVector Feet=GetNavAgentLocation();
    CrowdMoveUntil=bTravel?Now+.4:0.;
    if(bTravel)
    {
        const FVector Next=AI.GetImmediateMoveDestination();
        const bool OnPath=AI.GetMoveStatus()==EPathFollowingStatus::Moving || AI.GetMoveStatus()==EPathFollowingStatus::Paused;
        CrowdMoveDirection=((OnPath&&FVector::DistSquared2D(Feet,Next)>900.)?Next-Feet:Goal-Feet).GetSafeNormal2D();
    }
    if(!CanYieldToCrowd())return false;
    if(Now<CrowdYieldUntil)
    {
        const auto* Passer=CrowdPasser.Get();
        const bool Urgent=(bRetreating||bBowBlades) && Passer && Passer->CanYieldToCrowd() &&
            !Passer->bRetreating && !Passer->bBowBlades && bTacticalTargetVisible && TacticalTarget.IsValid() &&
            FVector::DistSquared2D(Feet,TacticalTarget->GetNavAgentLocation())<FMath::Square(360.f);
        const bool Passed=!Passer || Passer->Dead() || FVector::DistSquared2D(Feet,Passer->GetNavAgentLocation())>FMath::Square(480.f) ||
            FVector::DotProduct(Feet-Passer->GetNavAgentLocation(),Passer->CrowdMoveDirection)<-110.f;
        if(!Passed && !Urgent && !AI.ShouldAvoidNavigationGoal(CrowdYieldPoint))
        {
            bSprintIntent=false;
            if(FVector::DistSquared2D(Feet,CrowdYieldPoint)<FMath::Square(30.f) && FMath::Abs(Feet.Z-CrowdYieldPoint.Z)<=45.f)HoldForCrowd(AI);
            else
            {
                if(CrowdPausedRequest.IsValid()){AI.ResumeMove(CrowdPausedRequest);CrowdPausedRequest=FAIRequestID::InvalidRequest;}
                AI.NavigateTo(CrowdYieldPoint,20.f,.2f);
                LastTravelSample=LastTravelCall=Now; TravelSample=Feet; RemainingTravel=MAX_flt;
            }
            return true;
        }
        CrowdYieldUntil=0.; CrowdPasser.Reset();
    }
    if(Now<CrowdWaitUntil){HoldForCrowd(AI);return true;}
    if(CrowdPausedRequest.IsValid()){AI.ResumeMove(CrowdPausedRequest);CrowdPausedRequest=FAIRequestID::InvalidRequest;}
    if(Now<NextCrowdCheck)return false;
    if(!TakeCrowdBudget(false)){NextCrowdCheck=Now+FMath::FRandRange(.04f,.09f);return false;}
    NextCrowdCheck=Now+FMath::FRandRange(.14f,.22f);
    TArray<AUnknownHumanoid*> Allies;
    GatherCrowd(Feet,400.f,Allies);
    const int32 Partner=Allies.IndexOfByKey(CrowdBlocker.Get());
    if(Partner>0)Allies.Swap(0,Partner); // Finish resolving this pair before choosing another nearby partner.
    const FVector OwnDirection=bTravel?CrowdMoveDirection:FVector::ZeroVector;
    for(auto* Ally:Allies)
    {
        const FVector OtherFeet=Ally->GetNavAgentLocation();
        if(!NearFloor(Feet,OtherFeet))continue;
        const bool OtherMoving=Now<Ally->CrowdMoveUntil || Ally->GetVelocity().SizeSquared2D()>900.f;
        const FVector OtherDirection=Now<Ally->CrowdMoveUntil?Ally->CrowdMoveDirection:Ally->GetVelocity().GetSafeNormal2D();
        const float Radii=GetCapsuleComponent()->GetScaledCapsuleRadius()+Ally->GetCapsuleComponent()->GetScaledCapsuleRadius();
        const float Ahead=FVector::DotProduct(OtherFeet-Feet,OwnDirection);
        const bool SameDirection=bTravel && OtherMoving && FVector::DotProduct(OwnDirection,OtherDirection)>.65f;
        if(SameDirection && Ahead<=0.f)continue; // The leader never yields backwards into its queue.
        const float LookAhead=FMath::Clamp(float(GetVelocity().Size2D())*.35f+Radii,140.f,300.f);
        const bool Blocked=bTravel && Ahead>0.f &&
            FMath::PointDistToSegment(OtherFeet,Feet,Feet+OwnDirection*LookAhead)<Radii+22.f;
        const bool Incoming=OtherMoving && FVector::DotProduct(Feet-OtherFeet,OtherDirection)>0.f &&
            FMath::PointDistToSegment(Feet,OtherFeet,OtherFeet+OtherDirection*250.f)<Radii+22.f;
        if(!Blocked&&!Incoming)continue;
        FHitResult Wall;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(UnknownCrowdWall),false,this);
        Query.AddIgnoredActor(Ally);
        if(MagicOcclusion::TraceBlocker(GetWorld(),Feet+FVector(0,0,80),OtherFeet+FVector(0,0,80),Query,Wall,this))continue;
        if(CrowdBlocker.Get()!=Ally){CrowdBlocker=Ally;CrowdBlockedSince=Now;}
        const bool Queue=SameDirection && (Ally->GetVelocity().SizeSquared2D()>900.f || Now-Ally->LastTravelSample<.6);
        if(Queue && Ahead>Radii+40.f)
        {
            // Match a slower leader before contact rather than repeatedly
            // stopping/restarting a sprint at the doorway. Animation still
            // samples the actual movement velocity and its continuous gait.
            CrowdSpeedLimit=Ally->GetVelocity().Size2D()+FMath::Max(0.f,Ahead-Radii-55.f)*1.6f;
            CrowdSpeedUntil=Now+.4;
            return false;
        }
        const int32 Priority=(bRetreating||bBowBlades)?2:bTravel?1:0;
        const int32 OtherPriority=!Ally->CanYieldToCrowd()?3:(Ally->bRetreating||Ally->bBowBlades)?2:OtherMoving?1:0;
        const bool GiveWay=!Queue && Now>=Ally->CrowdYieldUntil &&
            (SameDirection || Priority<OtherPriority || (Priority==OtherPriority && GetUniqueID()>Ally->GetUniqueID()));
        if(GiveWay && TakeCrowdBudget(true) && FindCrowdYield(*Ally,OtherMoving?OtherDirection:OwnDirection,CrowdYieldPoint))
        {
            CrowdPasser=Ally;
            CrowdYieldUntil=Now+FMath::Clamp(float(FVector::Dist2D(Feet,CrowdYieldPoint))/FMath::Max(150.f,WalkSpeed)+.65f,1.f,2.f);
            CrowdWaitUntil=CrowdSpeedUntil=0.; BypassUntil=0.;
            if(Position!=EUnknownPosition::Open)LeaveCover(false);
            bSprintIntent=false;
            AI.NavigateTo(CrowdYieldPoint,20.f,.2f);
            LastTravelSample=LastTravelCall=Now; TravelSample=Feet; RemainingTravel=MAX_flt;
            return true;
        }
        // A moving queue or a committed yielding step gets a short pause.
        // A pair that cannot clear each other eventually returns to ordinary
        // blocked-route recovery rather than masking a permanent deadlock.
        if(Now-CrowdBlockedSince<1.1 || Now<Ally->CrowdYieldUntil)
        {CrowdWaitUntil=Now+.24;HoldForCrowd(AI);return true;}
        return false;
    }
    CrowdBlocker.Reset(); CrowdBlockedSince=-1.;
    return false;
}
