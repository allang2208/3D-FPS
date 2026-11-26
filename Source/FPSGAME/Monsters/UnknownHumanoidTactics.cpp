#include "UnknownHumanoid.h"
#include "UnknownHumanoidBow.h"
#include "UnknownSpellCombat.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "MonsterCombatComponent.h"
#include "MonsterAIController.h"
#include "GameFramework/PlayerController.h"
#include "../Skills/MagicOcclusion.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "Navigation/PathFollowingComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "../Combat/RangedAttackQuery.h"

namespace
{
    bool AtFootPoint(const FVector& Feet,const FVector& Point,float Radius)
    {
        return FMath::Abs(Feet.Z-Point.Z)<=45.f && FVector::DistSquared2D(Feet,Point)<=FMath::Square(Radius);
    }

    bool FitsAt(const ACharacter& Pawn,const FVector& Feet)
    {
        const auto* Capsule=Pawn.GetCapsuleComponent();
        const auto Shape=FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight());
        return !Pawn.GetWorld()->OverlapBlockingTestByChannel(Feet+FVector(0,0,Shape.GetCapsuleHalfHeight()+4.f),
            FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,FCollisionQueryParams(SCENE_QUERY_STAT(UnknownFootSpace),false,&Pawn),
            FCollisionResponseParams(Capsule->GetCollisionResponseToChannels()));
    }

    bool CanPlanThisFrame()
    {
        // A group spawned together shares the synchronous path-search budget.
        static uint64 LastFrame=MAX_uint64;
        if(LastFrame==GFrameCounter)return false;
        LastFrame=GFrameCounter;
        return true;
    }
}

void AUnknownHumanoid::UpdateBowTactics(APawn* Target,bool bVisible)
{
    if (Loadout.Role!=EUnknownRole::Bow || !HasAuthority() || Controlled()) return;
    PrepareArchery(); if (!Archery) return;
    auto& B=*Archery; const double Now=ServerTime();
    if (Dead()) return;
    bool Threat=false;
    bool Safe=!Target;
    if (Target && bVisible)
    {
        const FVector Relative=Target->GetActorLocation()-GetActorLocation();
        const float Distance=Relative.Size2D();
        const float Closing=-FVector::DotProduct(Target->GetVelocity()-GetVelocity(),Relative.GetSafeNormal2D());
        Threat=Distance-FMath::Max(0.f,Closing)*.45f<360.f;
        // A sprinting withdrawal can make the current separation look safe.
        // Do not credit that speed when predicting the slower swap/draw phase.
        const float Approach=FMath::Max(0.f,float(-FVector::DotProduct(Target->GetVelocity(),Relative.GetSafeNormal2D())));
        Safe=Distance>850.f && Distance-Approach*(.48f+B.Stats.Draw)>650.f &&
            HasFiringLane(AimOrigin(),*Target,Target->GetActorLocation());
    }
    if (!bBowBlades || !Safe) B.SafeSince=-1;
    else if (B.SafeSince<0) B.SafeSince=Now;
    const bool ReturnToBow=bBowBlades && Safe && B.SafeSince>=0 && Now-B.SafeSince>=.65 && Now>=B.SwitchAfter && !Busy();
    // The dwell time protects the offensive return, never an emergency defence.
    if ((!bBowBlades && Threat && (!Busy() || Motion.Action==EUnknownAction::DrawBow)) ||
        ReturnToBow)
    {
        const bool KeepRoute=ReturnToBow && (Position==EUnknownPosition::Adjust || Position==EUnknownPosition::SeekCover ||
            Position==EUnknownPosition::MoveToPeek);
        const float PreviousHealth=Health,PreviousStamina=Stamina;
        bBowBlades=!bBowBlades;
        Sheet=bBowBlades?BladeSheet:BowSheet;
        CacheStats();
        Health=FMath::Min(PreviousHealth,MaxHealth); Stamina=FMath::Min(PreviousStamina,MaxStamina);
        if (!KeepRoute) { bHasCover=false; Position=EUnknownPosition::Open; BypassUntil=0; NextReposition=0; }
        bRetreating=false;
        B.SwitchAfter=Now+1.5; B.RetreatAfter=Now;
        B.SafeSince=-1; B.bRetreatFailed=false;
        SetAction(EUnknownAction::SwapWeapon,.48f); OnRep_BowMode(); ForceNetUpdate();
    }
}

bool AUnknownHumanoid::PursueBowRetreat(AMonsterAIController& AI,APawn* Target)
{
    if (!bBowBlades || !Archery || Controlled()) return false;
    if (Busy() && !CanPursueDuringSwing(Target) && Motion.Action!=EUnknownAction::SwapWeapon) return false;
    const double Now=ServerTime(); auto& B=*Archery;
    if (!Target && Now-LastSeenTime>4.)
    {
        if (Position!=EUnknownPosition::Open) LeaveCover(false);
        return false;
    }
    const FVector Feet=GetNavAgentLocation();
    if (Target && Position!=EUnknownPosition::Open &&
        (FVector::DistSquared2D(PlannedTarget,Target->GetNavAgentLocation())>FMath::Square(480.f) ||
        FVector::Dist2D(FiringPoint,Target->GetNavAgentLocation())<FVector::Dist2D(Feet,Target->GetNavAgentLocation())-80.f))
    {
        LeaveCover(false); B.RetreatAfter=Now; B.bRetreatFailed=false;
    }
    if (Position!=EUnknownPosition::Open && AtFootPoint(Feet,FiringPoint,42.f))
    {
        // Continue a short withdrawal from its reached point on this same
        // task, without a forced stop or an intervening melee chase request.
        LeaveCover(false); B.RetreatAfter=Now; B.bRetreatFailed=false;
    }
    if (Position==EUnknownPosition::Open && B.SafeSince>=0)
    {
        // Wait out the short safe-distance dwell here, without chasing back
        // into the very range that caused the defensive weapon swap.
        AI.StopMovement(); bSprintIntent=false; return true;
    }
    // Fight while withdrawing along an actually reachable firing route. If a
    // corner offers no route, hold the blades and fight instead of running into it.
    if (Target && Now>=B.RetreatAfter && Position==EUnknownPosition::Open)
    {
        if (CanPlanThisFrame())
        {
            const float MeleeRange=AttackRange,MeleePreferred=PreferredRange;
            AttackRange=FMath::Min(3400.f,float(B.Stats.Range*100.)); PreferredRange=AttackRange*.7f;
            B.bRetreatFailed=!FindFiringPosition(Target,Target->GetNavAgentLocation(),true);
            AttackRange=MeleeRange; PreferredRange=MeleePreferred;
            B.RetreatAfter=Now+1.2;
        }
        else B.RetreatAfter=Now+FMath::FRandRange(.08f,.18f);
    }
    if (Position==EUnknownPosition::Open)
    {
        // A deferred path query is not a failed escape. Counterattack only
        // after an actual search fails; do not alternate chase/retreat per frame.
        if (Target && (!B.bRetreatFailed || Motion.Action==EUnknownAction::SwapWeapon))
        { AI.StopMovement(); bSprintIntent=false; return true; }
        return false;
    }
    if (Position==EUnknownPosition::SeekCover && AtFootPoint(Feet,CoverPoint,48.f))
        Position=EUnknownPosition::MoveToPeek;
    bSprintIntent=!Busy();
    MoveRanged(AI,Position==EUnknownPosition::SeekCover?CoverPoint:FiringPoint,35.f,true);
    return true;
}

bool AUnknownHumanoid::PursueLastSighting(AMonsterAIController& AI,FVector LastKnown)
{
    if ((Loadout.Role!=EUnknownRole::Bow && Loadout.Role!=EUnknownRole::Magic) ||
        !TacticalTarget.IsValid() || Controlled() || Position!=EUnknownPosition::Open) return false;
    const double Now=ServerTime();
    const FVector Feet=GetNavAgentLocation();
    if (Now-LastSeenTime<1.2 || (SearchSteps==0 && !AtFootPoint(Feet,LastKnown,120.f))) return false;
    bSprintIntent=false;
    if (bSearchingPoint && (AtFootPoint(Feet,SearchPoint,35.f) ||
        ShouldAvoidTravelPoint(SearchPoint) || AI.ShouldAvoidNavigationGoal(SearchPoint)))
    {
        FailedBypass=SearchPoint; AvoidBypassUntil=Now+3.;
        bSearchingPoint=false; NextSearchStep=Now+.35;
    }
    if (!bSearchingPoint)
    {
        // Reaching the last sighting is not proof that the opponent vanished.
        // Inspect up to three nearby clear steps using only the last observed
        // heading, then leave target expiry/return to the existing behaviour tree.
        if (SearchSteps>=3 || Now<NextSearchStep)
        { AI.StopMovement(); return true; }
        if (!CanPlanThisFrame())
        { NextSearchStep=Now+FMath::FRandRange(.1f,.2f); AI.StopMovement(); return true; }
        ++SearchSteps;
        if (!FindBypass(AI,LastKnown+LastSeenDirection*450.f,LastSeenDirection) ||
            FVector::DistSquared2D(BypassPoint,LastKnown)>FMath::Square(600.f))
        { NextSearchStep=Now+.65; AI.StopMovement(); return true; }
        SearchPoint=BypassPoint; bSearchingPoint=true;
    }
    MoveRanged(AI,SearchPoint,25.f,false);
    return true;
}

// If a movable prop or another pawn blocks a valid nav corridor, take a short clear
// step to one side before resuming the same goal. Never steer through geometry.
bool AUnknownHumanoid::FindBypass(AMonsterAIController& AI,FVector Goal,FVector Forward)
{
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Feet=GetNavAgentLocation();
    const auto& Agent=AI.GetNavAgentPropertiesRef();
    const auto* Data=Nav?Nav->GetNavDataForProps(Agent,Feet):nullptr;
    if (!Data) return false;
    const auto* Capsule=GetCapsuleComponent();
    const float Radius=Capsule->GetScaledCapsuleRadius();
    // Sweep above step height so a walkable tread does not rule out a lateral step.
    const float Step=GetCharacterMovement()->MaxStepHeight;
    const auto Shape=FCollisionShape::MakeCapsule(Radius,FMath::Max(Radius,Capsule->GetScaledCapsuleHalfHeight()-Step*.5f));
    const FVector Lift(0,0,Step+Shape.GetCapsuleHalfHeight()+3.f);
    const FCollisionQueryParams Collision(SCENE_QUERY_STAT(UnknownBypass),false,this);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const float Side=(GetUniqueID()&1)?1.f:-1.f;
    const bool Withdrawing=(bRetreating || bBowBlades) && TacticalTarget.IsValid() && ServerTime()-LastSeenTime<1.2;
    const FVector Threat=Withdrawing && bTacticalTargetVisible?TacticalTarget->GetNavAgentLocation():PlannedTarget;
    const float ThreatClearance=FMath::Min(float(FVector::Dist2D(Feet,Threat))*.8f,350.f);
    TArray<AUnknownHumanoid*> Allies;
    GatherCrowd(Feet,750.f,Allies);
    float Best=MAX_flt;
    for (const float Angle:{65.f,-65.f,110.f,-110.f,150.f,-150.f})
    {
        const FVector Desired=Feet+Forward.RotateAngleAxis(Angle*Side,FVector::UpVector)*FMath::Max(165.f,Radius*5.f);
        FNavLocation Point;
        if (!Nav->ProjectPointToNavigation(Desired,Point,FVector(45,45,55),Data) ||
            FVector::Dist2D(Feet,Point.Location)<100.f || !FitsAt(*this,Point.Location) ||
            FVector::Dist2D(Home,Point.Location)>Combat->LeashRange()-40.f) continue;
        FVector Edge;
        if (Data->Raycast(Feet,Point.Location,Edge,Data->GetDefaultQueryFilter(),&AI) ||
            GetWorld()->SweepTestByChannel(Feet+Lift,Point.Location+Lift,FQuat::Identity,Capsule->GetCollisionObjectType(),Shape,Collision,Response))continue;
        // Local obstacle recovery must obey the same enemy clearance as the
        // retreat corridor, rather than sidestepping through the pursuer.
        if (Withdrawing && FMath::PointDistToSegment(Threat,Feet,Point.Location)<ThreatClearance)continue;
        // Repeating a blocked side-step immediately would ping-pong at a narrow doorway.
        if ((ServerTime()<AvoidBypassUntil && AtFootPoint(Point.Location,FailedBypass,110.f)) ||
            ShouldAvoidTravelPoint(Point.Location))continue;
        const float Space=CrowdSpaceCost(Point.Location,Allies);
        if(Space==MAX_flt)continue;
        const float Score=FVector::Dist(Point.Location,Goal)+Space;
        if (Score<Best){Best=Score;BypassPoint=Point.Location;}
    }
    return Best<MAX_flt;
}

void AUnknownHumanoid::MoveRanged(AMonsterAIController& AI,FVector Goal,float Acceptance,bool bTactical)
{
    if (HandleCrowdTraffic(AI,Goal,true)) return;
    const double Now=ServerTime();
    const FVector Feet=GetNavAgentLocation();
    const bool NewLeg=(bLastTravelWasTactical!=bTactical) || (bTactical && !Goal.Equals(TravelGoal,32.f));
    if (!NewLeg && Now<RetryTravelAt && Goal.Equals(TravelGoal,140.f)) { LastTravelCall=Now; return; }
    const bool Restart=Now-LastTravelCall>.65;
    const bool GoalMoved=!Goal.Equals(TravelGoal,140.f);
    if (Restart)
    {
        // Shooting, casting and intentional holds are not blocked movement.
        LastTravelSample=Now; TravelSample=Feet; BypassUntil=RetryTravelAt=0.; BypassAttempts=0;
        RemainingTravel=MAX_flt;
    }
    else if (NewLeg || GoalMoved)
    {
        // Replacing a tactical goal does not prove that this pawn moved.
        // Keep the blocked timer/bypass limit across immediate replans.
        RemainingTravel=MAX_flt;
        BypassUntil=RetryTravelAt=0.;
    }
    if(Restart || NewLeg || GoalMoved)TravelGoal=Goal;
    bLastTravelWasTactical=bTactical; LastTravelCall=Now;
    if (BypassUntil>0.)
    {
        if (AtFootPoint(Feet,BypassPoint,32.f))
        {
            FailedBypass=BypassPoint; AvoidBypassUntil=Now+3.;
            BypassUntil=0.; TravelSample=Feet; LastTravelSample=Now; RemainingTravel=MAX_flt;
        }
        else if (Now<BypassUntil && !AI.ShouldAvoidNavigationGoal(BypassPoint,45.f))
        {
            AI.NavigateTo(BypassPoint,20.f,.2f);
            return;
        }
        else
        {
            FailedBypass=BypassPoint; AvoidBypassUntil=Now+3.;
            RememberBlockedTravel(BypassPoint);
            BypassUntil=0.; LastTravelSample=Now-2.;
        }
    }
    // Measure progress along the corridor. Going away from the enemy around a wall
    // is progress, but shuffling back and forth against the same corner is not.
    if (Now>=NextRouteSample && AI.GetMoveStatus()==EPathFollowingStatus::Moving)
    {
        NextRouteSample=Now+.22;
        const auto* Follow=AI.GetPathFollowingComponent();
        const auto Path=Follow->GetPath();
        if (Path.IsValid() && Path->GetPathPoints().IsValidIndex(Follow->GetNextPathIndex()))
        {
            const float Left=Path->GetLengthFromPosition(Feet,Follow->GetNextPathIndex());
            if (RemainingTravel==MAX_flt)
            {
                if (FVector::DistSquared(Feet,TravelSample)>FMath::Square(28.f))
                {TravelSample=Feet; LastTravelSample=Now;}
                RemainingTravel=Left;
            }
            if (Left<RemainingTravel-24.f && FVector::DistSquared(Feet,TravelSample)>FMath::Square(18.f))
            {
                if(FVector::DistSquared(Feet,FailedBypass)>FMath::Square(220.f))BypassAttempts=0;
                RemainingTravel=Left; TravelSample=Feet; LastTravelSample=Now;
            }
        }
    }
    const bool Failed=AI.ShouldAvoidNavigationGoal(Goal);
    if (Failed && bTactical)
    {
        AI.StopMovement();
        RememberBlockedTravel(Goal);
        LeaveCover(true);
        return;
    }
    if (!AtFootPoint(Feet,Goal,Acceptance) && (Failed || Now-LastTravelSample>1.3))
    {
        const FVector Forward=AI.GetMoveStatus()==EPathFollowingStatus::Moving?
            (AI.GetImmediateMoveDestination()-Feet).GetSafeNormal2D():(Goal-Feet).GetSafeNormal2D();
        AI.StopMovement();
        LastTravelSample=Now; TravelSample=Feet;
        if (BypassAttempts<2 && !Forward.IsNearlyZero() && FindBypass(AI,Goal,Forward))
        {
            ++BypassAttempts;
            BypassUntil=Now+2.;
            AI.NavigateTo(BypassPoint,20.f,.2f);
            return;
        }
        RememberBlockedTravel(Goal);
        if (bTactical) { LeaveCover(true); return; }
        BlockedApproachUntil=Now+4.; NextReposition=Now;
        RetryTravelAt=Now+1.;
        BypassAttempts=0; RemainingTravel=MAX_flt;
        return;
    }
    AI.NavigateTo(Goal,Acceptance,bTactical?.25f:.55f);
}

bool AUnknownHumanoid::WantsReload() const
{
    if(Loadout.Role!=EUnknownRole::Gun || Capacity<=0 || Magazine>=Capacity)return false;
    return Magazine==0 || (Position==EUnknownPosition::Sheltered && Magazine<=FMath::Max(BurstSize,Capacity/2));
}

bool AUnknownHumanoid::UnderPressure() const
{
    return Health<MaxHealth*.4f || ServerTime()-LastIncomingHit<1.6f ||
        (Loadout.Role==EUnknownRole::Gun && Magazine<=FMath::Max(BurstSize,Capacity/4));
}

APawn* AUnknownHumanoid::ConsiderVisibleOpponent(AMonsterAIController& AI,APawn* Current,bool bVisible,bool bMaySwitch)
{
    const double Now=ServerTime();
    if(Current==TacticalTarget.Get() && Now<NextSightSample)return Current;
    NextSightSample=Now+.4f;
    OtherOpponents.Reset();
    if(!Current || GetWorld()->GetNumPlayerControllers()<2)return Current;
    const FVector Feet=GetNavAgentLocation();
    const float CurrentDistance=bVisible?FVector::Dist2D(Feet,Current->GetNavAgentLocation()):0.f;
    APawn* Best=Current;
    float BestDistance=MAX_flt;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        const auto* PC=It->Get();
        auto* Other=PC?PC->GetPawn().Get():nullptr;
        if(!Other || Other==Current || !AI.CanSeePlayer(Other,true))continue;
        const float Distance=FVector::Dist2D(Feet,Other->GetNavAgentLocation());
        OtherOpponents.Add({Other,Other->GetNavAgentLocation(),Other->GetPawnViewLocation()});
        // A close challenger can displace a visible focus. Brief occlusion during a peek
        // is normal, so keep the existing opponent until the sight loss persists.
        const bool Better=bVisible?Distance<FMath::Min(CurrentDistance*.6f,IsRanged()?650.f:AttackRange):
            (Now-LastSeenTime>.85f && Distance<AttackRange);
        if(Better && Distance<BestDistance){BestDistance=Distance; Best=Other;}
    }
    if(!bMaySwitch || Now<NextTargetSwitch || Best==Current)return Current;
    NextTargetSwitch=Now+2.f;
    OtherOpponents.RemoveAll([Best](const FSighting& S){return S.Pawn.Get()==Best;});
    if(bVisible)OtherOpponents.Add({Current,Current->GetNavAgentLocation(),Current->GetPawnViewLocation()});
    return Best;
}

bool AUnknownHumanoid::HasVisibleCluster(const APawn* Focus,float Radius) const
{
    if(!Focus || ServerTime()>NextSightSample || Radius<=0)return false;
    for(const auto& S:OtherOpponents)
        if(S.Pawn.IsValid() && S.Pawn.Get()!=Focus && FVector::DistSquared(Focus->GetNavAgentLocation(),S.Feet)<=FMath::Square(Radius))
            return true;
    return false;
}

void AUnknownHumanoid::LeaveCover(bool bAvoid)
{
    if(bAvoid){FailedCover=bHasCover?CoverPoint:FiringPoint; AvoidCoverUntil=ServerTime()+4.f;}
    Position=EUnknownPosition::Open;
    bHasCover=false;
    bCrowdReposition=false;
    // The next task tick may continue straight into another route. Only an
    // actual movement pause resets its progress clock in MoveRanged.
    BypassUntil=0.;
    NextReposition=ServerTime()+(bAvoid?.15f:.5f);
}

void AUnknownHumanoid::RememberBlockedTravel(FVector Point)
{
    const double Now=ServerTime();
    BlockedTravelSites.RemoveAll([&](const FBlockedTravelSite& Site)
        { return Site.Until<=Now || AtFootPoint(Point,Site.Point,140.f); });
    if (BlockedTravelSites.Num()>=4) BlockedTravelSites.RemoveAt(0);
    BlockedTravelSites.Add({Point,Now+6.});
}

bool AUnknownHumanoid::ShouldAvoidTravelPoint(FVector Point) const
{
    const double Now=ServerTime();
    return BlockedTravelSites.ContainsByPredicate([&](const FBlockedTravelSite& Site)
        { return Site.Until>Now && AtFootPoint(Point,Site.Point,140.f); });
}

bool AUnknownHumanoid::CanActOutOfSight() const
{
    if (UsesMobileGunCombat() && WantsReload()) return true;
    return Loadout.Role==EUnknownRole::Magic && SelfCast();
}

// A hiding place is useful only when the same pawn can also reach a nearby firing lane.
bool AUnknownHumanoid::FindFiringPosition(APawn* Target,FVector LastKnown,bool bVisible)
{
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Feet=GetNavAgentLocation();
    const auto& Props=GetNavAgentPropertiesRef();
    const auto* Data=Nav?Nav->GetNavDataForProps(Props,Feet):nullptr;
    if (!Data) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(UnknownCover),false,this);
    Query.AddIgnoredActor(Target);
    const FVector Eye=bVisible?Target->GetPawnViewLocation():LastKnown+FVector(0,0,145);
    const FVector TargetBody=bVisible?Target->GetActorLocation():LastKnown+FVector(0,0,Target->GetSimpleCollisionHalfHeight());
    const FVector MuzzleOffset=AimOrigin()-Feet;
    const bool Pressure=UnderPressure();
    const double Now=ServerTime();
    const float CurrentDistance=FVector::Dist(Feet,LastKnown);
    const bool Withdraw=(bRetreating || bBowBlades) && (bVisible || Now-LastSeenTime<1.2);
    auto Covered=[&](FVector Point,float Height)
    {
        FHitResult Hit;
        const FVector From=Point+FVector(0,0,Height);
        return MagicOcclusion::TraceBlocker(GetWorld(),From,Eye,Query,Hit,this) &&
            !Cast<APawn>(Hit.GetActor()) && FVector::DistSquared(From,Hit.ImpactPoint)<=FMath::Square(310.f);
    };
    auto Project=[&](FVector Candidate,FVector& Result)
    {
        FNavLocation OnNav;
        if (!Nav->ProjectPointToNavigation(Candidate,OnNav,FVector(60,60,85),Data) ||
            FMath::Abs(OnNav.Location.Z-Candidate.Z)>80.f ||
            FVector::Dist2D(OnNav.Location,Home)>Combat->LeashRange()-60.f) return false;
        Result=OnNav.Location;
        return true;
    };
    const auto* AI=Cast<AMonsterAIController>(GetController());
    const UObject* Querier=AI?static_cast<const UObject*>(AI):this;
    auto TravelLength=[&](FVector From,FVector To,float& Length)
    {
        Length=FVector::Distance(From,To);
        if(Length<12.f)return true;
        FPathFindingQuery Path(Querier,*Data,From,To,Data->GetDefaultQueryFilter());
        Path.SetAllowPartialPaths(false);
        const auto Route=Nav->FindPathSync(Props,Path);
        if(!Route.IsSuccessful() || !Route.Path.IsValid() || Route.Path->IsPartial() ||
            Route.Path->GetPathPoints().IsEmpty() || !AtFootPoint(Route.Path->GetEndLocation(),To,35.f))return false;
        if (Withdraw)
        {
            // A farther destination is not a retreat if reaching it takes the
            // pawn straight through the opponent. Evaluate the actual corridor.
            const float Exclusion=FMath::Min(CurrentDistance*.8f,350.f);
            FVector Previous=From;
            for (const auto& Point:Route.Path->GetPathPoints())
            {
                if (FMath::PointDistToSegment(LastKnown,Previous,Point.Location)<Exclusion) return false;
                Previous=Point.Location;
            }
        }
        Length=FMath::Max(Length,float(Route.Path->GetLength()));
        return true;
    };
    const FVector Away=(Feet-LastKnown).GetSafeNormal2D(SMALL_NUMBER,GetActorForwardVector());
    TArray<AUnknownHumanoid*> Allies;
    GatherCrowd(Feet,FMath::Clamp(PreferredRange+800.f,1200.f,4200.f),Allies);
    struct FSite { FVector Hide,Peek; float Score; bool Cover; };
    TArray<FSite,TInlineAllocator<40>> Sites;
    auto Add=[&](FVector Hide,FVector Peek,bool Cover)
    {
        const float Range=FVector::Dist(Peek,LastKnown);
        // A short safe step is useful when a cramped room cannot offer the
        // complete bow-return distance in a single path. Continue from there.
        const float MinimumRange=bBowBlades?FMath::Min(920.f,CurrentDistance+140.f):Loadout.Role==EUnknownRole::Bow?650.f:
            FMath::Min(Loadout.Role==EUnknownRole::Magic?450.f:160.f,PreferredRange*.4f);
        if (Range>AttackRange*.96f || Range<MinimumRange) return;
        if (Withdraw)
        {
            const float Gain=FMath::Min(160.f,PreferredRange*.18f)*(Cover?.35f:1.f);
            if (Range<CurrentDistance+Gain || (Cover && FVector::Dist(Hide,LastKnown)<CurrentDistance)) return;
        }
        const FVector Stand=Cover?Hide:Peek;
        if (Now<AvoidCoverUntil && AtFootPoint(Stand,FailedCover,165.f))return;
        if (ShouldAvoidTravelPoint(Stand) || (Cover && ShouldAvoidTravelPoint(Peek)))return;
        if (AI && (AI->ShouldAvoidNavigationGoal(Stand) || (Cover && AI->ShouldAvoidNavigationGoal(Peek))))return;
        if (!Cover && AtFootPoint(Feet,Peek,40.f))return;
        if (Cover && (FVector::DistSquared2D(Hide,Peek)<FMath::Square(75.f) || FMath::Abs(Hide.Z-Peek.Z)>65.f))return;
        if(Sites.ContainsByPredicate([&](const FSite& S){return S.Cover==Cover && AtFootPoint(S.Hide,Hide,48.f) && AtFootPoint(S.Peek,Peek,48.f);}))return;
        const float Space=FMath::Max(CrowdSpaceCost(Stand,Allies),Cover?CrowdSpaceCost(Peek,Allies):0.f);
        if(Space==MAX_flt)return;
        float Score=FMath::Abs(Range-PreferredRange)+.48f*FVector::Dist2D(Feet,Cover?Hide:Peek)+Space;
        if(Cover)
        {
            Score-=Pressure?810.f:(bVisible?365.f:250.f);
        }
        if(Now<=NextSightSample)
            for(const auto& S:OtherOpponents)
            {
                auto* Opponent=S.Pawn.Get();
                if(!Opponent || Opponent==Target)continue;
                FCollisionQueryParams SideSight=Query;
                SideSight.AddIgnoredActor(Opponent);
                FHitResult Hit;
                const FVector At=(Cover?Hide:Peek)+FVector(0,0,143);
                if(!MagicOcclusion::TraceBlocker(GetWorld(),S.Eye,At,SideSight,Hit,this))
                    Score+=Pressure?920.f:580.f;
            }
        Sites.Add({Hide,Peek,Score,Cover});
    };
    auto EvaluateSite=[&](FVector Seed)
    {
        FVector Site;
        if(!Project(Seed,Site))return;
        if(HasFiringLane(Site+MuzzleOffset,*Target,TargetBody)){ Add(Site,Site,false); return; }
        if(!Covered(Site,143.f) || !Covered(Site,82.f))return;
        const FVector Side=FVector::CrossProduct((Eye-Site).GetSafeNormal2D(),FVector::UpVector);
        for(float Offset:{-125.f,125.f,-265.f,265.f})
        {
            FVector Peek;
            if(Project(Site+Side*Offset,Peek)&&HasFiringLane(Peek+MuzzleOffset,*Target,TargetBody))Add(Site,Peek,true);
        }
    };
    // Sample the sheltered side of nearby geometry as well as points in open space.
    const float Jitter=FMath::FRandRange(-12.f,12.f);
    for(int32 Sector=0;Sector<8;++Sector)
    {
        const FVector Ray=Away.RotateAngleAxis(Jitter+Sector*45.f,FVector::UpVector);
        FHitResult Wall;
        const FVector Start=Feet+FVector(0,0,125);
        if(MagicOcclusion::TraceBlocker(GetWorld(),Start,Start+Ray*560.f,Query,Wall,this) &&
            !Cast<APawn>(Wall.GetActor()) && FMath::Abs(Wall.ImpactNormal.Z)<.65f)
        {
            const FVector Foot(Wall.ImpactPoint.X,Wall.ImpactPoint.Y,Feet.Z);
            EvaluateSite(Foot+Wall.ImpactNormal.GetSafeNormal2D()*83.f);
        }
    }
    for (int32 Ring=0;Ring<3;++Ring)
        for (int32 Sector=0;Sector<8;++Sector)
        {
            const FVector Radial=Away.RotateAngleAxis(Jitter+Sector*45.f,FVector::UpVector);
            const FVector Seed=Ring==2?LastKnown+Radial*PreferredRange:Feet+Radial*(Ring==0?210.f:500.f);
            EvaluateSite(Seed);
        }
    Sites.Sort([](const FSite& A,const FSite& B){return A.Score<B.Score;});
    const float CurrentSpace=CrowdSpaceCost(Feet,Allies);
    const bool GoodCurrentLane=CurrentSpace<200.f && !Withdraw && bVisible && bHasFiringLane &&
        CurrentDistance>=PreferredRange*.70f && CurrentDistance<=AttackRange*.91f;
    // A comfortable open position is a real option. A long detour to distant cover
    // must improve on staying here, especially when nobody is pressuring the shooter.
    float BestScore=GoodCurrentLane?FMath::Abs(CurrentDistance-PreferredRange)+CurrentSpace:MAX_flt;
    const FSite* Best=nullptr;
    int32 Probes=0;
    for (const FSite& Site:Sites)
    {
        if(Probes>=8 || Site.Score>=BestScore)break;
        if(!Site.Cover && GoodCurrentLane)continue;
        if(Site.Cover && !bVisible && Now-LastSeenTime>2.8)continue;
        const FVector Stand=Site.Cover?Site.Hide:Site.Peek;
        if(!FitsAt(*this,Stand) || (Site.Cover && !FitsAt(*this,Site.Peek)))continue;
        float Approach,PeekTravel=0.f;
        ++Probes;
        if(!TravelLength(Feet,Stand,Approach))continue;
        // A nearby retreat spot behind a long wall is not an escape if the
        // full route loops through several rooms before gaining separation.
        if(Withdraw && Approach>FMath::Max(700.f,float(FVector::Dist2D(Feet,Stand))*2.4f+120.f))continue;
        if(Site.Cover)
        {
            if(Probes>=8)continue;
            ++Probes;
            if(!TravelLength(Site.Hide,Site.Peek,PeekTravel) || PeekTravel>FVector::Dist(Site.Hide,Site.Peek)*1.6f+45.f)continue;
        }
        const float Score=Site.Score+.48f*FMath::Max(0.f,Approach-float(FVector::Dist2D(Feet,Stand)))+.32f*PeekTravel;
        if(Score<BestScore){BestScore=Score;Best=&Site;}
    }
    if(!Best)return false;
    bHasCover=Best->Cover;
    bCrowdReposition=CurrentSpace>=200.f;
    CoverPoint=Best->Hide; FiringPoint=Best->Peek; PlannedTarget=LastKnown;
    Position=bHasCover?EUnknownPosition::SeekCover:EUnknownPosition::Adjust;
    return true;
}

void AUnknownHumanoid::UpdateTactics(APawn* Target,bool bVisible,FVector LastKnown)
{
    // A dead/unpossessed/streamed-out opponent cannot keep a pending swing or
    // burst busy while AI waits to acquire the replacement pawn.
    if (!UnknownSpell::IsTarget(this,AttackTarget.Get()))
    {
        if (Motion.Action==EUnknownAction::Swing || Motion.Action==EUnknownAction::Fire)
        {
            ShotsLeft=0;
            NextAttack=FMath::Max(NextAttack,double(ServerTime())+.3);
            SetAction(EUnknownAction::Ready);
        }
        CancelRangedAction();
        AttackTarget.Reset();
    }
    const double Now=ServerTime();
    const bool BowOrMagic=Loadout.Role==EUnknownRole::Bow || Loadout.Role==EUnknownRole::Magic;
    const bool Reacquired=Target && Target==TacticalTarget.Get() && bVisible && !bTacticalTargetVisible;
    bTacticalTargetVisible=Target && bVisible;
    if (Archery && TacticalTarget.Get()!=Target)
    { Archery->SafeSince=-1; Archery->bRetreatFailed=false; Archery->RetreatAfter=0; }
    if ((Motion.Action==EUnknownAction::Cast || Motion.Action==EUnknownAction::DrawBow) &&
        (!Target || Target!=AttackTarget.Get())) CancelRangedAction();
    if (!Target || TacticalTarget.Get()!=Target || (!IsRanged() && !bBowBlades && Position!=EUnknownPosition::Open))
    {
        bHasCover=false; bCrowdReposition=false; Position=EUnknownPosition::Open;
        TacticalTarget=Target; NextReposition=0;
        LastSeenTime=-100; AvoidCoverUntil=0;
        FiringLaneLostSince=-1;
        SearchSteps=0; bSearchingPoint=false; NextSearchStep=0;
        CrowdYieldUntil=CrowdWaitUntil=CrowdMoveUntil=CrowdSpeedUntil=0.; CrowdBlockedSince=-1;
        CrowdPasser.Reset(); CrowdBlocker.Reset(); CrowdPausedRequest=FAIRequestID::InvalidRequest;
        BypassUntil=AvoidBypassUntil=RetryTravelAt=BlockedApproachUntil=0.; LastTravelCall=-100.; bHasFiringLane=false; bRetreating=false;
        if(!Target)
        {
            UpdateCombatFocus(nullptr, false, LastKnown);
            OtherOpponents.Reset(); NextTargetSwitch=0;
            if (bBowBlades) UpdateBowTactics(nullptr,false);
            return;
        }
    }
    if (Reacquired)
    {
        // Fresh sight resumes decisions now, without throwing away a usable
        // corridor or forgetting which physical routes just failed.
        RetryTravelAt=BlockedApproachUntil=0.;
        NextReposition=Now;
        if (Archery) Archery->RetreatAfter=Now;
    }
    if(bVisible)
    {
        LastSeenTime=Now;
        LastSeenDirection=Target->GetVelocity().SizeSquared2D()>FMath::Square(30.f)?
            Target->GetVelocity().GetSafeNormal2D():(LastKnown-GetNavAgentLocation()).GetSafeNormal2D(SMALL_NUMBER,GetActorForwardVector());
        SearchSteps=0; bSearchingPoint=false; NextSearchStep=0;
    }
    UpdateCombatFocus(Target, bVisible, LastKnown);
    UpdateBowTactics(Target,bVisible);
    if(!IsRanged())return;
    bHasFiringLane=bVisible && HasFiringLane(AimOrigin(),*Target,Target->GetActorLocation());
    if (bHasFiringLane) FiringLaneLostSince=-1;
    else if (FiringLaneLostSince<0) FiringLaneLostSince=Now;
    const double LaneLostFor=FiringLaneLostSince>=0?Now-FiringLaneLostSince:0.;
    if (Motion.Action==EUnknownAction::Cast || Motion.Action==EUnknownAction::DrawBow)
    {
        const FVector Axis=(LastKnown-GetNavAgentLocation()).GetSafeNormal2D();
        const float Closing=bVisible?-FVector::DotProduct(Target->GetVelocity()-GetVelocity(),Axis):0.f;
        const bool Rushed=Motion.Action==EUnknownAction::Cast && Motion.Skill==TEXT("thunderLance") && bPendingContact &&
            bVisible && FVector::Dist2D(GetNavAgentLocation(),LastKnown)-FMath::Max(0.f,Closing)*.45f<420.f;
        if (Rushed || (!SelfCast() && LaneLostFor>.6)) CancelRangedAction();
    }
    if (Controlled() || (Busy() && !CanPursueDuringAction(Target,bVisible))) return;
    const FVector Feet=GetNavAgentLocation();
    const float CurrentRange=FVector::Dist(Feet,LastKnown);
    // Keep the chosen offensive spell's range while travelling to that firing position.
    // A change in visibility still allows defensive spells and recovery.
    const bool InTransit=Position==EUnknownPosition::Adjust || Position==EUnknownPosition::SeekCover || Position==EUnknownPosition::MoveToPeek;
    if (Loadout.Role==EUnknownRole::Magic && !Busy() &&
        (bVisible || Now-LastSeenTime>.6 || !HasChosenMagic()) &&
        (!InTransit || !HasChosenMagic() || !bVisible || SelfCast() || bRetreating || CurrentRange<550.f || ChosenMagicId()==TEXT("thunderLance")))
        SelectMagic(CurrentRange,bVisible);
    if (!bVisible && SearchSteps>0 && Position==EUnknownPosition::Open) return;
    const FVector ToTarget=(LastKnown-Feet).GetSafeNormal2D();
    const float Closing=bVisible?-FVector::DotProduct(Target->GetVelocity()-GetVelocity(),ToTarget):0.f;
    // React promptly to a visible rush, then retain the withdrawal until a
    // comfortable band is restored. Do not oscillate at one distance threshold.
    const bool NeedDistance=bVisible?(bRetreating?CurrentRange<PreferredRange*.82f:
        CurrentRange-FMath::Max(0.f,Closing)*.35f<PreferredRange*.60f):
        BowOrMagic && bRetreating && Now-LastSeenTime<1.2;
    if (NeedDistance && !bRetreating) NextReposition=Now;
    bRetreating=NeedDistance;
    if (Now<CrowdYieldUntil) return;
    // Cover deliberately breaks sight. Give the current leg time to round its obstacle,
    // but do not keep cycling an old position after the opponent is lost.
    const bool LostSight=!bVisible && Now-LastSeenTime>(InTransit?5.5:2.8);
    const bool RoundingObstacle=InTransit && Now-LastTravelCall<.5 && Now-LastTravelSample<1.3 && GetVelocity().SizeSquared2D()>FMath::Square(25.f);
    if(LostSight && !WantsReload() && !SelfCast() && !RoundingObstacle)
    {
        if(Position!=EUnknownPosition::Open)LeaveCover(false);
        if(Now>=BlockedApproachUntil)return;
    }
    const float PlannedRange=FVector::Dist(FiringPoint,LastKnown);
    const bool BadRange=PlannedRange>AttackRange || (bHasCover && PlannedRange<PreferredRange*.45f) ||
        (bRetreating && Position!=EUnknownPosition::Sheltered && PlannedRange<CurrentRange-80.f);
    if (Position!=EUnknownPosition::Open && (BadRange || FVector::Dist(PlannedTarget,LastKnown)>FMath::Clamp(PreferredRange*.35f,240.f,680.f)))
    {LeaveCover(false); NextReposition=Now;}
    if(Position==EUnknownPosition::Sheltered && !OtherOpponents.IsEmpty() && Now<=NextSightSample)
    {
        for(const auto& S:OtherOpponents)
        {
            auto* Other=S.Pawn.Get();
            if(!Other)continue;
            FHitResult Block;
            FCollisionQueryParams Side(SCENE_QUERY_STAT(UnknownShelterFlank),false,this);
            Side.AddIgnoredActor(Other);
            if(!MagicOcclusion::TraceBlocker(GetWorld(),S.Eye,AimOrigin(),Side,Block,this))
            {LeaveCover(true);return;}
        }
    }
    if (Position==EUnknownPosition::SeekCover && AtFootPoint(Feet,CoverPoint,32.f))
    {
        FCollisionQueryParams Wall(SCENE_QUERY_STAT(UnknownShelter),false,this);
        Wall.AddIgnoredActor(Target);
        FHitResult Block;
        if (!MagicOcclusion::TraceBlocker(GetWorld(),LastKnown+FVector(0,0,145),AimOrigin(),Wall,Block,this))
        {
            LeaveCover(true);
            return;
        }
        Position=EUnknownPosition::Sheltered;
        PositionUntil=Now+(UnderPressure()?FMath::FRandRange(1.1f,1.7f):FMath::FRandRange(.4f,.85f));
    }
    if(Position==EUnknownPosition::Sheltered)
    {
        if (BowOrMagic && bVisible && bRetreating)
        { LeaveCover(false); NextReposition=Now; return; }
        FHitResult Block;
        FCollisionQueryParams Sight(SCENE_QUERY_STAT(UnknownShelterOpened),false,this);
        Sight.AddIgnoredActor(Target);
        if(bVisible && !MagicOcclusion::TraceBlocker(GetWorld(),Target->GetPawnViewLocation(),AimOrigin(),Sight,Block,this))
        {LeaveCover(true);return;}
        if(WantsReload())return;
    }
    if (Position==EUnknownPosition::Sheltered && Now>=PositionUntil)
    { Position=EUnknownPosition::MoveToPeek; }
    if (Position==EUnknownPosition::MoveToPeek && AtFootPoint(Feet,FiringPoint,32.f))
    {
        if(!bHasFiringLane)
        { if(!BowOrMagic || LaneLostFor>.45)LeaveCover(true); return; }
        Position=EUnknownPosition::Peeking; PositionUntil=Now+(UnderPressure()?1.25f:2.6f);
    }
    if (Position==EUnknownPosition::Peeking)
    {
        if (bHasCover && (Now-LastIncomingHit<.3f ||
            (Now>=PositionUntil && bVisible && (!BowOrMagic || UnderPressure() || WantsReload()))))
            Position=EUnknownPosition::SeekCover;
        else if (!bHasFiringLane && (!BowOrMagic || LaneLostFor>.45)) LeaveCover(true);
        // Keep a useful firing position until there is a reason to hide.
        // An expired peek timer alone must not create an endless cover lap.
    }
    const bool InFiringBand=bHasFiringLane && CurrentRange>=PreferredRange*.86f && CurrentRange<=AttackRange*.91f;
    if (Position==EUnknownPosition::Adjust && (AtFootPoint(Feet,FiringPoint,32.f) ||
        (!bCrowdReposition && InFiringBand && FMath::Abs(Feet.Z-FiringPoint.Z)<=45.f)))
    { LeaveCover(!bHasFiringLane); }
    if (Position==EUnknownPosition::Open && Now>=NextReposition)
    {
        if(!CanPlanThisFrame()){NextReposition=Now+FMath::FRandRange(.10f,.25f);return;}
        NextReposition=Now+(bRetreating?FMath::FRandRange(.65f,.95f):
            bHasFiringLane?FMath::FRandRange(1.65f,2.7f):FMath::FRandRange(.75f,1.15f));
        FindFiringPosition(Target,LastKnown,bVisible);
    }
}
