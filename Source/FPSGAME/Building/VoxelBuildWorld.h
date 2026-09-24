#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "CollisionQueryParams.h"
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
    // Version 5 appended furnace smelting jobs (pure wall-clock); version 6 replaces that chunk
    // with the fuel model (accumulated progress + per-furnace stored fuel); version 7 adds batch
    // count to jobs and furnace upgrade level to fuel records; version 8 adds the idle-fire clock;
    // version 9 splits upgrades into three axes (fuel capacity + per-run input cap).
    // 该默认值是 UHT 字面量，升版本时必须与 VoxelBuildPersistence.h 的 GVoxelBuildSaveVersion 同步。
    UPROPERTY() int32 Version=9;
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
    // v6: smelting jobs (fuel model) + per-furnace stored fuel. VBX v6 trailing chunks.
    TArray<FVoxelSmeltingJob> Smelting;
    TArray<FVoxelFurnaceFuel> Fuel;
    // v5 read path only: old wall-clock jobs, migrated during load and never written back as-is.
    TArray<FVoxelSmeltingJobV5> LegacySmelting;
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
    /** 点击冶炼用：立刻把当前快照写入建筑档，不走 2 秒合并。 */
    bool FlushPersistenceNow();
    const FString& BuildingWorldKey() const { return WorldKey; }
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
    /**
     * 门／窗／柱等**已放置构件**的碰撞面也是体素焊接目标（2026-09-19）：命中构件自身碰撞时，
     * 返回命中面内侧那一格占用格（世界格子坐标，Volume 置空＝与 PrefabCells／世界格同一坐标系），
     * 调用方按普通体素面做面偏移出目标格。解决"在门框／窗框上或正上方砌不了体素、幽灵不贴构件面"。
     * 摆动出来的门／窗扇打在占格体积之外，返回 false（照常落回贴地分支）。
     */
    bool ResolvePrefabSurfaceCell(const FHitResult& Hit,FVoxelBuildKey& Key) const;
    /** 命中是否落在已放置构件的网格上（占位 Actor 或挂在它下面的逻辑构件），不校验占格——
     *  摆开到占格之外的门／窗扇也算。瞄准多命中用它跳过构件找后面的墙／地面。 */
    bool HitBelongsToPlacedPrefab(const FHitResult& Hit) const;
    /** 该世界格是否被某件已放置构件占用（自由体积的格先换算回世界格再查）。 */
    bool IsPrefabCell(FGuid Volume,FIntVector Cell) const;
    /** 世界最小角对应格的六面对面邻居里有构件占格：构件为体素提供支撑锚（2026-09-19）。 */
    bool PrefabSupportAt(FVector WorldMin) const;
    /** 瞄准格落在构件占格内时，给出该列"占格顶之上"那一格（仰视门框侧面＝框上砌块的手势，2026-09-19）。 */
    bool PrefabColumnTop(FIntVector Cell,FIntVector& OutTopCell) const;
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
    /** 该锚格上是否还有一件**在记录里**的构件（落体件不算：它已离开 Prefabs）。 */
    bool HasPrefabAt(FIntVector Cell) const
    {return Prefabs.ContainsByPredicate([Cell](const FVoxelBuildPrefabInstance& E){return E.Cell==Cell;});}
    /**
     * 炉内冶炼（VBX v6，随构件记录同生共死）：任务与燃料都按高炉锚格存。
     * 进度模型＝已积累秒数＋当前燃烧段（UTC ticks），燃料耗尽即停炉；
     * 结算/续燃在 UColdSteelSmeltingSystem（配方与物品侧），这里只存状态。
     */
    const FVoxelSmeltingJob* FindSmelting(FIntVector Cell) const;
    /** 就地结算入口——只应被 UColdSteelSmeltingSystem 的 Settle/AddFuel 使用。 */
    FVoxelSmeltingJob* FindSmeltingMutable(FIntVector Cell);
    /** 该锚格上是一件**在记录里**的高炉（Id 匹配稳定键）。燃料/开炉入口用它把关。 */
    bool IsFurnaceAt(FIntVector Cell) const
    {return Prefabs.ContainsByPredicate([Cell](const FVoxelBuildPrefabInstance& E){return E.Cell==Cell&&E.Id==VoxelSmeltingFurnaceId;});}
    /** 结算改写任务字段后标脏存档（FindSmeltingMutable 的写回配套；SetFuel 自带标脏）。 */
    void MarkSmeltingDirty(){MarkSaveDirty();}
    bool BeginSmelting(FIntVector Cell,FName Recipe,FString& Reason,int64 Batch=1);
    /** 高炉升级等级（VBX v7，存在燃料记录里）：无记录＝1 级。速度轴的旧名（大量既有调用）。 */
    int32 FurnaceLevel(FIntVector Cell) const;
    /** 写等级（封顶 VoxelFurnaceMaxLevel）；没有记录时创建一条 0 燃料记录承载等级。 */
    void SetFurnaceLevel(FIntVector Cell,int32 Level);
    /** 三轴升级等级（VBX v9，轴号见 VoxelFurnaceAxis*）：无记录/未升＝1 级。 */
    int32 FurnaceUpgradeLevel(FIntVector Cell,int32 Axis) const;
    void SetFurnaceUpgradeLevel(FIntVector Cell,int32 Axis,int32 Level);
    bool ClearSmelting(FIntVector Cell);
    double FuelAt(FIntVector Cell) const;
    /** 写燃料（秒）；<=0 清除条目。标脏存档。 */
    void SetFuel(FIntVector Cell,double Seconds);
    /** 空闲火种段起点（VBX v8，存在燃料记录里）：无记录/火已熄＝0。 */
    int64 FurnaceFireTicks(FIntVector Cell) const;
    /** 写火种段起点；仅记录存在时生效（火种随燃料同生共死，不单独标脏——料在烧自然会脏）。 */
    void SetFurnaceFireTicks(FIntVector Cell,int64 Ticks);
    /** 拆除前退回炉内矿料与存料（完成退产物、未完退原料，燃料折回木材）；
     *  false=背包放不下，状态保留、拒绝拆除。 */
    bool RefundSmeltingAt(FIntVector Cell,FString& Reason);
    /** bSurfaceBacked：本次瞄准命中了竖直表面（壁挂构件用它代替地面/邻接支撑判定）。 */
    bool CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked=false) const;
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
    /**
     * 构件被拆除／脱落后：检查腾出格的六面邻格里的体素节点，原来把构件当支撑锚的全部重判
     * （地面锚定＋构件邻接口径），失去锚定的改判 bAnchor=false 并标脏，交给承重解算按既有流程倒塌。
     */
    void ReanchorVoxelsAround(const TArray<FIntVector>& VacatedCells);
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
    /** 炉内冶炼任务（锚格→配方+积累进度+燃烧段），与 Prefabs 同档持久化（VBX v6）。 */
    TArray<FVoxelSmeltingJob> SmeltingJobs;
    /** 各炉存料（秒）：跨批次保留，拆除时折回木材退库。 */
    TArray<FVoxelFurnaceFuel> Fuels;
    TSet<FIntVector> PrefabCells;
    /** 占格 → 所属构件的锚格：支撑判定要区分"这格是别的构件"（含自己的格子）。 */
    TMap<FIntVector,FIntVector> PrefabCellOwner;
    // 审计 P23（2026-09-21 移除）：原 `TMap<FVoxelBuildKey,bool> AnchorCache` 全目录只有写入
    // 与删除、**没有任何读取**，所以它一条射线都没省下，只是每格多占一个 TMap 条目
    // （键 28B + bool + 哈希槽；2 万格约 0.6 MB）。已确认 AnchorCache 不在任何回归面上：
    // 放置判定走 CanPlaceAt 里临时构造的 Draft 图，锚定由 IsGroundAnchor/PrefabSupportAt 现算。
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
    /** CachedParams 由调用方在格循环外构造一次（审计 P3）：本函数会被 CanPlaceAt 逐格调用，
     *  而 VoxelGrounding::Query 每次构造都要遍历全部 Pawn。传 nullptr 时自行构造。 */
    bool ScenePlacementAllowed(FVector Min,FString& Reason,bool* OutAnchor=nullptr,const FCollisionQueryParams* CachedParams=nullptr) const;
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
    /** 冶炼后台落账（2026-09-24 排查"燃料不随时间减少"）：挂钟结算不能只活在面板 Tick 里，
     *  关着背包也要按真实时间烧料/推进并标脏存档（"关闭游戏也计入"承诺的兑现处）。 */
    void TickSmelting(float Delta);
    float SmeltingSettleAccum=0.f;
    void MarkSaveDirty();
    UVoxelBuildSave* MakeSnapshot() const;
    void EnqueueFragment(FVoxelFragmentSave State,TArray<FVoxelBuildKey> Sources={},FGuid Replaces={},bool bFailureDebris=false);
    UFUNCTION() void OnBuildingHit(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector Impulse,const FHitResult& Hit);
};
