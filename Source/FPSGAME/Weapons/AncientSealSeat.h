#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;

namespace AncientSealSeat
{
inline constexpr const TCHAR* Part=TEXT("ancient_breaking_seal_seat");
inline constexpr float Seconds=8.f,PhysicalBonus=.15f,ToughnessBonus=.25f;
inline bool Supports(const FString& Weapon)
{return Weapon==TEXT("ue_steel_warhammer")||Weapon==TEXT("ue_runebound_warhammer");}
FPSGAME_API bool Installed(const FColdSteelItem& Item);
}
