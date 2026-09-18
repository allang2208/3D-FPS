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
class AVoxelBuildPrefabActor;
struct FVoxelSupportGraph;
struct FVoxelBuildRuntime;
struct FVoxelGeometry;

UCLASS()
class FPSGAME_API UVoxelBuildSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version=4;
    UPROPERTY() int32 CellSizeCm=20;
    UPROPERTY() FString WorldKey;
    UPROPERTY() TArray<FVoxelSavedCell> Cells;
    UPROPERTY() TArray<FVoxelFreeVolume> FreeVolumes;
    UPROPERTY() TMap<FVoxelBuildKey,float> Damage;
    UPROPERTY() TSet<FVoxelBrokenBond> BrokenBonds;
    UPROPERTY() TArray<FVoxelFragmentSave> Fragments;
    UPROPERTY() TSet<FVoxelBuildKey> LegacyProtected;
    // Written by the custom VBX snapshot serializer, not by UObject reflection.
    TArray<FVoxelBuildPrefabInstance> Prefabs;
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
    /** Test/diagnostic entry: initialise with the default palette and no player controller
        so Tools/Building/audit_voxel_placement.py can reproduce placement reports headless. */
    UFUNCTION(BlueprintCallable,Category="Building|Debug") bool DebugInitialize(const FString& InWorldKey);
    UFUNCTION(BlueprintPure,Category="Building") FName MaterialAt(FIntVector Cell) const;
    UFUNCTION(BlueprintPure,Category="Building") int32 BlockCount() const;
    UFUNCTION(BlueprintPure,Category="Building") int32 UnsupportedBlockCount() const;
    UFUNCTION(BlueprintCallable,Category="Building") bool EditCells(const TArray<FIntVector>& Positions,FName Material);
    /** 撤销 = 拆除最后一批**放置**（不再把拆掉的东西变回来）；拆下来的方块由调用方回收进背包。 */
    UFUNCTION(BlueprintCallable,Category="Building") bool Undo();
    bool Undo(TMap<FName,int32>* OutRemovedBlocks);
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
    bool ResolveGroundPlacement(const FHitResult& Surface,FIntVector Size,bool bSnap,
        FVector& Origin,TArray<FIntVector>& Positions,FString& Reason) const;
    bool ResolveHit(const FHitResult& Hit,FVoxelBuildKey& Key) const;
    bool IsReady() const {return bReady;}
    const FString& ResultMessage() const {return Message;}
    bool OwnsSurface(const UPrimitiveComponent* Component) const;
    uint64 StructureRevision() const {return Revision;}
    FString StructureStatus() const;
    /** 存档槽名（不带扩展名）；验收工具会用它核对磁盘文件。 */
    const FString& SaveSlotName() const;
    /** 最弱接缝占比（1.0 = 断裂）。面板与提示栏用它做结构预警。 */
    float WeakestJointRatio() const;
    /** 最弱接缝摘要："抗剪 92% · 格(39,-30,10)"；没有解算结果时为空。 */
    FString WeakestJointSummary() const;
    /** 最近一次解算的观测值（面板读数 + 验收基线）：耗时、节点数、边界节点数。 */
    void SolverStats(float& OutSeconds,int32& OutNodes,int32& OutBoundary) const;
    /** 最近一次解算是否覆盖整块连通结构（false = 局部裁剪求解）。 */
    bool LastSolveWasFull() const;
    /** 求解规模/耗时摘要（状态行用）。 */
    FString SolverSummary() const;
    /** 主动拆除残骸时移除它（记录 + Actor + 存档脏标记）；方块物品由调用方发放。 */
    void RemoveFragment(class AVoxelCollapseFragment* Fragment);
    /** 过载渐进损伤：按经过时间给过载格累积损伤，损伤满耐久才掉块。 */
    void ApplyOverloadDamage(const TArray<struct FVoxelOverloadCell>& Overload,double Seconds);
    /** Prefabricated pieces (roman column, balustrade, ...) placed on the 20 cm lattice. */
    UFUNCTION(BlueprintCallable,Category="Building|Prefab") bool PlacePrefab(FName Id,FIntVector Cell,int32 Yaw=0);
    UFUNCTION(BlueprintCallable,Category="Building|Prefab") bool RemovePrefab(AActor* Piece);
    UFUNCTION(BlueprintPure,Category="Building|Prefab") int32 PrefabCount() const {return Prefabs.Num();}
    bool CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason) const;
    /** 构件底面下有没有地形（中心＋四角共 5 个探测点，与体素地面锚定同一口径）。 */
    bool IsPrefabOnGround(FIntVector AnchorCell,FIntVector Footprint) const;
    /**
     * 构件是否"有着落"（2026-09-18 用户报"拆掉周围方块后窗悬空"）：
     *   ① 底面下有地形（与体素共用同一个地面锚定口径 IsGroundAnchor）；
     *   ② 任一占格与体素面对面相邻（含正下方那一格）；
     *   ③ 任一占格与**另一件构件**面对面相邻（凉亭三件叠放、栏杆接柱）。
     * 三条都不成立就是悬空：放置会被拒绝，已放置的会在附近体素被拆／倒塌后脱落。
     * 大件按格子抽样（实现里有采样上限），超大构件理论上可能漏判一次接触。
     */
    bool IsPrefabSupported(const FVoxelBuildPrefabInstance& Instance,FIntVector* OutContact=nullptr) const;
    /** 体素改动后：改动点一格以内的构件若失去支撑就脱落（与右键拆除同一条路径，不退还材料）。 */
    void VerifyPrefabSupport(const TArray<FVoxelEditCell>& Edit);
    UPhysicalMaterial* ContactMaterial() const {return StructuralContact;}
    void QueueFragmentDamage(AVoxelCollapseFragment* Fragment,FVector Position,float Amount,float Radius,float Energy);
    void QueueCollapseImpact(AActor* Other,const FHitResult& Hit,float Energy);

private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TMap<FVoxelBuildKey,TObjectPtr<UDynamicMeshComponent>> Chunks;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> SurfaceMaterials;
    UPROPERTY() TObjectPtr<UPhysicalMaterial> StructuralContact;
    UPROPERTY() TMap<FGuid,TObjectPtr<AVoxelCollapseFragment>> Fragments;
    UPROPERTY() TMap<FIntVector,TWeakObjectPtr<AActor>> PrefabActors;
    TMap<FIntVector,FName> Cells;
    TMap<FGuid,FVoxelFreeVolume> FreeVolumes;
    TArray<FVoxelBuildPrefabInstance> Prefabs;
    TSet<FIntVector> PrefabCells;
    /** 占格 → 所属构件的锚格：支撑判定要区分"这格是别的构件"（含自己的格子）。 */
    TMap<FIntVector,FIntVector> PrefabCellOwner;
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
    bool ScenePlacementAllowed(FVector Min,FString& Reason,bool* OutAnchor=nullptr) const;
    bool IsGroundAnchor(FVector Min) const;
    bool CanCommit(const TArray<FVoxelEditCell>& Edit,FString& Reason) const;
    void RefreshSupportGraph();
    AVoxelBuildPrefabActor* SpawnPrefab(const FVoxelBuildPrefabInstance& Instance);
    void RefreshPrefabOccupancy();
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
    void EnqueueFragment(FVoxelFragmentSave State,TArray<FVoxelBuildKey> Sources={},FGuid Replaces={},bool bFailureDebris=false);
    UFUNCTION() void OnBuildingHit(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector Impulse,const FHitResult& Hit);
};
