#pragma once
#include "CoreMinimal.h"

// Independent catalog IDs. Mesh-local aim and outlet sockets are authored for
// every interface variant; their source UVs and optical materials stay intact.
namespace CommonHK416Parts
{
    inline constexpr const TCHAR* Optic = TEXT("eoth_holographic");
    inline constexpr const TCHAR* Suppressor = TEXT("multi_caliber_suppressor");
    inline FString OpticFamily(const FString& Definition)
    {
        if (Definition == TEXT("ue_hk416")) return TEXT("HK416");
        if (Definition == TEXT("ue_m16a2")) return TEXT("M16");
        if (Definition == TEXT("ue_m1911")) return TEXT("M1911");
        if (Definition == TEXT("ue_g18")) return TEXT("G18");
        if (Definition == TEXT("ue_dan_wesson715")) return TEXT("DW715");
        return TEXT("Common");
    }
    inline FString MeshPath(const FString& Definition, const FString& Variant)
    {
        const FString Family = Variant == Optic ? OpticFamily(Definition)
            : Definition == TEXT("ue_hk416") ? TEXT("HK416")
            : (Definition == TEXT("ue_m1911") || Definition == TEXT("ue_g18")) ? TEXT("Pistol") : TEXT("Common");
        return TEXT("/Game/Weapons/CommonHK41620260930/Meshes/SM_") + Family + TEXT("_") + Variant;
    }
    inline FString OpticInterface(const FString& Definition)
    {
        // AKM's modern optic bridge is an independent component. Its older
        // holographic assembly embeds the bridge in a different local frame.
        return Definition == TEXT("ue_akm") ? TEXT("panoramic_red_dot") : TEXT("holographic");
    }
}
