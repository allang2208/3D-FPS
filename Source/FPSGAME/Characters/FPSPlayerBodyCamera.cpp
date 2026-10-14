#include "FPSPlayerBodyComponent.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Camera/CameraTypes.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "Engine/World.h"

void AFPSGAMECharacter::CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult)
{
    Super::CalcCamera(DeltaTime, OutResult);
    if (auto* Body = FindComponentByClass<UFPSPlayerBodyComponent>())
    {Body->ApplyCameraView(OutResult);Body->ApplyReactionCamera(DeltaTime,OutResult);}
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
    // 这条路径由 CalcCamera 每帧驱动，是「每帧重注册」的主要嫌疑位置。
    UFPSPerformanceMetricsSubsystem::CountWorldVisibilityUpdate(this);
    FFPSPerformanceScope PerformanceScope(this,TEXT("PlayerBody.WorldVisibility"));
    // fps.body.WorldBody 0 keeps these components hidden regardless of the view mode.
    // This path runs from CalcCamera on every camera update, so without the early out
    // it would put the body straight back on screen.
    if (FPSPlayerBodyWorldBodyHidden())
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
    if(Character.IsValid()&&Character->IsLocallyControlled())
    {
        const bool bPistol=Character->IsPistolWeapon();
        const auto ViewmodelType=bPistol?EFirstPersonPrimitiveType::FirstPerson:EFirstPersonPrimitiveType::None;
        // Apply a weapon-family transition before this frame is rendered;
        // ordinary updates and newly attached parts use the existing refresh.
        if(Character->AKMViewmodel&&Character->AKMViewmodel->FirstPersonPrimitiveType!=ViewmodelType)
            UpdateOwnerVisibility();
        if(bPistol&&!IsThirdPersonViewEnabled())
        {
            // Uniform render-space scaling about the eye preserves screen size,
            // ADS and finger/gun contact while putting the viewmodel ahead of
            // the world-space torso/trousers. Gameplay sockets stay untouched.
            View.bUseFirstPersonParameters=true;
            View.FirstPersonFOV=View.FOV;
            View.FirstPersonScale=.25f;
        }
    }
    if (!IsThirdPersonViewEnabled())
    {
        bFixedThirdPersonCameraCaptured=false;
        return;
    }

    const bool bFixedView=IsFixedThirdPersonViewEnabled();
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
