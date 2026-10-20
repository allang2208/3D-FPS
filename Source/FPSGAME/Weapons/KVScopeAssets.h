#pragma once
#include "CoreMinimal.h"

// Original KV Inhibitor package optic. The real-world designation is unconfirmed.
// The original part ID is retained for installed items and shared icons.
// 1/2/4x are gameplay settings, not the source optic's real specification.
namespace KVScopeAssets
{
inline constexpr const TCHAR* Id=TEXT("kv_scope_4x");
inline constexpr float Magnifications[]={1.f,2.f,4.f};
inline int32 MagnificationIndex(float Value){return Value<1.5f?0:Value<3.f?1:2;}
inline float Magnification(float Value){return Magnifications[MagnificationIndex(Value)];}
inline float StepMagnification(float Value,float Delta)
{
    const int32 Step=FMath::IsNearlyZero(Delta)?0:Delta>0.f?1:-1;
    return Magnifications[FMath::Clamp(MagnificationIndex(Value)+Step,0,2)];
}
inline bool Supports(const FString& D)
{
    return D==TEXT("ue_m4a1")||D==TEXT("ue_akm")||D==TEXT("ue_qbz191")||D==TEXT("ue_rsh12")
        ||D==TEXT("ue_ash12")||D==TEXT("ue_m16a2")||D==TEXT("ue_a762")||D==TEXT("ue_svd")
        ||D==TEXT("ue_pkm_lowpoly")||D==TEXT("ue_lmg201")||D==TEXT("ue_hk416")
        ||D==TEXT("ue_super90")||D==TEXT("ue_m870")||D==TEXT("ue_svch")||D==TEXT("ue_saiga12k");
}
inline FString MeshPath(const FString& D)
{
    const TCHAR* Family=D==TEXT("ue_hk416")?TEXT("HK416"):D==TEXT("ue_m16a2")?TEXT("M16"):
        D==TEXT("ue_ash12")?TEXT("ASH12"):TEXT("Common");
    return FString(TEXT("/Game/Weapons/KVScope20261019/SM_KVScope_"))+Family;
}
inline FString SeatPath(const FString& D)
{
    const TCHAR* Family=D==TEXT("ue_rsh12")?TEXT("RSH12"):D==TEXT("ue_super90")?TEXT("Super90"):
        (D==TEXT("ue_m870")||D==TEXT("ue_saiga12k"))?TEXT("M870"):nullptr;
    return Family?FString(TEXT("/Game/Weapons/KVScope20261019/SM_KVScope_Seat"))+Family:FString();
}
}
