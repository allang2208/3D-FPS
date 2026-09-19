#pragma once
#include "CoreMinimal.h"

// ASH-12 (12.7x55 mm bullpup). The viewmodel rides the shared Manny arms, so
// this header only carries the rifle's own paths and measured fit numbers.
namespace ASH12WeaponAssets
{
    inline constexpr const TCHAR* ExtendedMagazineMeshPath = TEXT("/Game/Weapons/ASH12/MagazineFinish20260919/SM_ASH12_ExtMag30_Finish.SM_ASH12_ExtMag30_Finish");
    inline constexpr const TCHAR* Definition = TEXT("ue_ash12");
    inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface.SK_ASH12_Surface");
    inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials.DA_ASH12_WetMaterials");
    inline constexpr const TCHAR* FireSoundPath = TEXT("/Game/Weapons/ASH12/Audio20260919/S_ASH12_Fire.S_ASH12_Fire");
    inline constexpr const TCHAR* TacticalSuppressorMeshPath = TEXT("/Game/Weapons/ASH12/TacticalSuppressor20260919/SM_ASH12_TacticalSuppressor.SM_ASH12_TacticalSuppressor");
    inline constexpr const TCHAR* TacticalBrakeMeshPath = TEXT("/Game/Weapons/ASH12/TacticalBrake20260920/SM_ASH12_TacticalBrake.SM_ASH12_TacticalBrake");
    inline constexpr const TCHAR* CheekRestMeshPath = TEXT("/Game/Weapons/ASH12/CheekRest20260919/SM_ASH12_CheekRest.SM_ASH12_CheekRest");
    // The attachment is authored from its rear contact plane along local +X.
    inline constexpr float TacticalSuppressorLengthCM = 26.f;
    inline constexpr float TacticalBrakeLengthCM = 8.4f;
    // The accepted rifles put the iron sight at the receiver's rear, so 12 cm of
    // eye relief lands behind the gun. This one's sight is mid-receiver on the
    // carry handle; measured stills (Saved/ASH12SightAudit) show 12 cm showing
    // the gun's rear instead of a sight picture, while 18 cm frames it like the
    // QBZ reference does at 12 cm.
    inline constexpr float ADSRearEyeDistance = 18.f;
    // Rear/front sight markers are measured on the carry-handle rail crown, so
    // the shared optic saddle needs no drop below them.
    inline constexpr float OpticRailDrop = 0.f;
    // Factory flash-hider rear rim behind WPN_SOCKET_Muzzle, in centimetres.
    inline constexpr float MuzzleBackOffset = 6.79f;
    // Measured on the export: a 12.7 mm case leaves a longer trace than 5.56.
    inline constexpr float TracerLengthCM = 4.6f;
    // Source seconds in ASH12ReloadRefine20260919/author_reload.py. The shared
    // reload clock scales pose, audio and camera together with weapon stats.
    inline constexpr float MagazineOut = .36f;
    inline constexpr float MagazineInsert = 1.56f;
    inline constexpr float MagazineSeat = 1.86f;
    inline constexpr float ChargePull = 2.34f;
    inline constexpr float ChargeRelease = 2.60f;
    inline FString OpticMeshPath(const FString& Variant)
    {
        return FString::Printf(TEXT("/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_%s.SM_ASH12_%s"), *Variant, *Variant);
    }
    inline float OpticAlongCM(const FString& Variant)
    {
        return Variant == TEXT("holographic") || Variant == TEXT("lpvo_1_6x") ? 11.f : 10.f;
    }
    inline FString GripAnimationPath(const TCHAR* Family, const TCHAR* Clip)
    {
        return FString::Printf(TEXT("/Game/Weapons/ASH12/UniversalAttachments20260919/Animations/%s/A_ASH12_%s_%s.A_ASH12_%s_%s"), Family, Family, Clip, Family, Clip);
    }
    inline FString SprintAnimationPath(const TCHAR* Kind, const TCHAR* Family = TEXT("base"))
    {
        if (FCString::Strcmp(Family, TEXT("base")) != 0)
            return GripAnimationPath(Family, *(FString(TEXT("Sprint")) + Kind));
        return FString::Printf(TEXT("/Game/Weapons/ASH12/TacticalSprint20260919/A_ASH12_TacticalSprint_%s.A_ASH12_TacticalSprint_%s"), Kind, Kind);
    }
    inline FString AnimationPath(const TCHAR* Clip)
    {
        const TCHAR* Directory = FCString::Strcmp(Clip, TEXT("reload")) == 0
            || FCString::Strcmp(Clip, TEXT("reload_empty")) == 0
            ? TEXT("ReloadReference20260919") : TEXT("Integrated20260917/Animations");
        return FString::Printf(TEXT("/Game/Weapons/ASH12/%s/A_ASH12_%s.A_ASH12_%s"), Directory, Clip, Clip);
    }
}
