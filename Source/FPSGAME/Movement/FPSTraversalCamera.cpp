#include "FPSTraversalComponent.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"

FVector UFPSTraversalComponent::SweepCamera(FVector From,FVector To) const
{
    const auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    const auto* Capsule=C->GetCapsuleComponent();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(TraversalCamera),false,C);
    FHitResult Hit;
    if (GetWorld()->SweepSingleByProfile(Hit,From,To,FQuat::Identity,Capsule->GetCollisionProfileName(),
        FCollisionShape::MakeSphere(5.f),Query))
        return Hit.bStartPenetrating?From:Hit.Location;
    return To;
}

void UFPSTraversalComponent::UpdateCameraReturn(float DeltaSeconds)
{
    auto* C=CastChecked<AFPSGAMECharacter>(GetOwner());
    const FVector Target=C->FirstPersonCamera->GetComponentLocation();
    const FQuat TargetRotation=C->FirstPersonCamera->GetComponentQuat();
    const FVector Capsule=C->GetActorLocation();
    // Carry actual walking/falling displacement. Bound only the recovery offset,
    // otherwise a falling body can outrun the camera and prevent convergence.
    const FVector Carried=LastCamera+Capsule-CameraReturnCapsule;
    const float Dt=FMath::Max(0.f,DeltaSeconds);
    CameraReturnSpeed=FMath::Min(450.f,CameraReturnSpeed+1800.f*Dt);
    const FVector Next=Carried+(Target-Carried).GetClampedToMaxSize(CameraReturnSpeed*Dt);
    LastCamera=SweepCamera(LastCamera,Next);
    LastCameraRotation=FMath::QInterpConstantTo(LastCameraRotation,TargetRotation,Dt,2.f*PI);
    CameraReturnCapsule=Capsule;
    C->FirstPersonCamera->SetWorldLocationAndRotation(LastCamera,LastCameraRotation);
    if (LastCamera.Equals(Target,.1f) && LastCameraRotation.AngularDistance(TargetRotation)<.001f)
        bReturningCamera=false;
}
