#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// SVD-specific actions and contacts. Shared Manny mesh/rest/skin remain unchanged.
// Markers are baked from the actual SVD into every action (metres in WPN_root).
namespace SVDWeaponAssets
{
    inline constexpr const TCHAR* Definition=TEXT("ue_svd");
    inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock.SK_SVD_ModularStock");
    inline constexpr const TCHAR* ItemAmmoId=TEXT("ammo_pkm_762x54r");
    inline constexpr float ADSRearEyeDistance=7.f;
    inline constexpr float Magnification=4.f;
    inline constexpr bool bSingleShotTrigger=true;
    inline constexpr int32 FireVariantCount=1;
    inline constexpr float MagazineOut=52.f/120.f;
    inline constexpr float MagazineInsert=220.f/120.f;
    inline constexpr float MagazineSeat=240.f/120.f;
    inline constexpr float ChargeStart=268.f/120.f;
    inline constexpr float ChargePull=310.f/120.f;
    inline constexpr float ChargeRelease=350.f/120.f;
    inline constexpr float EquipPull=64.f/120.f;
    inline constexpr float EquipRelease=100.f/120.f;
    inline bool Matches(const USkeletalMeshComponent* Mesh)
    {
        return Mesh&&Mesh->GetSkeletalMeshAsset()&&Mesh->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/SVDDragunov20260922/"));
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        return FString::Printf(TEXT("/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_%s.A_SVD_%s"),Clip,Clip);
    }
    inline FString FireSoundPath(int32 Variant)
    {
        return FString::Printf(TEXT("/Game/Weapons/SVDDragunov20260922/VideoAudio20260923/S_SVD_Fire_%02d"),Variant);
    }
    inline FString MechanicalSoundPath(const TCHAR* Cue)
    {
        return FString::Printf(TEXT("/Game/Weapons/SVDDragunov20260922/VideoAudio20260923/S_SVD_%s"),Cue);
    }
}
