#pragma once
#include "CoreMinimal.h"

class APawn;
struct FColdSteelItem;
namespace ThunderHammerCall
{
    inline constexpr const TCHAR* Seat=TEXT("ji_lei_seat");
    inline constexpr float RangeCM=2000.f,RadiusCM=300.f,StaminaPerSecond=8.f,ManaPerSecond=6.f;
    inline constexpr float ReleaseSeconds=.72f,VisualScale=1.65f;
    inline constexpr const TCHAR* Charge=TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/A_ThunderHammer_CallCharge.A_ThunderHammer_CallCharge");
    inline constexpr const TCHAR* Release=TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/A_ThunderHammer_CallRelease.A_ThunderHammer_CallRelease");
    inline constexpr const TCHAR* ChargeSound=TEXT("/Game/Weapons/ThunderGodHammer20261028/JiLeiRecordedCurrentV2/MS_JiLei_CurrentRandom.MS_JiLei_CurrentRandom");
    bool Installed(const FColdSteelItem& Item);
    bool SelectGround(const APawn* Pawn,FHitResult& Hit);
}
