#pragma once
#include "CoreMinimal.h"
#include "DungeonTypes.generated.h"

// Saved profile compatibility only. Old recipe rooms/encounters are no longer generated.
USTRUCT()
struct FDungeonEnemySlot
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() FString ClassPath;
    UPROPERTY() FVector Offset = FVector::ZeroVector;
    UPROPERTY() float HealthMultiplier = 1;
    UPROPERTY() float DamageMultiplier = 1;
};

USTRUCT()
struct FDungeonRoom
{
    GENERATED_BODY()
    UPROPERTY() FName Id;
    UPROPERTY() FString Role;
    UPROPERTY() FString TemplateId;
    UPROPERTY() int32 TemplateVersion = 1;
    UPROPERTY() FVector Center = FVector::ZeroVector;
    UPROPERTY() FVector Size = FVector(1600,1600,380);
    UPROPERTY() int32 DressingSeed = 0;
    UPROPERTY() int32 CoverCount = 0;
    UPROPERTY() bool bWorkbench = false;
    UPROPERTY() int32 AliveCap = 6;
    UPROPERTY() int32 GoldReward = 0;
    UPROPERTY() int32 AmmoReward = 0;
    UPROPERTY() TArray<FDungeonEnemySlot> Enemies;
};

USTRUCT()
struct FDungeonConnection
{
    GENERATED_BODY()
    UPROPERTY() int32 A = 0;
    UPROPERTY() int32 B = 0;
    UPROPERTY() float Width = 600;
    // Includes room centres; the assembler trims to the actual doorway planes.
    UPROPERTY() TArray<FVector> Path;
    UPROPERTY() TArray<FName> RequiresClears;
};

USTRUCT()
struct FDungeonRunState
{
    GENERATED_BODY()
    UPROPERTY() int32 Version = 1;
    UPROPERTY() FString RunId;
    UPROPERTY() FString ProfileId;
    UPROPERTY() int32 ProfileRevision = 1;
    UPROPERTY() int32 Seed = 0;
    // Authored generator receipt. A seed alone cannot reproduce a timed-out search.
    UPROPERTY() int32 GeneratorVersion = 0;
    UPROPERTY() FString LayoutManifestJson;
    UPROPERTY() int32 GlobalAliveCap = 12;
    UPROPERTY() float PortalWidth = 240;
    UPROPERTY() float PortalHeight = 280;
    UPROPERTY() bool bCompleted = false;
    UPROPERTY() TArray<FDungeonRoom> Rooms;
    UPROPERTY() TArray<FDungeonConnection> Connections;
    UPROPERTY() TSet<FName> Explored;
    UPROPERTY() TSet<FName> ActiveEncounters;
    UPROPERTY() TSet<FName> Cleared;
    UPROPERTY() TSet<FName> Claimed;
    UPROPERTY() TSet<FName> Events;
    UPROPERTY() TSet<FName> DefeatedEnemies;
    // Checkpoints are safe room centres, never an enemy room or a doorway.
    UPROPERTY() int32 SafeRoom = 0;
};
