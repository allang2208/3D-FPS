#pragma once
#include "CoreMinimal.h"
class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace M870TubeMagazineAssets
{
inline constexpr const TCHAR* Part=TEXT("m870_tube_extension");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/M870/ExtendedTube20261017/Meshes/SM_M870_ExtendedTube");
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,bool Enabled);
}
