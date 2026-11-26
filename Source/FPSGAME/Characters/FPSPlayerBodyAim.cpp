#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Combat/RangedAttackQuery.h"
#include "Camera/CameraComponent.h"

void UFPSPlayerBodyComponent::CaptureGunAimPresentation()
{
    DisplayState.bHasGunAimTarget=false;
    if(!Character.IsValid()||!Character->FirstPersonCamera||DisplayState.Action==EFPSBodyAction::Dead||
        (DisplayState.Family!=TEXT("Rifle")&&DisplayState.Family!=TEXT("Pistol")&&!DisplayState.bOffhandPistol))return;
    const FVector Eye=Character->FirstPersonCamera->GetComponentLocation();
    const FVector Direction=FRotator(DisplayState.AimPitch,Character->GetActorRotation().Yaw+DisplayState.AimYaw,0).Vector();
    const FVector End=Eye+Direction*100000.f;
    FHitResult Hit;
    const bool Blocked=RangedAttackQuery::LineTraceSingle(GetWorld(),Character.Get(),Hit,Eye,End,ECC_Visibility,
        FCollisionQueryParams(SCENE_QUERY_STAT(BodyGunAim),true,Character.Get()));
    DisplayState.GunAimTarget=Blocked?Hit.ImpactPoint:End;
    DisplayState.bHasGunAimTarget=true;
}

void UFPSPlayerBodyComponent::SanitizeGunAimPresentation(FFPSBodyState& State) const
{
    // Cosmetic only: accepted weapon identity and the 0.6 s pose lease are
    // enforced by SampleRemoteAuthorityState. Never use this point for damage.
    State.bHasGunAimTarget&=!State.GunAimTarget.ContainsNaN()&&
        FVector::DistSquared(State.GunAimTarget,GetOwner()->GetActorLocation())<=FMath::Square(100500.f);
    if(!State.bHasGunAimTarget)State.GunAimTarget=FVector::ZeroVector;
}
