#include "FPSPlayerBodyComponent.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "../Production/ProductionToolComponent.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "Camera/CameraTypes.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "Engine/World.h"

namespace
{
bool ResolveHorseCameraPoint(const AFPSGAMECharacter& Pawn,FVector& WorldPoint)
{
    const UWorld* World=Pawn.GetWorld();
    const auto* Capsule=Pawn.GetCapsuleComponent();
    if(!World || !Capsule)return false;
    const FVector Center=Capsule->GetComponentLocation();
    const double Half=Capsule->GetScaledCapsuleHalfHeight();
    const double SafeHalf=FMath::Max(0.,Half-Capsule->GetScaledCapsuleRadius());
    const FVector Anchor=Center+FVector(0.,0.,FMath::Clamp(WorldPoint.Z-Center.Z,-SafeHalf,SafeHalf));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(HorseCameraClearance),false,&Pawn);
    if(const auto* Ride=Pawn.FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->Active()&&IsValid(Ride->GetMount()))
        Params.AddIgnoredActor(Ride->GetMount());
    constexpr float HorseEyeRadius=9.5f;
    const auto Shape=FCollisionShape::MakeSphere(HorseEyeRadius);
    FHitResult Hit;
    bool bHitHorse=false;
    for(int32 Pass=0;Pass<3;++Pass)
    {
        if(!World->SweepSingleByChannel(Hit,Anchor,WorldPoint,FQuat::Identity,ECC_Camera,Shape,Params)||!Hit.bBlockingHit)
            break;
        if(Hit.GetActor() && Hit.GetActor()->IsA<AStableRidingHorse>())
        {
            bHitHorse=true;
            break;
        }
        // A nearby wall slightly inside the horse probe radius should not mask a horse directly behind it.
        if(Hit.GetActor())Params.AddIgnoredActor(Hit.GetActor());
        else break;
    }
    if(!bHitHorse)return false;
    if(!Hit.bStartPenetrating)
    {
        WorldPoint=FMath::Lerp(Anchor,WorldPoint,FMath::Max(0.f,Hit.Time-.015f));
        return true;
    }
    // A horse turning its head or neck into a stationary player can penetrate the capsule axis.
    // Push the camera cleanly out of the horse while guarding against any wall behind the player.
    FVector Safe=Anchor;
    for(int32 Attempt=0;Attempt<3 && Hit.bStartPenetrating;++Attempt)
    {
        const FVector Step=Hit.Normal*FMath::Min(Hit.PenetrationDepth+1.5f,Capsule->GetScaledCapsuleRadius()*.85f);
        const FVector Candidate=Safe+Step;
        FCollisionQueryParams WallQuery(SCENE_QUERY_STAT(HorseCameraWallGuard),false,&Pawn);
        if(Hit.GetActor())WallQuery.AddIgnoredActor(Hit.GetActor());
        FHitResult WallHit;
        if(World->SweepSingleByChannel(WallHit,Safe,Candidate,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(6.f),WallQuery))
            Safe=WallHit.bStartPenetrating?Safe:FMath::Lerp(Safe,Candidate,FMath::Max(0.f,WallHit.Time-.02f));
        else Safe=Candidate;
        if(!World->SweepSingleByChannel(Hit,Safe,Safe+FVector(0,0,.01f),FQuat::Identity,ECC_Camera,Shape,Params)
            || !Hit.GetActor() || !Hit.GetActor()->IsA<AStableRidingHorse>())
            break;
    }
    WorldPoint=Safe;
    return true;
}
}

void AFPSGAMECharacter::CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult)
{
    Super::CalcCamera(DeltaTime, OutResult);
    if (auto* Rest=FindComponentByClass<UFPSFurnitureRestComponent>())Rest->ApplyCamera(OutResult);
    if (auto* Body = FindComponentByClass<UFPSPlayerBodyComponent>())
    {
        if(IsLocallyControlled())
            if(const auto* Ride=FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->Active())
            {
                OutResult.Location+=Ride->SaddleViewCorrection();
                if(!Body->IsThirdPersonViewEnabled())
                {
                    const float Aim=Bow&&Bow->IsEquipped()?Bow->AimZoomAlpha():CameraADSFactor;
                    OutResult.Location+=Ride->SeatedViewOffset()*FMath::Clamp(CameraMotionScale/.45f,0.f,1.5f)
                        *(1.f-FMath::SmoothStep(0.f,1.f,Aim));
                }
            }
        Body->ConstrainCloseCameraPoint(OutResult.Location);
        Body->ApplyCameraView(OutResult);Body->ApplyReactionCamera(DeltaTime,OutResult);
        // Additive camera layers are applied after the component transform.
        // Keep the rendered owner eye inside the same leap collision boundary;
        // the fixed/rear third-person observation camera has its own contract.
        if(!Body->IsThirdPersonViewEnabled())
            if(const auto* Tool=FindComponentByClass<UProductionToolComponent>())Tool->ConstrainLeapStrikeView(OutResult.Location);
    }
}

void UFPSPlayerBodyComponent::RestoreCloseCameraClearance()
{
    if(!AppliedCloseCameraOffset.IsNearlyZero() && Character.IsValid() && Character->FirstPersonCamera)
        Character->FirstPersonCamera->SetRelativeLocation(Character->FirstPersonCamera->GetRelativeLocation()-AppliedCloseCameraOffset);
    AppliedCloseCameraOffset=FVector::ZeroVector;
}

void UFPSPlayerBodyComponent::UpdateCloseCameraClearance(float Delta)
{
    AppliedCloseCameraOffset=FVector::ZeroVector;
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!Character->FirstPersonCamera||IsThirdPersonViewEnabled()
        ||IsDeathViewActive()||UFPSFurnitureRestComponent::IsResting(Character.Get())||IsWorkstationIdle()||Character->IsTraversing())
    {
        CloseCameraClearanceOffset=FVector::ZeroVector;
        return;
    }
    const FVector Desired=Character->FirstPersonCamera->GetComponentLocation();
    FVector Safe=Desired;
    const bool bBlocked=ResolveHorseCameraPoint(*Character,Safe);
    const FQuat Frame=Character->GetActorQuat();
    const FVector Required=bBlocked?Frame.UnrotateVector(Safe-Desired):FVector::ZeroVector;
    // Retract immediately when a horse enters the eye envelope; glide back smoothly once clear.
    if(bBlocked && Required.SizeSquared()>=CloseCameraClearanceOffset.SizeSquared())
        CloseCameraClearanceOffset=Required;
    else
        CloseCameraClearanceOffset=FMath::VInterpConstantTo(CloseCameraClearanceOffset,Required,FMath::Max(0.f,Delta),220.f);
    if(!CloseCameraClearanceOffset.IsNearlyZero(.05f))
    {
        FVector Applied=Desired+Frame.RotateVector(CloseCameraClearanceOffset);
        if(ResolveHorseCameraPoint(*Character,Applied))
            CloseCameraClearanceOffset=Frame.UnrotateVector(Applied-Desired);
        const FVector BeforeRel=Character->FirstPersonCamera->GetRelativeLocation();
        Character->FirstPersonCamera->SetWorldLocation(Applied);
        AppliedCloseCameraOffset=Character->FirstPersonCamera->GetRelativeLocation()-BeforeRel;
    }
}

void UFPSPlayerBodyComponent::ConstrainCloseCameraPoint(FVector& WorldPoint) const
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||IsThirdPersonViewEnabled()
        ||IsDeathViewActive()||UFPSFurnitureRestComponent::IsResting(Character.Get())||IsWorkstationIdle()||Character->IsTraversing())
        return;
    ResolveHorseCameraPoint(*Character,WorldPoint);
}

bool UFPSPlayerBodyComponent::IsThirdPersonViewEnabled() const
{
    return Character.IsValid() && Character->IsLocallyControlled() &&
        UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Character.Get(), EDevelopmentTuningOption::ThirdPersonView);
}

bool UFPSPlayerBodyComponent::IsFixedThirdPersonViewEnabled() const
{
    return IsThirdPersonViewEnabled() &&
        UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Character.Get(), EDevelopmentTuningOption::FixedThirdPersonView);
}

void UFPSPlayerBodyComponent::RefreshViewMode()
{
    if (!IsFixedThirdPersonViewEnabled()) bFixedThirdPersonCameraCaptured=false;
    UpdateOwnerVisibility();
}

void UFPSPlayerBodyComponent::ApplyInteractionView(FVector& Eye, FRotator& View) const
{
    if (IsThirdPersonViewEnabled() && Character->FirstPersonCamera)
    {
        Eye = Character->FirstPersonCamera->GetComponentLocation();
        View = Character->FirstPersonCamera->GetComponentRotation();
    }
}

void UFPSPlayerBodyComponent::UpdateWorldOwnerVisibility(bool bHideFromOwner)
{
    // The fallback includes its head in the same mesh; keep it out of the
    // first-person death camera just as the separate real head would be.
    FPSBodyEquipment::ApplyOwnerVisibilityFlags(InitialAppearanceFallback,false,
        bHideFromOwner||((IsDeathViewActive()||UHorseRiderComponent::IsRiding(Character.Get()))&&!IsThirdPersonViewEnabled()));
    // 这条路径由 CalcCamera 每帧驱动，是「每帧重注册」的主要嫌疑位置。
    UFPSPerformanceMetricsSubsystem::CountWorldVisibilityUpdate(this);
    FFPSPerformanceScope PerformanceScope(this,TEXT("PlayerBody.WorldVisibility"));
    // fps.body.WorldBody 0 keeps these components hidden regardless of the view mode.
    // This path runs from CalcCamera on every camera update, so without the early out
    // it would put the body straight back on screen.
    if (IsWorldBodyPresentationHidden())
    {
        ApplyWorldBodyVisibility();
        return;
    }
    // CalcCamera runs on every camera update, so this must be a no-op when the
    // answer has not changed: SetOwnerNoSee dirties the render state.
    FPSBodyEquipment::ApplyOwnerVisibilityFlags(GetBodyMesh(),/*bOnlyOwnerSee=*/false,bHideFromOwner);
    for (auto Weapon : WorldWeapons) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Weapon,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    for (auto Part : WorldParts) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Part,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    for (auto Prop : WorldReloadProps) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Prop,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    UpdateBowVisibility(bHideFromOwner);
    FPSBodyEquipment::ApplyOwnerVisibilityFlags(WorldFloatingBook,false,bHideFromOwner);
    for (auto Outfit : OutfitMeshes) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Outfit,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    for (auto Outfit : OutfitStaticMeshes) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Outfit,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    // Owner visibility must not re-enable shadows on hidden or stowed equipment.
    ApplyWorldBodyShadow();
}

void UFPSPlayerBodyComponent::ApplyCameraView(FMinimalViewInfo& View)
{
    if(ApplyDeathCameraView(View))return;
    bool bClose=false;
    if(Character.IsValid()&&!IsThirdPersonViewEnabled()&&!IsDeathViewActive()&&!UFPSFurnitureRestComponent::IsResting(Character.Get()))
    {
        const bool bHasLowerBody=FirstPersonLowerBody&&ShouldShowFirstPersonLowerBody();
        const bool bCheckTorso=UHorseRiderComponent::IsRiding(Character.Get())
            || !CloseCameraClearanceOffset.IsNearlyZero(1.f)
            || bHasLowerBody;
        if(bCheckTorso)
            if(const auto* Body=GetBodyMesh();Body&&Body->GetBoneIndex(TEXT("neck_01"))!=INDEX_NONE)
            {
                const FVector Spine3=Body->GetSocketLocation(TEXT("spine_03"));
                const FVector Head=Body->GetSocketLocation(TEXT("head"));
                const FVector UpperTorso=FMath::ClosestPointOnSegment(View.Location,Spine3,Head);
                bClose=FVector::DistSquared(View.Location,UpperTorso)<FMath::Square(bRideEyeOccluded?28.f:23.f);
                if(!bClose&&bHasLowerBody&&Body->GetBoneIndex(TEXT("pelvis"))!=INDEX_NONE)
                {
                    const FVector Pelvis=Body->GetSocketLocation(TEXT("pelvis"));
                    const FVector LowerTorso=FMath::ClosestPointOnSegment(View.Location,Pelvis,Spine3);
                    bClose=FVector::DistSquared(View.Location,LowerTorso)<FMath::Square(bRideEyeOccluded?26.f:22.f);
                    if(!bClose&&View.Location.Z>=Pelvis.Z-10.&&View.Location.Z<=Head.Z+18.)
                    {
                        const FVector Forward=Character->GetActorForwardVector().GetSafeNormal2D();
                        double FrontDot=FVector::DotProduct(Pelvis,Forward);
                        for(const FName Bone:{FName(TEXT("spine_01")),FName(TEXT("spine_03")),FName(TEXT("spine_05")),FName(TEXT("neck_01")),FName(TEXT("head"))})
                            if(Body->GetBoneIndex(Bone)!=INDEX_NONE)
                                FrontDot=FMath::Max(FrontDot,FVector::DotProduct(Body->GetSocketLocation(Bone),Forward));
                        const double Clearance=FVector::DotProduct(View.Location,Forward)-FrontDot;
                        bClose=Clearance<(bRideEyeOccluded?22.:16.);
                    }
                }
            }
    }
    if(bRideEyeOccluded!=bClose){bRideEyeOccluded=bClose;UpdateOwnerVisibility();}
    if(Character.IsValid()&&Character->IsLocallyControlled())
    {
        // The firearm rig retains its last model when the owner switches to a bow.
        const bool bPistol=Character->HasInventoryWeapon()&&Character->IsPistolWeapon();
        const bool bWarhammer=UsesWarhammerFirstPersonPass();
        const auto ViewmodelType=bPistol||bWarhammer?EFirstPersonPrimitiveType::FirstPerson:EFirstPersonPrimitiveType::None;
        // Apply a weapon-family transition before this frame is rendered;
        // ordinary updates and newly attached parts use the existing refresh.
        if(Character->AKMViewmodel&&Character->AKMViewmodel->FirstPersonPrimitiveType!=ViewmodelType)
            UpdateOwnerVisibility();
        if((bPistol||bWarhammer)&&!UHorseRiderComponent::UsesSaddleHands(Character.Get())&&!IsThirdPersonViewEnabled()&&!UFPSFurnitureRestComponent::IsResting(Character.Get()))
        {
            // Uniform render-space scaling about the eye preserves screen size,
            // ADS and finger/gun contact while putting the viewmodel ahead of
            // the world-space torso/trousers. Gameplay sockets stay untouched.
            View.bUseFirstPersonParameters=true;
            View.FirstPersonFOV=View.FOV;
            // Warhammer uses only the first-person shadow classification;
            // preserve its authored world depth, FOV and floor contact.
            View.FirstPersonScale=bWarhammer?1.f:.25f;
        }
    }
    if (!IsThirdPersonViewEnabled())
    {
        bFixedThirdPersonCameraCaptured=false;
        return;
    }

    const bool bFixedView=IsFixedThirdPersonViewEnabled()&&!UFPSFurnitureRestComponent::IsResting(Character.Get());
    if (!bFixedView) bFixedThirdPersonCameraCaptured=false;
    View.bUseFirstPersonParameters=false;
    if (bFixedView && bFixedThirdPersonCameraCaptured)
    {
        // Only the rendered observation POV is held. Never freeze control yaw
        // or the eye component: whirlwind, dash, aim and hit queries still run.
        const FVector Eye=View.Location;
        View.Location=FixedThirdPersonLocation;
        View.Rotation=FixedThirdPersonRotation;
        View.FOV=FixedThirdPersonFOV;
        UpdateWorldOwnerVisibility(FVector::DistSquared(Eye,View.Location)<FMath::Square(60.f));
        return;
    }

    // Pull back on the existing aim axis: the reticle and eye-origin gameplay rays
    // still point at the same target. Never move the first-person component itself;
    // weapon poses, shot origins and traversal camera recovery keep their contract.
    const FVector Eye = View.Location;
    const FVector Desired = Eye - View.Rotation.Vector() * 300.f;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PlayerBodyCamera), false, GetOwner());
    if (const auto* Ride = Character->FindComponentByClass<UHorseRiderComponent>(); Ride && Ride->Transferring() && IsValid(Ride->GetMount()))
        Query.AddIgnoredActor(Ride->GetMount());
    FHitResult Hit;
    View.Location = GetWorld()->SweepSingleByChannel(Hit, Eye, Desired, FQuat::Identity,
        ECC_Camera, FCollisionShape::MakeSphere(12.f), Query)
        ? (Hit.bStartPenetrating ? Eye : Hit.Location) : Desired;

    if (bFixedView)
    {
        // Capture the collision-adjusted third-person view once, including
        // when the button was enabled directly from first person.
        FixedThirdPersonLocation=View.Location;
        FixedThirdPersonRotation=View.Rotation;
        FixedThirdPersonFOV=View.FOV;
        bFixedThirdPersonCameraCaptured=true;
    }

    // Hide only from the owning view when an obstacle pushes the camera into the
    // character. Hidden-shadow behavior and visibility to other players remain.
    UpdateWorldOwnerVisibility(FVector::DistSquared(Eye, View.Location) < FMath::Square(60.f));
}
