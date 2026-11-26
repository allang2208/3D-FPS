#include "PistolDualWieldComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "../FPSGAMECharacter.h"
#include "FPSGunplayAnimInstance.h"
#include "ScopeADSEyeRelief.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/World.h"

FVector UPistolDualWieldComponent::SightDirection() const
{
    return Player->ComputeWeaponAimDirection();
}

UStaticMeshComponent* UPistolDualWieldComponent::LonePhysicalOptic() const
{
    return Cast<UStaticMeshComponent>(LeftOptic.Get());
}

void UPistolDualWieldComponent::UpdateAimTarget(float Delta)
{
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();
    // Convergence follows the reticle, not last frame's moving sight. Feeding
    // the animated sight back into this target makes the ADS transition drift.
    const FVector Direction=Player->FirstPersonCamera->GetForwardVector();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DualPistolConvergence),true,Player);
    FHitResult Hit;
    const bool HasTarget=RangedAttackQuery::LineTraceSingle(GetWorld(), GetOwner(), Hit,Eye,Eye+Direction*100000.f,ECC_Visibility,Query);
    const float Distance=HasTarget?FMath::Clamp(Hit.Distance,300.f,10000.f):1200.f;
    const float TargetInverse=1.f/Distance;
    if(Delta<=0.f)AimInverseDistance=TargetInverse;
    else AimInverseDistance=FMath::Lerp(AimInverseDistance,TargetInverse,1.f-FMath::Exp(-12.f*Delta));
    AimTargetWorld=Eye+Direction/AimInverseDistance;
}

void UPistolDualWieldComponent::ConfigureLoneSight()
{
    bLoneSightCalibrated=false;
    if(!Player || !Player->IsLoneLeftHandRig() || !Hands.IsValidIndex(1))return;
    const auto& H=Hands[1];
    if(!H.Mesh || !H.Anim)return;
    H.Anim->LonePistolSightBone=NAME_None;
    H.Anim->LonePistolOpticMount=FTransform::Identity;
    if(auto* Optic=LeftOptic.Get())
    {
        FTransform Mount=FTransform::Identity;
        for(auto* Part=Optic;Part && Part!=H.Mesh;Part=Part->GetAttachParent())
        {
            auto* Parent=Part->GetAttachParent();
            Mount=Mount*Part->GetRelativeTransform();
            const FName Socket=Part->GetAttachSocketName();
            if(Parent==H.Mesh)
            {
                if(H.Mesh->GetBoneIndex(Socket)==INDEX_NONE)return;
                H.Anim->LonePistolSightBone=Socket;
                break;
            }
            if(Parent && !Socket.IsNone())Mount=Mount*Parent->GetSocketTransform(Socket,RTS_Component);
        }
        if(H.Anim->LonePistolSightBone.IsNone())return;
        H.Anim->LonePistolOpticMount=Mount;
        H.Anim->LonePistolSightRear=LeftOpticRear;
        H.Anim->LonePistolSightFront=LeftOpticFront;
        H.Anim->LonePistolSightUp=LeftOpticUp;
    }
    else if(H.Mesh->GetBoneIndex(TEXT("WPN_RearSight"))==INDEX_NONE
        || H.Mesh->GetBoneIndex(TEXT("WPN_FrontSight"))==INDEX_NONE)return;
    H.Anim->LonePistolEyeDistance=Player->UsesPhysicalScope()
        ?ScopeADSEyeRelief::DistanceCM:Player->ADSRearEyeDistance;
    bLoneSightCalibrated=true;
}

FVector UPistolDualWieldComponent::LoneAimDirection() const
{
    const FVector Forward=Player->FirstPersonCamera->GetForwardVector();
    if(!bLoneSightCalibrated || !Hands[1].Mesh)return Forward;
    // Magnified overlays are camera-centred, as in the right-hand single rig.
    if(Player->UsesPhysicalScope())return Forward;
    const auto* Optic=LeftOptic.Get();
    const FVector Point=Optic?Optic->GetComponentTransform().TransformPosition(LeftOpticFront)
        :Hands[1].Mesh->GetSocketLocation(TEXT("WPN_FrontSight"));
    const FVector Direction=(Point-Player->FirstPersonCamera->GetComponentLocation()).GetSafeNormal();
    return Direction.IsNearlyZero()?Forward:Direction;
}
