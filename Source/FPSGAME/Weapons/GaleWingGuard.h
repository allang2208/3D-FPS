#pragma once
#include "CoreMinimal.h"
#include "GunsmithSystem.h"
#include "../UI/ColdSteelInventoryTypes.h"

namespace GaleWing
{
    inline constexpr float Duration = 3.f;
    inline constexpr float MoveMultiplier = 1.25f;
    enum class EAttack : uint8 { Swing, Dash, Heavy, Sweep, Quick, Uppercut, Whirlwind, Chain };

    inline uint64 Key(EAttack Attack, uint32 Serial)
    {
        return Serial ? (uint64(uint8(Attack) + 1) << 32) | Serial : 0;
    }

    inline bool Installed(const UGunsmithSystem* Gunsmith, const FColdSteelItem* Item)
    {
        return Item && Item->Definition == TEXT("ue_highland_claymore") && Gunsmith
            && Gunsmith->Installed(*Item).FindRef(TEXT("guard")) == TEXT("highland_gale_wing");
    }
}
