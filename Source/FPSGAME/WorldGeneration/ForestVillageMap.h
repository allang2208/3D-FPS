#pragma once
#include "CoreMinimal.h"
#include "Engine/World.h"

namespace ForestVillageMap
{
inline constexpr TCHAR Name[] = TEXT("L_ForestPathVillage");
inline constexpr TCHAR Package[] = TEXT("/Game/GameMaps/L_ForestPathVillage");
// Metres, in the original forest coordinate system.
inline constexpr int32 West=-624, South=-320, SideMeters=1024;
inline FBox2D Bounds()
{
    return FBox2D(FVector2D(West,South)*100.,FVector2D(West+SideMeters,South+SideMeters)*100.);
}
inline bool Is(const UWorld* World)
{
    if (!World) return false;
    return UWorld::RemovePIEPrefix(World->GetPackage()->GetName()) == Package;
}
inline bool HasVillage(const FString& Map)
{
    return Map == Name || Map == TEXT("L_TemperateHills_Initial");
}
}
