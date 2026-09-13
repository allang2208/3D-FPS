#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "VoxelBuildWorld.generated.h"

class UVoxelBuildPalette;
class UDynamicMeshComponent;
class UMaterialInterface;

USTRUCT()
struct FVoxelSavedCell
{
    GENERATED_BODY()
    UPROPERTY() FIntVector Position=FIntVector::ZeroValue;
    UPROPERTY() FName Material;
};

UCLASS()
class FPSGAME_API UVoxelBuildSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=1;
    UPROPERTY() int32 CellSizeCm=20;
    UPROPERTY() FString WorldKey;
    UPROPERTY() TArray<FVoxelSavedCell> Cells;
};

struct FVoxelEditCell
{
    FIntVector Position;
    FName Before;
    FName After;
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
    UFUNCTION(BlueprintPure, Category="Building") int32 BlockCount() const { return Cells.Num(); }
    UFUNCTION(BlueprintCallable, Category="Building") bool EditCells(const TArray<FIntVector>& Positions, FName Material);
    UFUNCTION(BlueprintCallable, Category="Building") bool Undo();
    UFUNCTION(BlueprintCallable, Category="Building") bool Save();
    bool CanPlace(const TArray<FIntVector>& Positions, FName Material, FString& Reason) const;
    bool IsReady() const { return bReady; }
    const FString& ResultMessage() const { return Message; }
    bool OwnsSurface(const UPrimitiveComponent* Component) const;

private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TMap<FIntVector,TObjectPtr<UDynamicMeshComponent>> Chunks;
    UPROPERTY() TMap<FIntVector,TObjectPtr<UDynamicMeshComponent>> RoundedChunks;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> SurfaceMaterials;
    TMap<FIntVector,FName> Cells;
    TArray<TArray<FVoxelEditCell>> History;
    TMap<FName,int32> MaterialSlots;
    FString WorldKey;
    FString SaveSlot;
    FString Message;
    bool bReady=false;
    bool Commit(const TArray<FVoxelEditCell>& Edit, bool bRemember);
    void RebuildAffected(const TArray<FVoxelEditCell>& Edit);
    void RebuildChunk(FIntVector Chunk);
};
