#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// A762 keeps the AKM/Manny action clock, with its own geometry and marker tracks.
namespace A762WeaponAssets
{
inline constexpr const TCHAR* Definition = TEXT("ue_a762");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/A762/Integrated20260920/SK_A762_Manny.SK_A762_Manny");
inline bool Matches(const USkeletalMeshComponent* Mesh)
{
    return Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/A762/"));
}
inline FString AnimationPath(const TCHAR* Clip)
{
    return FString::Printf(TEXT("/Game/Weapons/A762/Integrated20260920/Animations/A_A762_%s.A_A762_%s"),Clip,Clip);
}
inline FString SightPath(int32 Index)
{
    return FString::Printf(TEXT("/Game/Weapons/A762/Accessories05/Meshes/SM_A762_%sSight"),Index==0?TEXT("Rear"):TEXT("Front"));
}
// Bone-local metres; FBX reflects Blender's Y and inherits the 100 cm root scale.
inline const FVector SightHinges[] = {FVector(.00056f,-.05576f,.1065f),FVector(.00056f,.49144f,.0935f)};
inline const FVector MuzzleMount(.00056f,.51736f,.05440f);
inline const FVector OpticMount(.00056f,.12f,.0995f);
}
