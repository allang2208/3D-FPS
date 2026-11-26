#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "../Building/ColdSteelDoorNetState.h"
#include "ColdSteelWorldSnapshot.generated.h"
UCLASS()
class UColdSteelWorldSnapshot : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() FString Map;
    UPROPERTY() FColdSteelProfile Harvest;
    UPROPERTY() TArray<FColdSteelHarvestRemoval> HarvestRemovals;
    UPROPERTY() TArray<uint8> Building;
    UPROPERTY() FColdSteelPlantingNetState Planting;
    UPROPERTY() TMap<FString,FTransform> SceneTransforms;
    UPROPERTY() TSet<FString> BrokenGlass;
    UPROPERTY() TSet<FString> OpenedContainers;
    UPROPERTY() TSet<FString> OpenedChests;
    UPROPERTY() TMap<FString,FColdSteelDoorNetState> DoorSwings;
    UPROPERTY() bool bWelcomeEliteDefeated=false;
    UPROPERTY() FString RunId;
    // Reuse the reliable, compressed world stream. Split strings stay below
    // the archive's per-string bound; this layout is sent once per run/player.
    UPROPERTY() FString DungeonLayoutRunId;
    UPROPERTY() int32 DungeonLayoutSeed=0;
    UPROPERTY() TArray<FString> DungeonLayoutParts;
    UPROPERTY() TSet<FName> Cleared;
    UPROPERTY() TSet<FName> Explored;
    UPROPERTY() bool bCompleted=false;
};
