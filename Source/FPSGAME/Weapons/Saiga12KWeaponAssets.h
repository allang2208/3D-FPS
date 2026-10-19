#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// Source geometry is fitted to the current AKM V9 rig. WPN_root inherits 100x
// FBX scale, so these measured root-local mounts are expressed in metres.
namespace Saiga12KWeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_saiga12k");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/Saiga12K/Detail20261018/SK_Saiga12K_Manny.SK_Saiga12K_Manny");
inline constexpr const TCHAR* FireSoundPath=TEXT("/Game/Weapons/Saiga12K/GameDevAudio20261018/S_Saiga12K_Fire");
inline constexpr int32 PelletCount=8;
inline constexpr float MinimumAttackInterval=.12f;
inline const FVector Muzzle(.0008,.593942075,.03953);
inline const FVector Rear(.0008,.17414625,.0912);
inline const FVector Front(.0008,.39626875,.0915725);
inline bool Matches(const USkeletalMeshComponent* Mesh)
{return Mesh&&Mesh->GetSkeletalMeshAsset()&&Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/Saiga12K/"));}
inline FString AnimationPath(const TCHAR* Name)
{
    const FString Clip(Name);
    if(Clip==TEXT("reload")||Clip==TEXT("reload_empty"))
        return FString::Printf(TEXT("/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_%s"),Name);
    if(Clip.StartsWith(TEXT("equip")))return TEXT("/Game/Weapons/AKMIntegration/EquipCharge/A_AKM_equip");
    return FString::Printf(TEXT("/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_%s"),Name);
}
}
