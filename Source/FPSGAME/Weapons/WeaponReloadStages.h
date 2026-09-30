#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;

/** Source-animation seconds; gameplay speed and drum remapping are applied by the owner. */
struct FWeaponReloadStages
{
    float Insert = 0.f;
    float CycleBegin = 0.f;
    float Ready = 0.f;
};

namespace WeaponReloadStages
{
    FWeaponReloadStages ForWeapon(const FString& Definition, bool Empty, bool Drum,
        bool SingleRound = false, int32 RoundCount = 0);
    bool NeedsCycle(const FColdSteelItem& Item);
    bool UsesEmptyCycle(const FColdSteelItem& Item);
    // Kept in the instance's existing serialized Data, alongside revolver cases.
    // 0 ready, 1 empty/cylinder tail, 2 nonempty feed-cover closure.
    bool SetNeedsCycle(FColdSteelItem& Item, int32 Pending);
}
