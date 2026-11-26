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
    Shop,
    Planting,
    Incinerate,
    ArtisanLesson,
    MountPotion,
    MountGear,
    MountRelease
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
    UPROPERTY() uint32 ConversationSession = 0;
    UPROPERTY() int64 Revision = 0;
    UPROPERTY() EColdSteelInventoryAction Action = EColdSteelInventoryAction::Consume;
    UPROPERTY() FString Item;
    UPROPERTY() TObjectPtr<AActor> Target = nullptr;
    UPROPERTY() TObjectPtr<APawn> Pawn = nullptr;
    UPROPERTY() FVector_NetQuantize Eye = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantize Origin = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Direction = FVector::ZeroVector;
    UPROPERTY() float Charge=0.f;
    // Manual perfect-release candidate only; authority checks its own draw session.
    UPROPERTY() float BowReleaseElapsed=-1.f;
    // All releases report their continuous draw clock; damage remains server-derived.
    UPROPERTY() float BowChargeElapsed=-1.f;
    UPROPERTY() FGuid BowDrawId;
    UPROPERTY() FGuid ConsumableUseId;
    UPROPERTY() FGuid MountId;
    UPROPERTY() EArrowElement ArrowElement=EArrowElement::None;
    UPROPERTY() bool bIlluminationArrow=false;
    UPROPERTY() int64 ContainerRevision=0;
    UPROPERTY() int64 Count=0;
    UPROPERTY() int32 Place=0;
    UPROPERTY() int32 Cell=-1;
    UPROPERTY() int32 Orientation=-1;
    UPROPERTY() int32 Page=0;
    UPROPERTY() FString Mode;
    // Compare-and-swap identity for placing into the personal enhancement escrow.
    UPROPERTY() FString ExpectedBenchId;
    UPROPERTY() FGuid Volume;
    UPROPERTY() FIntVector Anchor=FIntVector::ZeroValue;
    UPROPERTY() TArray<FIntVector> Cells;
    /** 2026-10-17 楔形切割（VoxelCut 编码）与 Cells 按下标平行；空=全整格（旧客户端兼容）。
     *  联机放置必须随事务带上切割，否则服务端无切割重放会把坡落成阶梯。 */
    UPROPERTY() TArray<uint8> CellShapes;
    UPROPERTY() FName Definition;
    // Planting requests carry identities and intent; no client growth/yield/transform.
    UPROPERTY() FGuid PlantingBedId;
    UPROPERTY() FGuid ExpectedPlantId;
    // Exact selected cells, bounded to one 4x4 bed. Authority derives anchors and total cost.
    UPROPERTY() TArray<int32> PlantingSlots;
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
    // Explicit outcome even when the replicated perfect flag did not change.
    UPROPERTY() bool bBowPerfect=false;
    UPROPERTY() bool bBowPiercing=false;
    UPROPERTY() FString Message;
    UPROPERTY() TArray<FColdSteelItem> Changed;
    UPROPERTY() TArray<FString> Removed;
    UPROPERTY() TMap<FString,int64> PouchDelta;
    UPROPERTY() TMap<FString,int64> WorldReceipts;
    UPROPERTY() FGuid FoodClockId;
    UPROPERTY() double FoodClockDay=0.;
    UPROPERTY() int64 ServerSoulCredits=0;
    UPROPERTY() int64 ServerSoulDebits=0;
    UPROPERTY() FStableMountRoster MountPotionRoster;
    UPROPERTY() bool bResourcesChanged = false;
    UPROPERTY() float ManaRestored = 0.f;
    UPROPERTY() float ElementManaSpent=0.f;
    UPROPERTY() EArrowElement ArrowElement=EArrowElement::None;
    UPROPERTY() bool bIlluminationArrow=false;
    UPROPERTY() float ElementCooldown=0.f;
    UPROPERTY() double ElementCooldownEnd=0.;
    UPROPERTY() float StaminaSpent = 0.f;
    UPROPERTY() bool bEquipmentChanged=false;
    UPROPERTY() int32 ActiveWeaponSlot=6;
    UPROPERTY() FString ActiveProductionTool;
    UPROPERTY() bool bWorldAction=false;
    UPROPERTY() bool bPlantingView=false;
    UPROPERTY() FColdSteelPlantingNetState Planting;
    UPROPERTY() FDungeonRunState DungeonRun;
    UPROPERTY() FColdSteelForgeJob ForgeJob;
    UPROPERTY() FColdSteelGunAssemblyJob GunAssemblyJob;
    UPROPERTY() FColdSteelWoodworkingJob WoodworkingJob;
    UPROPERTY() FColdSteelAlchemyJob AlchemyJob;
    UPROPERTY() FColdSteelItem EnhancementItem;
    UPROPERTY() bool bContainerView=false;
    UPROPERTY() FString ContainerKey;
    UPROPERTY() FString ContainerCaption;
    UPROPERTY() int32 ContainerPages=1;
    UPROPERTY() int64 ContainerRevision=0;
    UPROPERTY() TArray<FColdSteelItem> ContainerItems;
    UPROPERTY() bool bContainerSearch=false;
    UPROPERTY() TArray<FString> ContainerRevealed;
    UPROPERTY() FString ContainerSearchItem;
    UPROPERTY() float ContainerSearchElapsed=0;
    UPROPERTY() float ContainerSearchDuration=0;
};
