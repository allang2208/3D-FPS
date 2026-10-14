#pragma once
#include "CoreMinimal.h"
#include "ColdSteelInventoryTypes.h"

class UColdSteelStatusModel;

/** Transient confirmation. Never serialized into the player's profile. */
struct FColdSteelIncinerationQuote
{
    bool bValid=false, bAmmo=false;
    FString Key, Reason;
    int64 Count=0, Available=0, Generation=-1;
    FColdSteelItem Before;
};

struct FColdSteelIncinerationSelection
{
    FString Key;
    bool bAmmo=false;
    int64 Count=1;
};

/** All entries refer to one original inventory generation, never intermediate results. */
struct FColdSteelIncinerationBatch
{
    bool bValid=false;
    int64 Generation=-1;
    FString Reason;
    TArray<FColdSteelIncinerationQuote> Entries;
};

namespace ColdSteelIncineration
{
    FPSGAME_API bool Accessible(const FColdSteelItem& Item);
    FPSGAME_API bool ParseQuantity(const FString& Text,int64& Count);
    FPSGAME_API FString Location(const FColdSteelItem& Item);
    FPSGAME_API FColdSteelIncinerationQuote Quote(const FColdSteelProfile& State,const FString& Key,bool bAmmo,int64 Count);
    FPSGAME_API bool Apply(const FColdSteelProfile& State,const FColdSteelIncinerationQuote& Quote,FColdSteelProfile& Next,FString& Reason);
    FPSGAME_API FString Describe(UColdSteelStatusModel& Model,const FColdSteelIncinerationQuote& Quote);
    FPSGAME_API FColdSteelIncinerationBatch QuoteBatch(const FColdSteelProfile& State,const TArray<FColdSteelIncinerationSelection>& Selections);
    FPSGAME_API bool ApplyBatch(const FColdSteelProfile& State,const FColdSteelIncinerationBatch& Batch,FColdSteelProfile& Next,FString& Reason);
    FPSGAME_API FString DescribeBatch(UColdSteelStatusModel& Model,const FColdSteelIncinerationBatch& Batch);
}

/** A confirmation can be consumed once, including a failed save. A retry must be reviewed again. */
class FPSGAME_API FColdSteelIncinerationSession
{
public:
    const FColdSteelIncinerationQuote& Pending() const { return Draft; }
    bool Review(UColdSteelStatusModel& Model,const FString& Key,bool bAmmo,int64 Count);
    bool Confirm(UColdSteelStatusModel& Model,FString& Reason);
    void Cancel() { Draft=FColdSteelIncinerationQuote(); }
private:
    FColdSteelIncinerationQuote Draft;
    bool bCommitting=false;
};

class FPSGAME_API FColdSteelIncinerationBatchSession
{
public:
    const FColdSteelIncinerationBatch& Pending() const { return Draft; }
    bool Review(UColdSteelStatusModel& Model,const TArray<FColdSteelIncinerationSelection>& Selections);
    bool Confirm(UColdSteelStatusModel& Model,FString& Reason);
    void Cancel() { Draft=FColdSteelIncinerationBatch(); }
private:
    FColdSteelIncinerationBatch Draft;
    bool bCommitting=false;
};
