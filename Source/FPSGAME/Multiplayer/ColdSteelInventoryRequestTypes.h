#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ColdSteelInventoryRequestTypes.generated.h"

class AActor;
class APawn;

UENUM()
enum class EColdSteelInventoryAction : uint8
{
    Consume,
    Fountain,
    Drop,
    Pickup,
    PickupNearby,
    BowShot,
    RecoverArrow,
    ContainerOpen,
    ContainerMove,
    ContainerSplit,
    ContainerBatch,
    ContainerSort,
    ContainerStoreMatching,
    ContainerRetrieveAll,
    Shrine,
    Harvest,
    SoilRefill,
    Building,
    Workstation,
    Shop
};

USTRUCT()
struct FColdSteelInventoryTradeLine
{
    GENERATED_BODY()
    UPROPERTY() FString Key;
    UPROPERTY() int64 Value=0;
};

USTRUCT()
struct FColdSteelInventoryRequest
{
    GENERATED_BODY()
    UPROPERTY() uint32 Sequence = 0;
    UPROPERTY() int64 Revision = 0;
    UPROPERTY() EColdSteelInventoryAction Action = EColdSteelInventoryAction::Consume;
    UPROPERTY() FString Item;
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() TObjectPtr<APawn> Pawn = nullptr;
    UPROPERTY() FVector_NetQuantize Eye;
    UPROPERTY() FVector_NetQuantize Origin;
    UPROPERTY() FVector_NetQuantizeNormal Direction;
    UPROPERTY() float Charge=0.f;
    // Manual perfect-release candidate only; authority checks its own draw session.
    UPROPERTY() float BowReleaseElapsed=-1.f;
    UPROPERTY() int64 ContainerRevision=0;
    UPROPERTY() int64 Count=0;
    UPROPERTY() int32 Place=0;
    UPROPERTY() int32 Cell=-1;
    UPROPERTY() int32 Orientation=-1;
    UPROPERTY() int32 Page=0;
    UPROPERTY() FString Mode;
    UPROPERTY() FGuid Volume;
    UPROPERTY() FIntVector Anchor=FIntVector::ZeroValue;
    UPROPERTY() TArray<FIntVector> Cells;
    UPROPERTY() FName Definition;
    UPROPERTY() TArray<FColdSteelInventoryTradeLine> TradeItems;
};

// Only changed inventory entries cross the wire. Normal SaveGame files and the
// periodic profile mirror keep their existing complete-profile representation.
UCLASS()
class UColdSteelInventoryReply : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() uint32 Sequence = 0;
    UPROPERTY() int64 Revision = 0;
    UPROPERTY() bool bSuccess = false;
    UPROPERTY() FString Message;
    UPROPERTY() TArray<FColdSteelItem> Changed;
    UPROPERTY() TArray<FString> Removed;
    UPROPERTY() TMap<FString,int64> PouchDelta;
    UPROPERTY() TMap<FString,int64> WorldReceipts;
    UPROPERTY() int64 ServerSoulCredits=0;
    UPROPERTY() int64 ServerSoulDebits=0;
    UPROPERTY() bool bResourcesChanged = false;
    UPROPERTY() float ManaRestored = 0.f;
    UPROPERTY() float StaminaSpent = 0.f;
    UPROPERTY() bool bEquipmentChanged=false;
    UPROPERTY() int32 ActiveWeaponSlot=6;
    UPROPERTY() FString ActiveProductionTool;
    UPROPERTY() bool bWorldAction=false;
    UPROPERTY() FDungeonRunState DungeonRun;
    UPROPERTY() FColdSteelForgeJob ForgeJob;
    UPROPERTY() FColdSteelGunAssemblyJob GunAssemblyJob;
    UPROPERTY() FColdSteelWoodworkingJob WoodworkingJob;
    UPROPERTY() bool bContainerView=false;
    UPROPERTY() FString ContainerKey;
    UPROPERTY() FString ContainerCaption;
    UPROPERTY() int32 ContainerPages=1;
    UPROPERTY() int64 ContainerRevision=0;
    UPROPERTY() TArray<FColdSteelItem> ContainerItems;
};
