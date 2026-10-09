#pragma once
#include "CoreMinimal.h"

namespace Super90SpeedloaderAssets
{
inline constexpr const TCHAR* Id=TEXT("super90_tube_loader");
inline constexpr const TCHAR* Guide=TEXT("/Game/Weapons/Super90/Speedloader20261007/SM_Super90_LoaderGuide.SM_Super90_LoaderGuide");
inline constexpr const TCHAR* Props=TEXT("/Game/Weapons/Super90/Speedloader20261007/SK_Super90_LoaderProps.SK_Super90_LoaderProps");
inline constexpr int32 Capacity=7;
// Native 60 Hz source clock. Base gameplay rate remains 1.3x.
inline constexpr float Insert=90.f/60.f;
inline constexpr float Step=4.f/60.f;
inline constexpr float NormalReference=146.f/60.f;
inline constexpr float EmptyReference=182.f/60.f;
inline constexpr float PropsVisibleBegin=74.f/60.f;
inline float LastContact(int32 Count){return Insert+FMath::Max(0,Count-1)*Step;}
inline float PropsVisibleEnd(int32 Count){return LastContact(Count)+13.f/60.f;}
inline float Release(int32 Count){return Count>0?LastContact(Count)+44.f/60.f:1.1f*28.f/52.f;}
inline FString Animation(int32 Count,bool Empty)
{
    const FString Name=Count==0?TEXT("A_Super90_loader_cycle"):
        FString::Printf(TEXT("A_Super90_loader_%s_%d"),Empty?TEXT("empty"):TEXT("normal"),Count);
    return TEXT("/Game/Weapons/Super90/Speedloader20261007/Animations/")+Name+TEXT(".")+Name;
}
}
