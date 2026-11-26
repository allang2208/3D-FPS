#pragma once
#include "CoreMinimal.h"

// Measured once from the equipped, posed weapon and its anatomical palm mount.
// Values are in the body wrist frame, never in camera or donor-skeleton axes.
struct FFPSBodyGunAimFrame
{
    FVector Forward=FVector::RightVector;
    FVector Muzzle=FVector::ZeroVector;
    bool bValid=false;
};

class USkinnedMeshComponent;
namespace FPSBodyGunAim
{
    FFPSBodyGunAimFrame FromMuzzle(const FTransform& MuzzleInMesh,const FTransform& Mount);
    bool SightFrame(const USkinnedMeshComponent& Weapon,FTransform& Frame);
    FFPSBodyGunAimFrame FromWeapon(const USkinnedMeshComponent& Weapon);
}
