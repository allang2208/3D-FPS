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
    if (!Rules->IsValidConfiguration() || !bJumpPressed || !bAvailable || !P.bStandingGrounded)
        return Reject(TEXT("Unavailable"));
    const FVector Up=FVector::UpVector;
    FVector Forward=Character->GetActorForwardVector().GetSafeNormal2D();
    const FVector Start=Character->GetActorLocation();
    const float Radius=Capsule->GetScaledCapsuleRadius(), Half=Capsule->GetScaledCapsuleHalfHeight();
    const FName Profile=Capsule->GetCollisionProfileName();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSTraversal),false,Character);
    const auto Ray=[&](FHitResult& Hit,FVector A,FVector B)
    { return GetWorld()->LineTraceSingleByProfile(Hit,A,B,Profile,Params) && !Hit.bStartPenetrating; };
    FHitResult Ground;
    const FVector Feet=Start-Up*Half;
    if (!Ray(Ground,Feet+Up*10.f,Feet-Up*25.f) || !Movement->IsWalkable(Ground))
        return Reject(TEXT("NoGroundSupport"));
    const float FloorZ=Ground.ImpactPoint.Z;
    const FVector WallStart=FVector(Start.X,Start.Y,FloorZ+Rules->StepHeight+.05f);
    FHitResult Wall;
    // Keep physical wall clearance independent of the allowed view angle.
    const float MinFacingDot=FMath::Cos(FMath::DegreesToRadians(Rules->MaxFacingAngle));
    if (!Ray(Wall,WallStart,WallStart+Forward*((Radius+Rules->MaxEdgeDistance)/MinFacingDot)))
        return Reject(TEXT("NoWallAboveStep"));
    Result.Obstacle=Wall.GetComponent();
    P.bStaticObstacle=Result.Obstacle && Result.Obstacle->Mobility==EComponentMobility::Static;
    P.EdgeDistance=FMath::Max(0.f,FVector::DotProduct(Wall.ImpactPoint-Start,-Wall.ImpactNormal.GetSafeNormal2D())-Radius);
    P.FacingDot=FVector::DotProduct(Forward,-Wall.ImpactNormal.GetSafeNormal2D());
    if (!P.bStaticObstacle || P.FacingDot < MinFacingDot)
        return Reject(TEXT("MovingOrObliqueWall"));
    if (P.EdgeDistance>Rules->MaxEdgeDistance) return Reject(TEXT("TooFarFromWall"));
    // Facing is an input gate. Support pads and depth must follow the wall, not
    // camera yaw: a slight look angle otherwise puts one palm outside a wide ledge.
    Result.WallNormal=Wall.ImpactNormal.GetSafeNormal2D();
    Forward=-Result.WallNormal;
    const FVector Right=FVector::CrossProduct(Up,Forward);
    FVector TopXY=Wall.ImpactPoint+Forward*2.f;
    FHitResult Top;
    if (!Ray(Top,FVector(TopXY.X,TopXY.Y,FloorZ+Rules->MantleMaxHeight+20.f),
        FVector(TopXY.X,TopXY.Y,FloorZ+Rules->StepHeight)) || Top.GetComponent()!=Result.Obstacle)
        return Reject(TEXT("NoReachableTop"));
    P.Height=Top.ImpactPoint.Z-FloorZ;
    P.bTopWalkable=Movement->IsWalkable(Top);
    Result.FrontEdge=FVector(Wall.ImpactPoint.X,Wall.ImpactPoint.Y,Top.ImpactPoint.Z);
    const auto HeightClass=Rules->ClassifyHeight(P.Height);
    if (HeightClass==EFPSTraversalAction::None || HeightClass==EFPSTraversalAction::Step || !P.bTopWalkable)
        return Reject(TEXT("HeightOrSlope"));
    // Reverse trace measures the back face, including exact 120 cm depth boundaries.
    // A solid starting point indicates a broad platform; 240 cm is a lower bound.
    const float DepthLimit=FMath::Max(Rules->VaultMaxDepth,Rules->MantleMinDepth)+120.f;
    const FVector DepthStart=Result.FrontEdge+Forward*DepthLimit-Up*2.f;
    FHitResult Back;
    // Measure only this obstacle. A separate far-side blocker must not prevent
    // the legitimate fallback of climbing onto an otherwise clear wide top.
    const bool bBackHit=Result.Obstacle->LineTraceComponent(Back,DepthStart,Result.FrontEdge-Forward,Params);
    P.Depth=bBackHit && !Back.bStartPenetrating
        ? FVector::DotProduct(Back.ImpactPoint-Result.FrontEdge,Forward) : DepthLimit;
    // Full standing capsule clearance, with 8 cm side and 10 cm headroom margin.
    const float PadRadius=Radius+8.f;
    for (float Side : {-1.f,1.f})
    {
        const FVector PalmEdge=Top.ImpactPoint+Right*Side*(PadRadius-1.f);
        FHitResult Support;
        if (!Ray(Support,PalmEdge+Up*30.f,PalmEdge-Up*30.f) || Support.GetComponent()!=Result.Obstacle ||
            !Movement->IsWalkable(Support) || FMath::Abs(FVector::DotProduct(Support.ImpactPoint-Top.ImpactPoint,Top.ImpactNormal))>8.f)
            return Reject(TEXT("NarrowOrBrokenEdge"));
    }
    const auto StandingSpace=[&](FVector Foot)
    {
        return !GetWorld()->OverlapBlockingTestByProfile(Foot+Up*(Half+6.f),FQuat::Identity,Profile,
            FCollisionShape::MakeCapsule(PadRadius,Half+5.f),Params);
    };
    const auto SupportedPad=[&](FHitResult& Center)
    {
        // Sample corners and edge midpoints. Accept modest unevenness, but reject
        // holes and steep surfaces; stand above the highest sampled support.
        float Highest=Center.ImpactPoint.Z;
        for (float X : {-1.f,0.f,1.f}) for (float Y : {-1.f,0.f,1.f})
        {
            const FVector Pos=Center.ImpactPoint+(Forward*X+Right*Y)*(PadRadius-1.f);
            FHitResult Support;
            if (!Ray(Support,Pos+Up*60.f,Pos-Up*60.f) || !Movement->IsWalkable(Support) ||
                FMath::Abs(FVector::DotProduct(Support.ImpactPoint-Center.ImpactPoint,Center.ImpactNormal))>8.f)
                return false;
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
    Result.RaisedStart=FVector(Start.X,Start.Y,Top.ImpactPoint.Z+Half+11.f);
    P.bApproachClear=ClearSegment(Start,Result.RaisedStart);
    FVector MantleFoot=Result.FrontEdge+Forward*FMath::Max(PadRadius,Rules->MantleMinDepth*.5f);
    FHitResult MantleSupport;
    if (Ray(MantleSupport,MantleFoot+Up*60.f,MantleFoot-Up*60.f) &&
        MantleSupport.GetComponent()==Result.Obstacle && Movement->IsWalkable(MantleSupport))
    {
        P.bTopStandingSpace=SupportedPad(MantleSupport);
        MantleFoot=MantleSupport.ImpactPoint;
    }
    Result.RaisedStart.Z=FMath::Max(Result.RaisedStart.Z,MantleFoot.Z+Half+11.f);
    P.bApproachClear=ClearSegment(Start,Result.RaisedStart);
    const FVector MantleEnd=MantleFoot+Up*(Half+2.f);
    const FVector MantleRaised=FVector(MantleEnd.X,MantleEnd.Y,Result.RaisedStart.Z);
    P.bMantlePathClear=P.bApproachClear && ClearSegment(Result.RaisedStart,MantleRaised) && ClearSegment(MantleRaised,MantleEnd);
    FVector VaultEnd=FVector::ZeroVector, VaultRaised=FVector::ZeroVector;
    if (P.Depth<=Rules->VaultMaxDepth)
    {
        const FVector LandingXY=Result.FrontEdge+Forward*(P.Depth+PadRadius+2.f);
        FHitResult Landing;
        if (Ray(Landing,FVector(LandingXY.X,LandingXY.Y,FloorZ+Rules->MaxLandingRise+1.f),
            FVector(LandingXY.X,LandingXY.Y,FloorZ-Rules->MaxLandingDrop-1.f)) && Movement->IsWalkable(Landing))
        {
            P.LandingHeightDelta=Landing.ImpactPoint.Z-FloorZ;
            P.bLandingStandingSpace=SupportedPad(Landing);
            VaultEnd=Landing.ImpactPoint+Up*(Half+2.f);
            VaultRaised=FVector(VaultEnd.X,VaultEnd.Y,Result.RaisedStart.Z);
            P.bVaultPathClear=P.bApproachClear && ClearSegment(Result.RaisedStart,VaultRaised) && ClearSegment(VaultRaised,VaultEnd);
        }
    }
    Result.Action=Rules->Evaluate(P);
    const bool bVault=Result.Action==EFPSTraversalAction::Vault;
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
