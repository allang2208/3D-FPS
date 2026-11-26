#pragma once
#include "CoreMinimal.h"

// Equipment and muzzle swaps resolve the same bank, independently of the animation rig.
namespace RifleSuppressedAudioAssets
{
inline const TCHAR* Bank(const FString& Definition)
{
    if (Definition == TEXT("ue_m4a1")) return TEXT("M4");
    if (Definition == TEXT("ue_akm")) return TEXT("AKM");
    if (Definition == TEXT("ue_a762")) return TEXT("A762");
    if (Definition == TEXT("ue_svd")) return TEXT("SVD");
    if (Definition == TEXT("ue_svch")) return TEXT("SVCh");
    return nullptr;
}

inline FString SoundPath(const TCHAR* BankName, int32 Variant = 1)
{
    return FString::Printf(TEXT("/Game/Weapons/RifleSuppressedAudio20261015/%s/S_%s_Suppressed_%02d.S_%s_Suppressed_%02d"),
        BankName, BankName, Variant, BankName, Variant);
}
}
