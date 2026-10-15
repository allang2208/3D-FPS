#pragma once
#include "CoreMinimal.h"
#include "../Weapons/RuneSwordGuardTuning.h"

namespace WarhammerGuard
{
    inline constexpr float EnterSeconds=.22f,HoldSeconds=1.6f,HitSeconds=.30f,ExitSeconds=.25f;
    inline constexpr float BreakSeconds=RuneSwordGuardTuning::BreakStunSeconds;
    inline constexpr const TCHAR* Clips[]={TEXT("GuardEnter"),TEXT("GuardHold"),TEXT("GuardHit"),TEXT("GuardBreak"),TEXT("GuardExit")};
    inline FString ClipPath(const TCHAR* Clip)
    {
        const FString Name=FString(TEXT("A_Warhammer_"))+Clip;
        return FString(TEXT("/Game/Weapons/SteelWarhammer20261014/GuardV1/"))+Name+TEXT(".")+Name;
    }
    inline constexpr const TCHAR* Sounds[]={
        TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_01.S_MeleeBlock_01"),
        TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02"),
        TEXT("/Game/Weapons/AzureRunesword20260913/S_RuneSword_Parry.S_RuneSword_Parry")};
}
