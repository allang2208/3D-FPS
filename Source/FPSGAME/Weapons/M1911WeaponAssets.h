#pragma once
#include "CoreMinimal.h"
#include "TacticalSuppressorAssets.h"

namespace M1911WeaponAssets
{
    // 12 current clips, 904 poses at 60 Hz, all skinned vertices; 10% margin.
    // Imported reference bounds are behind the animated pistol (audit 2026-09-13).
    inline constexpr float ViewmodelBoundsScale = 4.17f;
    // Body geometry is resized in the authoring pipeline; mounting feet and bore
    // retain their pistol interfaces. Aim points follow the optical geometry.
    inline constexpr float HolographicBodyScale = .55f;
    inline constexpr float PanoramicBodyScale = .62f;
    inline constexpr float SuppressorTipCM = 13.02f;
    inline constexpr float BrakeTipCM = 3.4f;
    inline constexpr const TCHAR* ActionRoot = TEXT("/Game/Weapons/M1911/Contact20260913");
    inline constexpr const TCHAR* ReloadRoot = TEXT("/Game/Weapons/M1911/ReloadReady20260913");
    inline FString AnimationPath(const TCHAR* Clip)
    {
        const bool Reload = FCString::Strcmp(Clip, TEXT("reload")) == 0 || FCString::Strcmp(Clip, TEXT("reload_empty")) == 0;
        return FString::Printf(TEXT("%s/Animations/A_M1911_%s.A_M1911_%s"), Reload ? ReloadRoot : ActionRoot, Clip, Clip);
    }
    inline FString AttachmentPath(const FString& Part)
    {
        if (Part == TEXT("tactical_suppressor")) return TacticalSuppressorAssets::MeshPath(TEXT("M1911"));
        if (Part == TEXT("panoramic_red_dot"))
            return TEXT("/Game/Weapons/M1911/SculptedMount20260913/Meshes/SM_M1911_") + Part;
        if (Part == TEXT("brake"))
            return TEXT("/Game/Weapons/M1911/MuzzleRedDot20260913/Meshes/SM_M1911_") + Part;
        return TEXT("/Game/Weapons/M1911/CompactFit20260913/Meshes/SM_M1911_") + Part;
    }
}
