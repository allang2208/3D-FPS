#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "CampfireSharedTypes.generated.h"

USTRUCT()
struct FCampfireOrder
{
    GENERATED_BODY()
    UPROPERTY() FName Recipe;
    UPROPERTY() int64 Batch=1;
    UPROPERTY(NotReplicated) TArray<FColdSteelItem> Ingredients;
    UPROPERTY() bool bMaterialsWaived=false;
    UPROPERTY() double FreshDays=-1.;
};
USTRUCT()
struct FCampfireProduct
{
    GENERATED_BODY()
    UPROPERTY() FString Item;
    UPROPERTY() int64 Count=0;
    UPROPERTY(NotReplicated) FColdSteelItem Payload;
    UPROPERTY() double FreshDays=-1.;
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
    UPROPERTY() bool bMaterialsWaived=false;
    UPROPERTY() double FreshDays=-1.;
    // The legacy recipe/count fields remain the compact presentation contract.
    // Escrow owns the exact paid items; claiming never recreates fresh food.
    UPROPERTY(NotReplicated) int32 FoodEscrowVersion=0;
    UPROPERTY(NotReplicated) TArray<FColdSteelItem> Ingredients;
    UPROPERTY(NotReplicated) FGuid FoodClockId;
    UPROPERTY(NotReplicated) double FoodSampleDay=0.;
    UPROPERTY(NotReplicated) int64 FoodUtcTicks=0;
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
