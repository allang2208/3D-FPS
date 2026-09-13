#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildWorld.generated.h"

class UVoxelBuildPalette;
class UDynamicMeshComponent;
class UMaterialInterface;
class UPhysicalMaterial;
class AVoxelCollapseFragment;
struct FVoxelSupportGraph;
struct FVoxelBuildRuntime;
struct FVoxelGeometry;

UCLASS()
class FPSGAME_API UVoxelBuildSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=3;
    UPROPERTY() int32 CellSizeCm=20;
    UPROPERTY() FString WorldKey;
    UPROPERTY() TArray<FVoxelSavedCell> Cells;
    UPROPERTY() TArray<FVoxelFreeVolume> FreeVolumes;
    UPROPERTY() TMap<FVoxelBuildKey,float> Damage;
    UPROPERTY() TSet<FVoxelBrokenBond> BrokenBonds;
    UPROPERTY() TArray<FVoxelFragmentSave> Fragments;
    UPROPERTY() TSet<FVoxelBuildKey> LegacyProtected;
};

/** Local single-player world owner. Static voxels are batched; debris uses compound bodies. */
UCLASS(BlueprintType)
class FPSGAME_API AVoxelBuildWorld : public AActor
{
    GENERATED_BODY()
public:
    AVoxelBuildWorld();
    AVoxelBuildWorld(FVTableHelper& Helper);
    virtual ~AVoxelBuildWorld() override;
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual float TakeDamage(float Amount,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
    static constexpr int32 CellSizeCm=20;
    static constexpr int32 ChunkSide=16;
    static FIntVector ToCell(const FVector& Position);
    static FVector CellMin(FIntVector Cell);
    static FVector CellCenter(FIntVector Cell);
    static FIntVector ChunkFor(FIntVector Cell);
    bool Initialize(const FString& InWorldKey,UVoxelBuildPalette* InPalette);
    UFUNCTION(BlueprintPure,Category="Building") FName MaterialAt(FIntVector Cell) const;
    UFUNCTION(BlueprintPure,Category="Building") int32 BlockCount() const;
    UFUNCTION(BlueprintPure,Category="Building") int32 UnsupportedBlockCount() const;
    UFUNCTION(BlueprintCallable,Category="Building") bool EditCells(const TArray<FIntVector>& Positions,FName Material);
    UFUNCTION(BlueprintCallable,Category="Building") bool Undo();
    UFUNCTION(BlueprintCallable,Category="Building") bool Save();
    UFUNCTION(BlueprintCallable,Category="Building|Structure") void SetAppliedLoad(FName LoadId,FVector ContactPoint,float MassKg);
    UFUNCTION(BlueprintCallable,Category="Building|Damage") void DamageBuilding(FVector Position,float Amount,float RadiusCm=0);
    bool CanPlace(const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    FName VolumeMaterialAt(FGuid Volume,FIntVector Cell) const;
    FVector VolumeOrigin(FGuid Volume) const;
    bool CanPlaceInVolume(FGuid Volume,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool CanPlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool EditVolumeCells(FGuid Volume,const TArray<FIntVector>& Positions,FName Material);
    bool PlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material);
    bool ResolveHit(const FHitResult& Hit,FVoxelBuildKey& Key) const;
    bool IsReady() const {return bReady;}
    const FString& ResultMessage() const {return Message;}
    bool OwnsSurface(const UPrimitiveComponent* Component) const;
    uint64 StructureRevision() const {return Revision;}
    FString StructureStatus() const;
    UPhysicalMaterial* ContactMaterial() const {return StructuralContact;}
    void QueueFragmentDamage(AVoxelCollapseFragment* Fragment,FVector Position,float Amount,float Radius,float Energy);
    void QueueCollapseImpact(AActor* Other,const FHitResult& Hit,float Energy);

private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TMap<FVoxelBuildKey,TObjectPtr<UDynamicMeshComponent>> Chunks;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> SurfaceMaterials;
    UPROPERTY() TObjectPtr<UPhysicalMaterial> StructuralContact;
    UPROPERTY() TMap<FGuid,TObjectPtr<AVoxelCollapseFragment>> Fragments;
    TMap<FIntVector,FName> Cells;
    TMap<FGuid,FVoxelFreeVolume> FreeVolumes;
    TMap<FVoxelBuildKey,bool> AnchorCache;
    TMap<FVoxelBuildKey,float> CellDamage;
    TSet<FVoxelBuildKey> LegacyProtected;
    TSharedPtr<FVoxelSupportGraph> SupportGraph;
    TUniquePtr<FVoxelBuildRuntime> Runtime;
    TArray<TArray<FVoxelEditCell>> History;
    TMap<FName,int32> MaterialSlots;
    FString WorldKey,SaveSlot,Message;
    uint64 Revision=0;
    bool bReady=false,bClosing=false;
    bool Commit(const TArray<FVoxelEditCell>& Edit,bool bRemember);
    bool CanPlaceAt(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const;
    bool ScenePlacementAllowed(FVector Min,FString& Reason) const;
    bool IsGroundAnchor(FVector Min) const;
    bool CanCommit(const TArray<FVoxelEditCell>& Edit,FString& Reason) const;
    void RefreshSupportGraph();
    void SetCell(const FVoxelEditCell& Edit,bool bAfter);
    void ApplyChanges(const TArray<FVoxelEditCell>& Edit);
    void RebuildAffected(const TArray<FVoxelEditCell>& Edit);
    FVoxelBuildKey RenderKey(FVoxelBuildKey SourceChunk) const;
    void TickMeshes();
    void ApplyChunk(FVoxelBuildKey Key,TSharedPtr<FVoxelGeometry> Geometry);
    void TickStructure();
    void TickFragments();
    void TickDamage();
    void TickPersistence(bool bFlush=false);
    void MarkSaveDirty();
    UVoxelBuildSave* MakeSnapshot() const;
    void EnqueueFragment(FVoxelFragmentSave State,TArray<FVoxelBuildKey> Sources={},FGuid Replaces={});
    UFUNCTION() void OnBuildingHit(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector Impulse,const FHitResult& Hit);
};
