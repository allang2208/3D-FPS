#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"

FVector UPistolDualWieldComponent::SightDirection() const
{
    // Pose, projectile cone and tactical laser share the visible reticle centre.
    // Sampling the unshaken control rotation here displaced dual shots/lasers
    // from the HUD when the rendered first-person camera moved.
    return Player->ComputeWeaponAimDirection();
}

void UPistolDualWieldComponent::UpdateAimTarget(float Delta)
{
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();
    const FVector Direction=SightDirection();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DualPistolConvergence),true,Player);
    FHitResult Hit;
    const bool HasTarget=GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+Direction*100000.f,ECC_Visibility,Query);
    // Close surfaces are handled by the shared lower/retract pose. Do not make
    // the arms cross to chase a target inches from the camera.
    const float Distance=HasTarget?FMath::Clamp(Hit.Distance,300.f,10000.f):1200.f;
    const float TargetInverse=1.f/Distance;
    if(Delta<=0.f)AimInverseDistance=TargetInverse;
    else AimInverseDistance=FMath::Lerp(AimInverseDistance,TargetInverse,1.f-FMath::Exp(-12.f*Delta));
    AimTargetWorld=Eye+Direction/AimInverseDistance;
}
