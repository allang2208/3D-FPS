#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "CampfireSharedTypes.generated.h"

USTRUCT()
struct FCampfireOrder
{
    GENERATED_BODY()
    UPROPERTY() FName Recipe;
    UPROPERTY() int64 Batch=1;
};
USTRUCT()
struct FCampfireProduct
{
    GENERATED_BODY()
    UPROPERTY() FString Item;
    UPROPERTY() int64 Count=0;
};
/** Small public snapshot, independent of the non-replicated building world. */
USTRUCT()
struct FCampfireSharedState
{
    GENERATED_BODY()
    UPROPERTY() double Fuel=0;
    UPROPERTY() double Progress=0;
    UPROPERTY() FName Recipe;
    UPROPERTY() int64 Batch=1;
    UPROPERTY() int64 Produced=0;
    UPROPERTY() TArray<FCampfireOrder> Queue;
    UPROPERTY() TArray<FCampfireProduct> Products;
    UPROPERTY() int64 FireTicks=0;
    UPROPERTY() int64 BurnTicks=0;
    UPROPERTY() bool bSaveBlocked=false;
    UPROPERTY() double ServerTime=0;
    UPROPERTY() int32 Revision=0;
};
/** One write-ahead record per building world. Never contains a client-supplied profile. */
UCLASS()
class UColdSteelCampfireJournal : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FString WorldKey;
    UPROPERTY() FIntVector Cell=FIntVector::ZeroValue;
    UPROPERTY() FGuid InstanceId;
    UPROPERTY() FString PlayerSlot;
    UPROPERTY() bool bGuest=false;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() FCampfireSharedState After;
};
