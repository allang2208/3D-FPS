#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GameFramework/SaveGame.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ColdSteelSharedInventorySubsystem.generated.h"

class AColdSteelPickup;
class AColdSteelPlayerState;
class UColdSteelStatusModel;
struct FColdSteelInventoryRequest;
class UColdSteelInventoryReply;

USTRUCT()
struct FColdSteelHarvestRemoval
{
    GENERATED_BODY()
    UPROPERTY() FString Id;
    UPROPERTY() FSoftObjectPath Mesh;
    UPROPERTY() FVector Location=FVector::ZeroVector;
    UPROPERTY() int32 Layer=0;
};
USTRUCT()
struct FColdSteelSharedContainer
{
    GENERATED_BODY()
    UPROPERTY() TArray<FColdSteelItem> Items;
    UPROPERTY() int32 Pages=1;
    UPROPERTY() int64 Revision=0;
    UPROPERTY() bool bSeeded=false;
    // Separate from the legacy empty-cabinet marker; never reset when looted empty.
    UPROPERTY() bool bSceneLootResolved=false;
    bool CanMutate(int64 ExpectedRevision,bool RequiresSceneLoot) const
    {return bSeeded&&(!RequiresSceneLoot||bSceneLootResolved)&&Revision<MAX_int64&&ExpectedRevision==Revision;}
};

USTRUCT()
struct FColdSteelSharedInventoryData
{
    GENERATED_BODY()
    UPROPERTY() TArray<FColdSteelItem> Drops;
    UPROPERTY() TMap<FString,FColdSteelSharedContainer> Containers;
    UPROPERTY() TArray<FColdSteelHarvestRemoval> HarvestRemovals;
    UPROPERTY() bool bHarvestSeeded=false;
    UPROPERTY() FColdSteelProfile Harvest;
    UPROPERTY() TArray<uint8> Building;
    UPROPERTY() bool bBuildingPending=false;
};

UCLASS()
class UColdSteelSharedInventorySave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=1;
    UPROPERTY() FColdSteelSharedInventoryData Data;
};

UCLASS()
class UColdSteelSharedInventoryJournal : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FString PlayerSlot;
    UPROPERTY() bool bGuest=false;
    UPROPERTY() int64 InventoryRevision=0;
    UPROPERTY() FColdSteelSharedInventoryData After;
};

/** Server-owned shared loot, with the same durable player-receipt journal as campfires. */
UCLASS()
class UColdSteelSharedInventorySubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void OnWorldBeginPlay(UWorld& World) override;
    virtual void Deinitialize() override;
    bool InitializeAuthority();
    bool FlushForTravel();
    bool ImportPlayerDrops(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest);
    bool Drop(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,const FString& Item,FString& Reason);
    bool Pickup(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,AColdSteelPickup* Actor,bool Nearby,FString& Reason);
    bool PickupNearby(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,FString& Reason);
    bool ContainerOperation(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& Request,FString& Reason);
    void FillContainerReply(AActor* Target,UColdSteelInventoryReply* Reply,const class APawn* Viewer) const;
    bool Commit(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,FColdSteelProfile Profile,
        FColdSteelSharedInventoryData After,FString& Reason);
    static UColdSteelStatusModel* HarvestModel(const UObject* Context);
    static void CopyHarvest(const FColdSteelProfile& From,FColdSteelProfile& To);
    void ApplyHarvestMirror(const FColdSteelProfile& State,const TArray<FColdSteelHarvestRemoval>& Removals);
    void AdvanceHarvest(float Delta);
    bool RestoreBuilding(class AVoxelBuildWorld* World);
    bool CompleteBuildingCommit(class AVoxelBuildWorld* World);
    bool WorldAction(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& Request,FString& Reason);
    const FColdSteelSharedInventoryData& Data() const {return Current;}
    const FString& WorldKey() const {return SaveSlot;}
private:
    void CaptureDropTransforms();
    void RefreshDropActors();
    bool SaveWorld(const FColdSteelSharedInventoryData& Data);
    UPROPERTY() FColdSteelSharedInventoryData Current;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> SharedHarvestModel;
    TMap<FString,TWeakObjectPtr<AColdSteelPickup>> DropActors;
    FString SaveSlot;
    bool bInitialized=false,bBlocked=false,bCommitting=false;
    float HarvestClockAccum=0.f;
};
