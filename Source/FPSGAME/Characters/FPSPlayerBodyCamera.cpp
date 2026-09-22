#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "Camera/CameraTypes.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"

void AFPSGAMECharacter::CalcCamera(float DeltaTime, FMinimalViewInfo& OutResult)
{
    Super::CalcCamera(DeltaTime, OutResult);
    if (auto* Body = FindComponentByClass<UFPSPlayerBodyComponent>()) Body->ApplyCameraView(OutResult);
}

bool UFPSPlayerBodyComponent::IsThirdPersonViewEnabled() const
{
    return Character.IsValid() && Character->IsLocallyControlled() &&
        UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(Character.Get(), EDevelopmentTuningOption::ThirdPersonView);
}

void UFPSPlayerBodyComponent::RefreshViewMode()
{
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
    for (auto Outfit : OutfitMeshes) FPSBodyEquipment::ApplyOwnerVisibilityFlags(Outfit,/*bOnlyOwnerSee=*/false,bHideFromOwner);
    // Owner visibility must not re-enable shadows on hidden or stowed equipment.
    ApplyWorldBodyShadow();
}

void UFPSPlayerBodyComponent::ApplyCameraView(FMinimalViewInfo& View)
{
    if (!IsThirdPersonViewEnabled()) return;

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

    // Hide only from the owning view when an obstacle pushes the camera into the
    // character. Hidden-shadow behavior and visibility to other players remain.
    UpdateWorldOwnerVisibility(FVector::DistSquared(Eye, View.Location) < FMath::Square(60.f));
}
