#pragma once
#include "CoreMinimal.h"

class USkeletalMeshComponent;
namespace M870TacticalAssets
{
inline FString MeshPath(const FString& Kind)
{
    if(Kind==TEXT("laser"))return TEXT("/Game/Weapons/M870/TacticalFit20261017/SM_laser");
    if(Kind==TEXT("flashlight"))return TEXT("/Game/Weapons/M870/TacticalFit20261017/SM_flashlight");
    if(Kind==TEXT("blessed_laser"))return TEXT("/Game/Weapons/M870/TacticalFit20261017/SM_blessed_laser");
    return FString();
}
FTransform Mount(const USkeletalMeshComponent* Host);
}
