#pragma once
#include "CoreMinimal.h"

// PSO-1 is an opt-in side-mounted accessory. SVD retains its factory assembly.
namespace PSO1AttachmentAssets
{
inline constexpr const TCHAR* Variant = TEXT("pso1_4x");
inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/PSO1Russian20260923/DA_PSO1_WetMaterials");
inline bool Supports(const FString& Definition)
{
    return Definition==TEXT("ue_akm") || Definition==TEXT("ue_a762") || Definition==TEXT("ue_pkm_lowpoly");
}
inline FString MeshPath(const FString& Definition)
{
    if(!Supports(Definition))return FString();
    const TCHAR* Family=Definition==TEXT("ue_akm")?TEXT("AKM"):Definition==TEXT("ue_a762")?TEXT("A762"):TEXT("PKM");
    return FString::Printf(TEXT("/Game/Weapons/PSO1Russian20260923/%s/SM_PSO1_%s"),Family,Family);
}
// Each fitted asset is authored in gun-root space, rotated into an X-forward
// optical frame. Yaw restores that frame; the shared Manny root uses metres.
inline FTransform Mount()
{
    return FTransform(FQuat(FVector::UpVector,PI*.5f),FVector::ZeroVector,FVector(.01f));
}
}
