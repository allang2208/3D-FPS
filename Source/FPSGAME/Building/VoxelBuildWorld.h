#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildWorld.generated.h"

class UVoxelBuildPalette;
class UDynamicMeshComponent;
class UMaterialInterface;
struct FVoxelSupportGraph;

UCLASS()
class FPSGAME_API UVoxelBuildSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=2;
    UPROPERTY() int32 CellSizeCm=20;
    UPROPERTY() FString WorldKey;
    UPROPERTY() TArray<FVoxelSavedCell> Cells;
    UPROPERTY() TArray<FVoxelFreeVolume> FreeVolumes;
};

/** One world owner; 16^3 cells per mesh component, no per-cell Actors. Local single player. */
UCLASS(BlueprintType)
class FPSGAME_API AVoxelBuildWorld : public AActor
{
    GENERATED_BODY()
public:
    AVoxelBuildWorld();
    static constexpr int32 CellSizeCm=20;
    static constexpr int32 ChunkSide=16;
    static FIntVector ToCell(const FVector& Position);
    static FVector CellMin(FIntVector Cell);
    static FVector CellCenter(FIntVector Cell);
    static FIntVector ChunkFor(FIntVector Cell);
    bool Initialize(const FString& InWorldKey, UVoxelBuildPalette* InPalette);
    UFUNCTION(BlueprintPure, Category="Building") FName MaterialAt(FIntVector Cell) const;
    UFUNCTION(BlueprintPure, Category="Building") int32 BlockCount() const;
    UFUNCTION(BlueprintPure, Category="Building") int32 UnsupportedBlockCount() const;
    UFUNCTION(BlueprintCallable, Category="Building") bool EditCells(const TArray<FIntVector>& Positions, FName Material);
    UFUNCTION(BlueprintCallable, Category="Building") bool Undo();
    UFUNCTION(BlueprintCallable, Category="Building") bool Save();
    bool CanPlace(const TArray<FIntVector>& Positions, FName Material, FString& Reason) const;
    FName VolumeMaterialAt(FGuid Volume,FIntVector Cell) const;
    FVector VolumeOrigin(FGuid Volume) const;
    bool CanPlaceInVolume(FGuid Volume,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool CanPlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool EditVolumeCells(FGuid Volume,const TArray<FIntVector>& Positions,FName Material);
    bool PlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material);
    bool ResolveHit(const FHitResult& Hit,FVoxelBuildKey& Key) const;
    bool IsReady() const { return bReady; }
    const FString& ResultMessage() const { return Message; }
    bool OwnsSurface(const UPrimitiveComponent* Component) const;

private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TMap<FVoxelBuildKey,TObjectPtr<UDynamicMeshComponent>> Chunks;
    UPROPERTY() TMap<FVoxelBuildKey,TObjectPtr<UDynamicMeshComponent>> RoundedChunks;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> SurfaceMaterials;
    TMap<FIntVector,FName> Cells;
    TMap<FGuid,FVoxelFreeVolume> FreeVolumes;
    TMap<const UPrimitiveComponent*,FGuid> CollisionVolumes;
    TMap<FVoxelBuildKey,bool> AnchorCache;
    TSharedPtr<FVoxelSupportGraph> SupportGraph;
    TArray<TArray<FVoxelEditCell>> History;
    TMap<FName,int32> MaterialSlots;
    FString WorldKey;
    FString SaveSlot;
    FString Message;
    bool bReady=false;
    bool Commit(const TArray<FVoxelEditCell>& Edit, bool bRemember);
    bool CanPlaceAt(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool ScenePlacementAllowed(FVector Min,FString& Reason) const;
    bool IsGroundAnchor(FVector Min) const;
    bool CanCommit(const TArray<FVoxelEditCell>& Edit,FString& Reason) const;
    void RefreshSupportGraph();
    void SetCell(const FVoxelEditCell& Edit,bool bAfter);
    void RebuildAffected(const TArray<FVoxelEditCell>& Edit);
    void RebuildChunk(FVoxelBuildKey Chunk);
};
