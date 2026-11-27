#pragma once

#include "CoreMinimal.h"
#include "LumberMillQuestTypes.generated.h"

/**
 * Authoritative progression stages for the shared "Rebuild Lumber Mill" quest line
 * in L_ForestPathVillage. Triggered automatically once the Village Carpenter Workshop is repaired.
 */
UENUM()
enum class ELumberMillQuestStage : uint8
{
    Locked = 0,        // Carpenter workshop not yet repaired; mill is ruined & occupied.
    TalkToNun = 1,     // Step 1 accepted on Carpenter repair -> Step 2 active: speak with Chapel Nun.
    ClearMonsters = 2, // Step 3 active: clear 2 Witches, 4 Infected Dogs & 1 Hand-Brain at the ruined mill.
    ReportToNun = 3,   // Step 4 active: all 7 monsters defeated -> report back to Chapel Nun.
    Completed = 4,     // Step 5 complete: Lumber Mill permanently restored & saved.
};

/** Compact replicated state owned by ATemperateHillsWorld (shared across host & all clients). */
USTRUCT()
struct FPSGAME_API FLumberMillQuestState
{
    GENERATED_BODY()

    UPROPERTY() uint8 Stage = 0;
    UPROPERTY() uint8 DefeatedMask = 0;
    UPROPERTY() bool bRepaired = false;
    UPROPERTY() uint32 Generation = 0;
    UPROPERTY() uint32 Revision = 0;

    ELumberMillQuestStage GetStage() const
    {
        return Stage <= static_cast<uint8>(ELumberMillQuestStage::Completed)
            ? static_cast<ELumberMillQuestStage>(Stage)
            : ELumberMillQuestStage::Locked;
    }

    bool operator==(const FLumberMillQuestState& Other) const
    {
        return Stage == Other.Stage
            && DefeatedMask == Other.DefeatedMask
            && bRepaired == Other.bRepaired
            && Generation == Other.Generation
            && Revision == Other.Revision;
    }
    bool operator!=(const FLumberMillQuestState& Other) const { return !(*this == Other); }
};

namespace LumberMillQuest
{
    inline const FName TaskId(TEXT("village.lumber_mill.rebuild"));

    inline constexpr int32 WitchCount = 2;
    inline constexpr int32 DogCount = 4;
    inline constexpr int32 HandBrainCount = 1;
    inline constexpr int32 TotalMonsters = WitchCount + DogCount + HandBrainCount; // 7

    // Slot bit layout in DefeatedMask: [0..1] Witches, [2..5] Infected Dogs, [6] Hand-Brain.
    inline constexpr uint8 WitchMask = 0x03;     // bits 0..1
    inline constexpr uint8 DogMask = 0x3C;       // bits 2..5
    inline constexpr uint8 HandBrainMask = 0x40; // bit 6
    inline constexpr uint8 AllDefeatedMask = WitchMask | DogMask | HandBrainMask; // 0x7F

    // World-space origin of LumberMill_Compound in L_ForestPathVillage (cm).
    inline const FVector CompoundOrigin(15400.0, 6200.0, 1100.0);

    inline int32 CountBits(uint8 Mask)
    {
        int32 Count = 0;
        while (Mask)
        {
            Count += (Mask & 1u) ? 1 : 0;
            Mask >>= 1;
        }
        return Count;
    }

    inline int32 WitchesDefeated(uint8 Mask) { return CountBits(Mask & WitchMask); }
    inline int32 DogsDefeated(uint8 Mask) { return CountBits(Mask & DogMask); }
    inline int32 HandBrainDefeated(uint8 Mask) { return CountBits(Mask & HandBrainMask); }
    inline int32 TotalDefeated(uint8 Mask) { return CountBits(Mask & AllDefeatedMask); }
    inline bool AreAllMonstersDefeated(uint8 Mask) { return (Mask & AllDefeatedMask) == AllDefeatedMask; }

    inline bool IsWitchSlot(int32 Slot) { return Slot >= 0 && Slot < WitchCount; }
    inline bool IsDogSlot(int32 Slot) { return Slot >= WitchCount && Slot < WitchCount + DogCount; }
    inline bool IsHandBrainSlot(int32 Slot) { return Slot == WitchCount + DogCount; }
}
