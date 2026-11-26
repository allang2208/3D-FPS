#pragma once

#include "CoreMinimal.h"
#include "DungeonSharedProgress.generated.h"

/** One server-owned objective state for everyone in the same dungeon run. */
USTRUCT()
struct FPSGAME_API FDungeonSharedProgress
{
    GENERATED_BODY()
    UPROPERTY() FString RunId;
    UPROPERTY() uint32 Revision = 0;
    UPROPERTY() bool bWelcomeEliteDefeated = false;
    UPROPERTY() bool bMedicalBossDefeated = false;
    UPROPERTY() bool bFreightBossDefeated = false;
    UPROPERTY() bool bEcologyBossDefeated = false;
    UPROPERTY() bool bPowerBossDefeated = false;
    UPROPERTY() bool bIncinerationBossDefeated = false;
    UPROPERTY() bool bStaffLivingBossDefeated = false;
    UPROPERTY() bool bFinalBossDefeated = false;
    UPROPERTY() bool bFinalTreasureLooted = false;
    UPROPERTY() bool bCompleted = false;
    UPROPERTY() TArray<FName> Cleared;
    UPROPERTY() TArray<FName> Explored;

    /** Also used when replication precedes local layout readiness. No saves or rewards. */
    bool ApplyNewer(const FDungeonSharedProgress& Incoming, const FString& BoundRunId)
    {
        if (BoundRunId.IsEmpty() || Incoming.RunId != BoundRunId || Incoming.Revision == 0
            || (RunId == BoundRunId && Incoming.Revision <= Revision)) return false;
        *this = Incoming;
        return true;
    }
};
