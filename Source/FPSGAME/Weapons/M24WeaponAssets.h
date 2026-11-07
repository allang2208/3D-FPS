#pragma once
#include "CoreMinimal.h"

// Source frames at 30 Hz; the six-frame lead-in is included in reload clocks.
namespace M24WeaponAssets
{
inline constexpr const TCHAR* Definition=TEXT("ue_m24");
inline constexpr const TCHAR* FireSoundPath=TEXT("/Game/Weapons/M24/FireAudio20261104/S_M24_Fire");
inline constexpr const TCHAR* SuppressedSoundPath=TEXT("/Game/Weapons/M24/FireAudio20261104/S_M24_Suppressed_Warm");
inline constexpr const TCHAR* MeshPath=TEXT("/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.SK_M24_MotionV9");
inline constexpr const TCHAR* SupportGripProfile=TEXT("/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip");
inline constexpr const TCHAR* ExtendedMagazineProfile=TEXT("/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10");
// Saved SVD rear-sight height/lateral alignment; scope and receiver inside the hip frame.
// SourceAssets/M24Hold20261027/hip-calibration.json, centimetres in camera space.
inline const FVector HipPresentationOffset(23.219236f,1.379742f,1.296371f);
inline const FVector SightUp(0.f,-1.f,0.f);
inline TMap<FString,FString> FactoryParts()
{return {{TEXT("optic"),TEXT("m24_custom_scope_6x")},{TEXT("muzzle"),TEXT("none")},{TEXT("stock"),TEXT("m24_cheekrest")},{TEXT("magazine"),TEXT("false")},{TEXT("bipod"),TEXT("false")},{TEXT("bolt"),TEXT("false")},{TEXT("reargrip"),TEXT("false")},{TEXT("body"),TEXT("false")}};}
inline constexpr float FireDuration=55.f/30.f;
inline constexpr float BoltLift=20.f/30.f;
inline constexpr float BoltPull=25.f/30.f;
inline constexpr float BoltEject=30.f/30.f;
inline constexpr float BoltPush=35.f/30.f;
inline constexpr float BoltClosed=40.f/30.f;
inline constexpr float MagazineOut=21.f/30.f;
inline constexpr float MagazineInsert=38.f/30.f;
inline constexpr float MagazineSeat=40.f/30.f;
inline constexpr float ChargeStart=54.f/30.f;
inline constexpr float ChargeLift=72.f/30.f;
inline constexpr float ChargePull=77.f/30.f;
inline constexpr float ChargeEject=82.f/30.f;
inline constexpr float ChargePush=87.f/30.f;
inline constexpr float ChargeRelease=94.f/30.f;
// EquipBoltOnly20261028: native bolt cycle at the calibrated hip anchor.
inline constexpr float EquipBoltPull=25.f/30.f;
inline constexpr float EquipBoltEject=BoltEject+3.f/30.f;
// The handle starts turning down at frame 40 and is mechanically locked at 42.
inline constexpr float EquipBoltClosed=42.f/30.f;
inline constexpr const TCHAR* ReadyEquipPath=TEXT("/Game/Weapons/M24/EquipConditional20261104/A_M24_equip_ready");
inline FString AnimationPath(const TCHAR* Role)
{
    const bool SharedHold=FCString::Strcmp(Role,TEXT("idle"))==0||FCString::Strcmp(Role,TEXT("aim"))==0;
    return FString::Printf(TEXT("/Game/Weapons/M24/%s/Animations/A_M24_%s.A_M24_%s"),SharedHold?TEXT("Hold20261027"):TEXT("MotionMagazine20261027"),Role,Role);
}
}
