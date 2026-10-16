#pragma once
#include "CoreMinimal.h"
class AActor;
class USkeletalMeshComponent;
class UStaticMeshComponent;

namespace Super90TubeMagazineAssets
{
inline constexpr const TCHAR* Part=TEXT("super90_extended_tube");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/Super90/ExtendedTube20261015/Meshes/SM_Super90_ExtendedTube");
inline constexpr const TCHAR* ChokeMeshPath=TEXT("/Game/Weapons/Super90/ExtendedTube20261015/Meshes/SM_Super90_ChokeTubeFit");
inline constexpr const TCHAR* SuppressorMeshPath=TEXT("/Game/Weapons/Super90/ExtendedTube20261015/Meshes/SM_Super90_SuppressorTubeFit");
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,UStaticMeshComponent* Existing,bool Enabled);
}
