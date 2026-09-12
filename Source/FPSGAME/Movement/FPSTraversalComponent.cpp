#include "FPSTraversalComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "DrawDebugHelpers.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

UFPSTraversalComponent::UFPSTraversalComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

bool UFPSTraversalComponent::IsStableSurface(const UPrimitiveComponent* Surface)
{
    // Imported village props often use Movable even though they never move.
    // Mobility is an editor capability, not evidence of current motion.
    return IsValid(Surface) && Surface->IsRegistered() && Surface->IsQueryCollisionEnabled() &&
        Surface->GetOwner() && Surface->GetOwner()->GetActorEnableCollision() && !Cast<APawn>(Surface->GetOwner()) &&
        !Surface->IsSimulatingPhysics() && Surface->GetComponentVelocity().SizeSquared()<=1.f;
}

bool UFPSTraversalComponent::IsBlockingSupport(const UPrimitiveComponent* Surface) const
{
    const auto* C=CastChecked<ACharacter>(GetOwner());
    const auto* Capsule=C->GetCapsuleComponent();
    return IsStableSurface(Surface) &&
        Surface->GetCollisionResponseToChannel(Capsule->GetCollisionObjectType())==ECR_Block &&
        Capsule->GetCollisionResponseToChannel(Surface->GetCollisionObjectType())==ECR_Block;
}

void UFPSTraversalComponent::BeginPlay()
{
    Super::BeginPlay();
    bDebugQueries = FParse::Param(FCommandLine::Get(), TEXT("TraversalProbeDebug"));
    bRuntimeAudit = FParse::Param(FCommandLine::Get(), TEXT("TraversalRuntimeAudit"));
    InitializePresentation();
}

FFPSTraversalTarget UFPSTraversalComponent::FindTarget(bool bJumpPressed, bool bAvailable) const
{
    FFPSTraversalTarget Result;
    const auto Reject = [&](const TCHAR* Why) { Result.Reason=Why; return Result; };
    const ACharacter* Character = Cast<ACharacter>(GetOwner());
    if (!Character || !GetWorld()) return Reject(TEXT("NoCharacter"));
    const auto* Movement = Character->GetCharacterMovement();
    const auto* Capsule = Character->GetCapsuleComponent();
    const auto* Rules = GetDefault<UFPSTraversalSettings>();
    auto& P = Result.Probe;
    P.bJumpPressed=bJumpPressed; P.bTraversalAvailable=bAvailable;
    P.bStandingGrounded=Movement && Movement->IsMovingOnGround() && !Character->bIsCrouched;
    P.bAirborne=Movement && Movement->IsFalling() && !Character->bIsCrouched;
    if (!Rules->IsValidConfiguration() || !bJumpPressed || !bAvailable || (!P.bStandingGrounded && !P.bAirborne))
        return Reject(TEXT("Unavailable"));
    if (P.bAirborne && Movement->Velocity.Z < -Rules->AirMaxFallSpeed)
        return Reject(TEXT("FallingTooFast"));
    const FVector Up=FVector::UpVector;
    // Look intent chooses the wall, independently of movement or body yaw.
    // Use view yaw so looking up/down at the lip does not shorten horizontal reach.
    FVector Forward=FRotator(0.f,Character->GetViewRotation().Yaw,0.f).Vector();
    const FVector Start=Character->GetActorLocation();
    const float Radius=Capsule->GetScaledCapsuleRadius(), Half=Capsule->GetScaledCapsuleHalfHeight();
    const FName Profile=Capsule->GetCollisionProfileName();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSTraversal),false,Character);
    const auto Ray=[&](FHitResult& Hit,FVector A,FVector B)
    { return GetWorld()->LineTraceSingleByProfile(Hit,A,B,Profile,Params) && !Hit.bStartPenetrating; };
    FHitResult Ground;
    const FVector Feet=Start-Up*Half;
    float FloorZ=Feet.Z;
    if (!P.bAirborne)
    {
        if (!Ray(Ground,Feet+Up*10.f,Feet-Up*25.f) || !Movement->IsWalkable(Ground))
            return Reject(TEXT("NoGroundSupport"));
        FloorZ=Ground.ImpactPoint.Z;
    }
    // In air use the current capsule's reach, not a fictional floor underneath it.
    // Chest, knee and low probes let a jump catch both tall walls and a nearly-cleared lip.
    FHitResult Wall;
    // Keep physical wall clearance independent of the allowed view angle.
    const float MinFacingDot=FMath::Cos(FMath::DegreesToRadians(Rules->MaxFacingAngle));
    const float WallRange=(Radius+Rules->MaxEdgeDistance)/MinFacingDot;
    const auto WallAt=[&](float Height)
    {
        const FVector A(Start.X,Start.Y,FloorZ+Height);
        return Ray(Wall,A,A+Forward*WallRange);
    };
    const bool bWallHit=P.bAirborne?(WallAt(Half) || WallAt(50.f) || WallAt(10.f)):WallAt(Rules->StepHeight+.05f);
    if (!bWallHit) return Reject(TEXT("NoWallInReach"));
    Result.Obstacle=Wall.GetComponent();
    P.bStableObstacle=IsStableSurface(Result.Obstacle);
    P.EdgeDistance=FMath::Max(0.f,FVector::DotProduct(Wall.ImpactPoint-Start,-Wall.ImpactNormal.GetSafeNormal2D())-Radius);
    P.FacingDot=FVector::DotProduct(Forward,-Wall.ImpactNormal.GetSafeNormal2D());
    if (!P.bStableObstacle) return Reject(TEXT("UnstableObstacle"));
    if (P.FacingDot < MinFacingDot) return Reject(TEXT("ObliqueWall"));
    if (P.EdgeDistance>Rules->MaxEdgeDistance) return Reject(TEXT("TooFarFromWall"));
    // Facing is an input gate. Support pads and depth must follow the wall, not
    // camera yaw: a slight look angle otherwise puts one palm outside a wide ledge.
    Result.WallNormal=Wall.ImpactNormal.GetSafeNormal2D();
    Forward=-Result.WallNormal;
    const FVector Right=FVector::CrossProduct(Up,Forward);
    // Search a small depth band: a 2 cm point alone often falls outside a
    // bevelled or broken stone lip. Hands need a grippable lip, not a walkable floor.
    const auto FindLip=[&](FHitResult& Best,FVector At)
    {
        bool Found=false;
        for (float Depth : {2.f,8.f,16.f,24.f,32.f})
        {
            const FVector XY=At+Forward*Depth;
            FHitResult Hit;
            if (Ray(Hit,FVector(XY.X,XY.Y,FloorZ+(P.bAirborne?Rules->AirMaxLedgeHeight:Rules->MantleMaxHeight)+20.f),
                FVector(XY.X,XY.Y,FloorZ+(P.bAirborne?Rules->AirMinLedgeHeight-.1f:Rules->StepHeight))) && IsStableSurface(Hit.GetComponent()) &&
                Hit.ImpactNormal.Z>.2f && (!Found || Hit.ImpactPoint.Z>Best.ImpactPoint.Z))
            { Best=Hit; Found=true; }
        }
        return Found;
    };
    FHitResult Top;
    if (!FindLip(Top,Wall.ImpactPoint)) return Reject(TEXT("NoReachableTop"));
    Result.Supports.AddUnique(Top.GetComponent());
    P.bTopGrippable=true;
    const float PadRadius=Radius;
    float LipHeight=Top.ImpactPoint.Z;
    for (float Side : {-1.f,1.f})
    {
        FHitResult Support;
        if (!FindLip(Support,Wall.ImpactPoint+Right*Side*28.f) ||
            FMath::Abs(Support.ImpactPoint.Z-Top.ImpactPoint.Z)>30.f)
            return Reject(TEXT("NarrowOrBrokenEdge"));
        Result.Supports.AddUnique(Support.GetComponent());
        LipHeight=FMath::Max(LipHeight,(float)Support.ImpactPoint.Z);
        // Pass the same accepted per-hand lip into animation. A second, stricter
        // surface test in the pose layer used to reject eligible broken/steep lips.
        FHitResult Face;
        FVector Hold=FVector(Wall.ImpactPoint.X,Wall.ImpactPoint.Y,Support.ImpactPoint.Z)+Right*Side*28.f;
        const FVector Seed=Support.ImpactPoint-Up*4.f;
        if (Ray(Face,Seed-Forward*60.f,Seed+Forward*20.f) && IsStableSurface(Face.GetComponent()))
        {
            Hold=Face.ImpactPoint+Face.ImpactNormal*5.f;
            Hold.Z=Support.ImpactPoint.Z+3.f;
            Result.Supports.AddUnique(Face.GetComponent());
        }
        else Hold+=Result.WallNormal*5.f+Up*3.f;
        FFPSTraversalHandhold Handhold; Handhold.Position=Hold; Handhold.Normal=Support.ImpactNormal;
        Result.Handholds.Add(Handhold);
    }
    P.Height=LipHeight-FloorZ;
    Result.FrontEdge=FVector(Wall.ImpactPoint.X,Wall.ImpactPoint.Y,LipHeight);
    P.bAirReachable=P.bAirborne && P.Height>=Rules->AirMinLedgeHeight && P.Height<=Rules->AirMaxLedgeHeight;
    const auto HeightClass=P.bAirborne
        ?(P.bAirReachable?(P.Height<=Rules->VaultMaxHeight?EFPSTraversalAction::Vault:EFPSTraversalAction::Mantle):EFPSTraversalAction::None)
        :Rules->ClassifyHeight(P.Height);
    if (HeightClass==EFPSTraversalAction::None || HeightClass==EFPSTraversalAction::Step)
        return Reject(TEXT("HeightOutOfRange"));
    // The back-face measurement is a starting estimate, not proof that a
    // fractured mesh has a capsule-wide clear landing at exactly that distance.
    const float DepthLimit=Rules->VaultMaxDepth+120.f;
    const FVector DepthStart=Result.FrontEdge+Forward*DepthLimit-Up*2.f;
    FHitResult Back;
    const bool bBackHit=Result.Obstacle->LineTraceComponent(Back,DepthStart,Result.FrontEdge-Forward,Params);
    P.Depth=bBackHit && !Back.bStartPenetrating
        ? FVector::DotProduct(Back.ImpactPoint-Result.FrontEdge,Forward) : DepthLimit;
    const auto StandingSpace=[&](FVector Foot)
    {
        return !GetWorld()->OverlapBlockingTestByProfile(Foot+Up*(Half+2.f),FQuat::Identity,Profile,
            FCollisionShape::MakeCapsule(Radius,Half),Params);
    };
    const auto SupportedPad=[&](FHitResult& Center,TArray<TObjectPtr<UPrimitiveComponent>>& Supports)
    {
        // Sample corners and edge midpoints. Accept modest unevenness, but reject
        // holes and steep surfaces; stand above the highest sampled support.
        float Highest=Center.ImpactPoint.Z;
        for (float X : {-1.f,0.f,1.f}) for (float Y : {-1.f,0.f,1.f})
        {
            const FVector Pos=Center.ImpactPoint+(Forward*X+Right*Y).GetClampedToMaxSize(1.f)*(PadRadius-1.f);
            FHitResult Support;
            if (!Ray(Support,Pos+Up*60.f,Pos-Up*60.f) || !IsStableSurface(Support.GetComponent()) || !Movement->IsWalkable(Support) ||
                FMath::Abs(FVector::DotProduct(Support.ImpactPoint-Center.ImpactPoint,Center.ImpactNormal))>8.f)
                return false;
            Supports.AddUnique(Support.GetComponent());
            Highest=FMath::Max(Highest,(float)Support.ImpactPoint.Z);
        }
        Center.ImpactPoint.Z=Highest;
        return StandingSpace(Center.ImpactPoint);
    };
    const auto ClearSegment=[&](FVector A,FVector B)
    {
        FHitResult Hit;
        return !GetWorld()->SweepSingleByProfile(Hit,A,B,FQuat::Identity,Profile,
            FCollisionShape::MakeCapsule(Radius,Half),Params);
    };
    Result.RaisedStart=FVector(Start.X,Start.Y,LipHeight+Half+3.f);
    FVector MantleFoot=Result.FrontEdge+Forward*(PadRadius+2.f);
    TArray<TObjectPtr<UPrimitiveComponent>> MantleSupports,VaultSupports;
    FHitResult MantleSupport;
    if (Ray(MantleSupport,MantleFoot+Up*60.f,MantleFoot-Up*60.f) &&
        IsStableSurface(MantleSupport.GetComponent()) && Movement->IsWalkable(MantleSupport))
    {
        P.bTopStandingSpace=SupportedPad(MantleSupport,MantleSupports);
        MantleFoot=MantleSupport.ImpactPoint;
    }
    Result.RaisedStart.Z=FMath::Max(Result.RaisedStart.Z,MantleFoot.Z+Half+3.f);
    P.bApproachClear=ClearSegment(Start,Result.RaisedStart);
    const FVector MantleEnd=MantleFoot+Up*(Half+2.f);
    const FVector MantleRaised=FVector(MantleEnd.X,MantleEnd.Y,Result.RaisedStart.Z);
    P.bMantlePathClear=P.bApproachClear && ClearSegment(Result.RaisedStart,MantleRaised) && ClearSegment(MantleRaised,MantleEnd);
    FVector VaultEnd=FVector::ZeroVector, VaultRaised=FVector::ZeroVector;
    if (HeightClass==EFPSTraversalAction::Vault)
    {
        const float FirstDepth=P.Depth>0.f && P.Depth<=Rules->VaultMaxDepth?P.Depth:20.f;
        // Bound the search by the allowed obstacle depth. Every candidate still
        // needs standing support, headroom and the entire swept route.
        for (float Depth=FirstDepth;;Depth=FMath::Min(Depth+20.f,Rules->VaultMaxDepth))
        {
            const FVector LandingXY=Result.FrontEdge+Forward*(Depth+PadRadius+2.f);
            FHitResult Landing;
            if (Ray(Landing,FVector(LandingXY.X,LandingXY.Y,FloorZ+Rules->MaxLandingRise+1.f),
                FVector(LandingXY.X,LandingXY.Y,FloorZ-(P.bAirborne?Rules->AirMaxLandingDrop:Rules->MaxLandingDrop)-1.f)) && Movement->IsWalkable(Landing))
            {
                VaultSupports.Reset();
                if (SupportedPad(Landing,VaultSupports))
                {
                    VaultEnd=Landing.ImpactPoint+Up*(Half+2.f);
                    for (float Lift : {0.f,10.f,20.f})
                    {
                        if (P.Height+Lift>Rules->VaultMaxHeight) continue;
                        const FVector Raised=FVector(Start.X,Start.Y,LipHeight+Half+3.f+Lift);
                        VaultRaised=FVector(VaultEnd.X,VaultEnd.Y,Raised.Z);
                        if (ClearSegment(Start,Raised) && ClearSegment(Raised,VaultRaised) && ClearSegment(VaultRaised,VaultEnd))
                        {
                            Result.RaisedStart=Raised;
                            P.bApproachClear=P.bVaultPathClear=P.bLandingStandingSpace=true;
                            P.LandingHeightDelta=Landing.ImpactPoint.Z-FloorZ; P.Depth=Depth;
                            break;
                        }
                    }
                }
            }
            if (P.bVaultPathClear || Depth>=Rules->VaultMaxDepth) break;
        }
    }
    Result.Action=Rules->Evaluate(P);
    const bool bVault=Result.Action==EFPSTraversalAction::Vault;
    for (const auto& Support:bVault?VaultSupports:MantleSupports) Result.Supports.AddUnique(Support);
    Result.Destination=bVault?VaultEnd:MantleEnd;
    Result.RaisedEnd=bVault?VaultRaised:MantleRaised;
    Result.Reason=Result.Action==EFPSTraversalAction::None?TEXT("InsufficientSpaceOrPath"):TEXT("Eligible");
    return Result;
}

void UFPSTraversalComponent::InspectJump(bool bAvailable)
{
    LastJumpTarget=FindTarget(true,bAvailable);
    if (!bDebugQueries) return;
    const auto& T=LastJumpTarget;
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_PROBE action=%d height=%.2f depth=%.2f reason=%s"),
        static_cast<int32>(T.Action),T.Probe.Height,T.Probe.Depth,*T.Reason);
    if (T.Action!=EFPSTraversalAction::None)
    {
        DrawDebugSphere(GetWorld(),T.FrontEdge,8.f,12,FColor::Yellow,false,3.f);
        DrawDebugLine(GetWorld(),GetOwner()->GetActorLocation(),T.RaisedStart,FColor::Green,false,3.f);
        DrawDebugLine(GetWorld(),T.RaisedStart,T.RaisedEnd,FColor::Green,false,3.f);
        DrawDebugLine(GetWorld(),T.RaisedEnd,T.Destination,FColor::Green,false,3.f);
    }
}
