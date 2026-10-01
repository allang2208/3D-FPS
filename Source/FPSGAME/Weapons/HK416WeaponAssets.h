#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace HK416WeaponAssets
{
inline constexpr const TCHAR* Definition = TEXT("ue_hk416");
inline constexpr const TCHAR* StockPart = TEXT("hk416_stock");
inline constexpr const TCHAR* RearGripPart = TEXT("hk416_reargrip");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny.SK_HK416_Manny");
inline constexpr const TCHAR* WetMaterialsPath = TEXT("/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials");
inline bool Matches(const USkeletalMeshComponent* Component)
{
    return Component && Component->GetSkeletalMeshAsset()
        && Component->GetSkeletalMeshAsset()->GetPathName().StartsWith(TEXT("/Game/Weapons/HK416/Reworked20260930/"));
}
inline FString AnimationPath(const TCHAR* Clip, const TCHAR* Family = TEXT("base"))
{
    return FString::Printf(TEXT("/Game/Weapons/HK416/Reworked20260930/Animations/%s/A_HK416_%s_%s.A_HK416_%s_%s"), Family, Family, Clip, Family, Clip);
}
inline FString AttachmentPath(const FString& Part)
{
    if (Part == StockPart)
        return TEXT("/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_factory_stock.SM_HK416_factory_stock");
    if (Part == RearGripPart)
        return TEXT("/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_factory_grip.SM_HK416_factory_grip");
    if (Part == TEXT("tactical_vertical") || Part == TEXT("canted") || Part == TEXT("prism") || Part == TEXT("angled")
        || Part == TEXT("panoramic_red_dot") || Part == TEXT("prism_scope_2x") || Part == TEXT("lpvo_1_6x") || Part == TEXT("lpvo_ring")
        || Part == TEXT("tactical_suppressor") || Part == TEXT("brake") || Part == TEXT("large_drum") || Part == TEXT("ext_mag")
        || Part == TEXT("skeleton") || Part == TEXT("qr_performance") || Part == TEXT("core_stock") || Part == TEXT("tactical_telescopic")
        || Part.EndsWith(TEXT("reargrip")))
        return FString::Printf(TEXT("/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_%s"), *Part);
    return FString::Printf(TEXT("/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_%s.SM_HK416_%s"), *Part, *Part);
}
}
