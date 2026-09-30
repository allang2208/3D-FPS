#pragma once
#include "DungeonTypes.h"
class AActor;

namespace DungeonLayout
{
    // Saved-profile compatibility only. Old recipe generation and encounter slots are gone.
    // Called in the same profile transaction as XP, including batched spell rewards.
    FPSGAME_API bool RecordKill(FDungeonRunState& Run, const AActor* Victim);
}
