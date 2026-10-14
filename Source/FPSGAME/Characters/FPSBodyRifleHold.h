#pragma once
#include "CoreMinimal.h"

// Centimetres in the BODY right wrist frame, after the anatomical palm mount.
// Built once per equipment/grip change; the animation proxy copies only values.
struct FFPSBodyRifleHold
{
    FQuat BarrelInHand=FQuat::Identity;
    FVector StockInHand=FVector::ZeroVector;
    bool bValid=false;
};

FFPSBodyRifleHold BuildFPSBodyRifleHold(class USkeletalMeshComponent& Weapon,const struct FFPSBodyWeapon& Definition);
