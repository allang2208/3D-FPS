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
    // Directional safe stop ellipse around the horse (253 cm total length: +128 muzzle, -95 rump, +-44 flank)
    // plus the player's capsule (42 cm) and anatomical forward eye offset (56-74 cm).
    constexpr float StopFront=275.f,StopRear=245.f,StopSide=230.f;
    constexpr float ResumeMargin=60.f;
    constexpr float ParkReachRadius=42.f;
    constexpr float ParkReanchorDistance=320.f;
    constexpr float ParkSettleMinSeconds=0.18f;
    constexpr float ParkSettleMaxSeconds=1.25f;
}

float AStableRidingHorse::EffectiveStopDistanceTo(const FVector& TargetFeet,float ExtraMargin) const
{
    const FVector ToTarget=TargetFeet-GetActorLocation();
    const FVector Fwd=GetActorForwardVector().GetSafeNormal2D();
    const FVector Right=GetActorRightVector().GetSafeNormal2D();
    const float X=FVector::DotProduct(ToTarget,Fwd);
    const float Y=FVector::DotProduct(ToTarget,Right);
    const float Dist2D=FMath::Sqrt(X*X+Y*Y);
    if(Dist2D<=KINDA_SMALL_NUMBER)return HorseFollow::StopSide+ExtraMargin;
    const float AxisX=(X>=0.f?HorseFollow::StopFront:HorseFollow::StopRear)+ExtraMargin;
    const float AxisY=HorseFollow::StopSide+ExtraMargin;
    const float Elliptic=FMath::Sqrt(FMath::Square(X/AxisX)+FMath::Square(Y/AxisY));
    return Dist2D/FMath::Max(Elliptic,KINDA_SMALL_NUMBER);
}

bool AStableRidingHorse::CanHorseStandAt(const FVector& Ground,const FRotator& Heading,const AActor* IgnoreActor) const
{
    const UWorld* World=GetWorld();
    if(!World)return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HorseParkSpot),false,this);
    if(IgnoreActor)Query.AddIgnoredActor(IgnoreActor);
    const FVector Fwd=Heading.Vector().GetSafeNormal2D();
    const auto Hull=FCollisionShape::MakeCapsule(34.f,76.f);
    for(const float Along:{-54.f,0.f,56.f})
    {
        const FVector Base=Ground+Fwd*Along;
        FHitResult Floor;
        if(!World->LineTraceSingleByChannel(Floor,Base+FVector(0,0,96),Base-FVector(0,0,150),ECC_Pawn,Query)
            || !Floor.bBlockingHit || Floor.ImpactNormal.Z<.73f
            || (Floor.GetActor()&&Floor.GetActor()->IsA<APawn>())
            || FMath::Abs(Floor.ImpactPoint.Z-Ground.Z)>34.f)
            return false;
        if(World->OverlapBlockingTestByChannel(Floor.ImpactPoint+FVector(0,0,96),FQuat::Identity,ECC_Pawn,Hull,Query))
            return false;
    }
    return true;
}

bool AStableRidingHorse::ComputeRecallParkSpot(const AFPSGAMECharacter& TargetPawn,FVector& OutGoal,float& OutYaw) const
{
    const UWorld* World=GetWorld();
    if(!World)return false;
    const FVector PlayerFeet=TargetPawn.GetNavAgentLocation();
    const float PlayerYaw=TargetPawn.GetController()?TargetPawn.GetControlRotation().Yaw:TargetPawn.GetActorRotation().Yaw;
    const FVector PlayerFwd=FRotator(0,PlayerYaw,0).Vector().GetSafeNormal2D();
    const FVector PlayerRight=FRotator(0,PlayerYaw+90.f,0).Vector().GetSafeNormal2D();
    const FVector ApproachDir=(GetActorLocation()-PlayerFeet).GetSafeNormal2D();
    const float SideSign=ApproachDir.IsNearlyZero()||FVector::DotProduct(ApproachDir,PlayerRight)>=0.f?1.f:-1.f;

    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    const auto* NavData=Nav?Nav->GetNavDataForProps(HorseFollow::Agent,PlayerFeet):nullptr;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HorseParkSpot),false,this);
    Query.AddIgnoredActor(&TargetPawn);

    auto TrySpot=[&](const FVector& OffsetDir,float Dist,float CandYaw) -> bool
    {
        const FVector Sample=PlayerFeet+OffsetDir.GetSafeNormal2D()*Dist;
        FHitResult Hit;
        if(!World->LineTraceSingleByChannel(Hit,Sample+FVector(0,0,110),Sample-FVector(0,0,180),ECC_Pawn,Query)
            || !Hit.bBlockingHit || Hit.ImpactNormal.Z<.73f
            || (Hit.GetActor()&&Hit.GetActor()->IsA<APawn>())
            || FMath::Abs(Hit.ImpactPoint.Z-PlayerFeet.Z)>120.f)
            return false;
        FVector Ground=Hit.ImpactPoint;
        if(NavData)
        {
            FNavLocation Projected;
            if(!Nav->ProjectPointToNavigation(Ground,Projected,FVector(85,85,65),NavData))return false;
            if(World->LineTraceSingleByChannel(Hit,Projected.Location+FVector(0,0,96),Projected.Location-FVector(0,0,150),ECC_Pawn,Query)
                && Hit.bBlockingHit && Hit.ImpactNormal.Z>=.73f && !(Hit.GetActor()&&Hit.GetActor()->IsA<APawn>()))
                Ground=Hit.ImpactPoint;
            else return false;
        }
        // Keep the parked horse on the same walkable side of fences/walls as the player.
        if(World->SweepTestByChannel(PlayerFeet+FVector(0,0,96),Ground+FVector(0,0,96),FQuat::Identity,ECC_Pawn,
            FCollisionShape::MakeSphere(22.f),Query))
            return false;
        const FRotator Heading(0,CandYaw,0);
        if(!CanHorseStandAt(Ground,Heading,&TargetPawn))return false;
        OutGoal=Ground;
        OutYaw=CandYaw;
        return true;
    };

    // Prefer side-front angled stance so the saddle flank faces the player cleanly,
    // then degrade gracefully to side, rear-side, and narrow-corridor face-on safe distance.
    for(const float Sign:{SideSign,-SideSign})
    {
        if(TrySpot(PlayerFwd.RotateAngleAxis(Sign*55.f,FVector::UpVector),250.f,FMath::UnwindDegrees(PlayerYaw-Sign*18.f)))return true;
    }
    for(const float Sign:{SideSign,-SideSign})
    {
        if(TrySpot(PlayerFwd.RotateAngleAxis(Sign*85.f,FVector::UpVector),245.f,FMath::UnwindDegrees(PlayerYaw)))return true;
    }
    for(const float Sign:{SideSign,-SideSign})
    {
        const FVector Dir=PlayerFwd.RotateAngleAxis(Sign*125.f,FVector::UpVector);
        const float ToPlayerYaw=(-Dir).Rotation().Yaw;
        if(TrySpot(Dir,255.f,FMath::UnwindDegrees(ToPlayerYaw+Sign*68.f)))return true;
    }
    const FVector FallbackDir=ApproachDir.IsNearlyZero()?-PlayerFwd:ApproachDir;
    const float FacePlayerYaw=(-FallbackDir).Rotation().Yaw;
    for(const float Dist:{285.f,275.f})
    {
        if(TrySpot(FallbackDir,Dist,FMath::UnwindDegrees(FacePlayerYaw)))return true;
    }
    return false;
}

void AStableRidingHorse::ClearFollowRoute()
{
    if(PendingQuery!=INVALID_NAVQUERYID)
        if(auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
            Nav->AbortAsyncFindPathRequest(PendingQuery);
    PendingQuery=INVALID_NAVQUERYID;
    FollowPath.Reset();NextCorner=1;bDirectApproach=false;
}
void AStableRidingHorse::SetLeader(AFPSGAMECharacter* NewLeader,bool bParkAfterArrival)
{
    if(!HasAuthority()||(NewLeader&&(Rider||IsRetreating())))return;
    if(bFollowing)GetCharacterMovement()->bCanWalkOffLedges=bPreviouslyAllowedLedges;
    ClearFollowRoute();
    if(bNavInvoker){UNavigationSystemV1::UnregisterNavigationInvoker(*this);bNavInvoker=false;}
    Leader=NewLeader;bFollowing=NewLeader!=nullptr;bAtHeel=false;
    bRecallParking=bFollowing && bParkAfterArrival;
    RecallSettleSeconds=0.f;
    if(!bRecallParking)bHasRecallParkGoal=false;
    else if(NewLeader && !bHasRecallParkGoal)
    {
        RecallAnchorPlayer=NewLeader->GetNavAgentLocation();
        bHasRecallParkGoal=ComputeRecallParkSpot(*NewLeader,RecallParkGoal,RecallParkYaw);
    }
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
    const FVector Feet=GetNavAgentLocation();
    const float Distance=FVector::Dist2D(Feet,Goal);
    const bool bParkTarget=bRecallParking && bHasRecallParkGoal;
    const float StopDist=bParkTarget?HorseFollow::ParkReachRadius:EffectiveStopDistanceTo(Goal);
    const float ResumeDist=bParkTarget?(HorseFollow::ParkReachRadius+24.f):EffectiveStopDistanceTo(Goal,HorseFollow::ResumeMargin);
    const bool NearEnough=Distance<=(bAtHeel?ResumeDist:StopDist);
    bDirectApproach=BlockedSeconds<.45f&&WalkableApproach(Goal);
    bAtHeel=NearEnough&&(bDirectApproach||bParkTarget);
    NextPlanTime=GetWorld()->GetTimeSeconds()+(bAtHeel?.45f:.65f);
    if(bDirectApproach){FollowPath.Reset();return;}
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if(!Nav)return;
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
    const FVector PlayerFeet=Leader->GetNavAgentLocation(),Feet=GetNavAgentLocation();
    if(bRecallParking && FVector::DistSquared2D(PlayerFeet,RecallAnchorPlayer)>FMath::Square(HorseFollow::ParkReanchorDistance))
    {
        RecallAnchorPlayer=PlayerFeet;
        bHasRecallParkGoal=ComputeRecallParkSpot(*Leader,RecallParkGoal,RecallParkYaw);
        bAtHeel=false;RecallSettleSeconds=0.f;NextPlanTime=0.;
    }
    const bool bParkTarget=bRecallParking && bHasRecallParkGoal;
    const FVector Goal=bParkTarget?RecallParkGoal:PlayerFeet;
    const float Distance=FVector::Dist2D(Feet,Goal);
    const float PlayerDistance=FVector::Dist2D(Feet,PlayerFeet);
    const float PlayerStopDist=EffectiveStopDistanceTo(PlayerFeet);
    const float StopDist=bParkTarget?HorseFollow::ParkReachRadius:PlayerStopDist;
    const float ResumeDist=bParkTarget?(HorseFollow::ParkReachRadius+24.f):EffectiveStopDistanceTo(PlayerFeet,HorseFollow::ResumeMargin);
    const double Now=GetWorld()->GetTimeSeconds();
    const bool GoalMoved=FVector::DistSquared(PlannedGoal,Goal)>FMath::Square(48.f);
    const bool RouteValid=FollowPath.IsValid()&&FollowPath->IsValid();
    const bool Near=Distance<StopDist+36.f;
    if(!PendingQuery&&Now>=NextPlanTime&&
        (GoalMoved||(!RouteValid&&!bAtHeel)||(!bAtHeel&&Near)||BlockedSeconds>.45f||
         (bAtHeel&&Distance>ResumeDist)))
        PlanFollowPath(Goal);

    // If a player walks directly toward a summoning horse, halt immediately at safe distance and park.
    if(bRecallParking && !bAtHeel && PlayerDistance<=PlayerStopDist)
    {
        const FVector ToGoal=(Goal-Feet).GetSafeNormal2D();
        const FVector ToPlayer=(PlayerFeet-Feet).GetSafeNormal2D();
        if(!bParkTarget || FVector::DotProduct(ToGoal,ToPlayer)>0.2f || Distance<=HorseFollow::ParkReachRadius+32.f)
            bAtHeel=true;
    }

    if(bAtHeel)
    {
        Move->StopMovementImmediately();
        if(bRecallParking)
        {
            RecallSettleSeconds+=Delta;
            bool bAligned=true;
            if(bHasRecallParkGoal)
            {
                const float Heading=GetActorRotation().Yaw;
                const float YawErr=FMath::FindDeltaAngleDegrees(Heading,RecallParkYaw);
                bAligned=FMath::Abs(YawErr)<=12.f;
                if(!bAligned)
                {
                    const float TurnStep=105.f*Traits.TurnScale()*Delta*MovementScale;
                    const FRotator Next(0,Heading+FMath::Clamp(YawErr,-TurnStep,TurnStep),0);
                    if(ClearBody(FVector::ZeroVector,Next))SetActorRotation(Next);
                    else bAligned=true;
                }
            }
            if(RecallSettleSeconds>=HorseFollow::ParkSettleMinSeconds &&
               (bAligned || RecallSettleSeconds>=HorseFollow::ParkSettleMaxSeconds))
            {
                SetLeader(nullptr);
            }
        }
        return;
    }

    FVector Waypoint;
    if(bDirectApproach)
    {
        Waypoint=PlannedGoal;
        if(Near&&Distance<=StopDist&&FVector::DistSquared(Goal,PlannedGoal)<FMath::Square(55.f))
        {bAtHeel=true;Move->StopMovementImmediately();return;}
    }
    else if(FollowPath.IsValid()&&FollowPath->IsValid())
    {
        const auto& Points=FollowPath->GetPathPoints();
        while(Points.IsValidIndex(NextCorner)&&FVector::Dist2D(Feet,Points[NextCorner].Location)<32.f)
            ++NextCorner;
        if(!Points.IsValidIndex(NextCorner))
        {
            FollowPath.Reset();
            if(bRecallParking && (Distance<=HorseFollow::ParkReachRadius+48.f || PlayerDistance<=PlayerStopDist+24.f))
                bAtHeel=true;
            Move->StopMovementImmediately();return;
        }
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
    const float Cruise=FMath::Lerp(225.f,CatchUp,FMath::SmoothStep(StopDist+90.f,StopDist+480.f,Distance));
    const float ApproachCap=FMath::Max(85.f,(Distance-StopDist+24.f)*1.6f);
    Move->MaxWalkSpeed=(Reverse?125.f:FMath::Min(bExhausted?220.f:Cruise,ApproachCap))*Traits.SpeedScale()*MovementScale;
    const FVector Advance=GetActorForwardVector()*(Reverse?-1.f:1.f);
    // Never step deeper inside the player's directional safety envelope between replans.
    const FVector NextFeet=Feet+Advance*Move->MaxWalkSpeed*Delta;
    if(!Reverse && PlayerDistance<=PlayerStopDist && FVector::Dist2D(NextFeet,PlayerFeet)<PlayerDistance)
    {
        if(bRecallParking || bDirectApproach)bAtHeel=true;
        Move->StopMovementImmediately();
        return;
    }
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
