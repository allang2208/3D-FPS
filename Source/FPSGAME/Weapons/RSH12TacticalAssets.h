#pragma once
#include "CoreMinimal.h"

namespace RSH12TacticalAssets
{
inline bool Supports(const FString& Variant)
{
    return Variant==TEXT("laser") || Variant==TEXT("flashlight");
}
inline FString MeshPath(const FString& Variant)
{
    return TEXT("/Game/Weapons/RSH12/Tactical20261005/Meshes/SM_RSH12_")+Variant;
}
inline FTransform Mount()
{
    // Forward clamp on the actual lower rail. The authored bracket puts the
    // device on the shooter's right, clear of the existing foregrip seat.
    const FVector Forward(0.f,.9980492592f,-.0624317825f);
    const FVector Up(0.f,.0624317825f,.9980492592f);
    const FVector Origin(-.0001100056f,.1150264516f,-.0183265284f);
    return FTransform(FRotationMatrix::MakeFromXZ(Forward,Up).ToQuat(),
        Origin+Forward*.1395f+Up*.0194712f,FVector(.01f));
}
}
