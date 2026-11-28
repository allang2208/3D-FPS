#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildComponent.generated.h"

class AVoxelBuildWorld;
class ATemperateHillsWorld;
class UVoxelBuildPalette;
class UVoxelBuildWidget;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
struct FVoxelBuildPrefab;
struct FInputKeyEventArgs;

/** Controller-owned input/presentation. World owns edits and persistence. */
UCLASS(ClassGroup=(Building),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UVoxelBuildComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UVoxelBuildComponent();
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    UPROPERTY(EditAnywhere,Category="Building") TSoftObjectPtr<UVoxelBuildPalette> PaletteAsset;
    UFUNCTION(BlueprintCallable,Category="Building") void SetBuildMode(bool Enabled);
    /** 2026-09-20 吸附排查：绕过输入锁强制建造态，逐瞄准姿态直调 UpdateTarget，报告落盘 Saved/aimdiag_report.txt。 */
    UFUNCTION(BlueprintCallable,Category="Building|Diagnostics") void RunAimDiagnostics();
    /** Drawer state: cursor & UI-only input while choosing, game input while placing. */
    UFUNCTION(BlueprintCallable,Category="Building") void SetPanelOpen(bool Open);
    UFUNCTION(BlueprintCallable,Category="Building") void ClosePanel() { SetPanelOpen(false); }
    UFUNCTION(BlueprintPure,Category="Building") bool IsPanelOpen() const { return bPanelOpen; }
    UFUNCTION(BlueprintCallable,Category="Building") void SelectMaterial(FName Id);
    /** Select a prefab piece instead of a voxel material; empty clears the component selection. */
    UFUNCTION(BlueprintCallable,Category="Building") void SelectComponent(FName Id);
    UFUNCTION(BlueprintCallable,Category="Building") void SelectComponentByIndex(int32 Index);
    /** Drawer 其他构造 entry: pick a material and one of the shared voxel construction shapes. */
    UFUNCTION(BlueprintCallable,Category="Building") void SelectShape(FName MaterialId,int32 ShapeMode);
    /** Number row 1/2/3-9/0 in the drawer: pick and return to building. */
    bool HandlePanelKey(const FKey& Key);
    /** The focused drawer already consumed this frame's key; the game-side shortcuts must skip it.
        Needed by the drawer's visible-row numbering, which differs from palette order when a
        其他构造 submenu is expanded. */
    void MarkDrawerKeyHandled();
    /** B/Esc keys pressed while the drawer owns keyboard focus. */
    bool HandleDrawerKey(const FKey& Key);
    UFUNCTION(BlueprintPure,Category="Building") FName GetSelectedComponent() const { return SelectedComponent; }
    UFUNCTION(BlueprintPure,Category="Building") bool IsBuilding() const { return bActive; }
    UFUNCTION(BlueprintPure,Category="Building") bool IsSnapEnabled() const { return bSnapEnabled; }
    bool IsVillageCameraPlacing() const { return VillageCamera != nullptr && !bPanelOpen; }
    bool HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend class UTemperateVillageCheckCommandlet;
    void SyncVillageCamera();
    void LeaveVillageCamera(bool RestoreGameInput);
    void SetVillageCursorMode();
    void UpdateVillageCamera(float DeltaSeconds);
    void PositionVillageCamera();
    bool VillageCursorRay(FVector& Origin,FVector& Direction) const;
    UPROPERTY(Transient) TObjectPtr<class ACameraActor> VillageCamera;
    TWeakObjectPtr<AActor> PreviousVillageView;
    TWeakObjectPtr<APawn> VillageCameraPawn;
    FVector VillageFocus=FVector::ZeroVector;
    double VillageCameraYaw=0.;
    bool bVillageVertical=false;
    bool bVillageDisabledPawn=false;
    TSharedPtr<class SWidget> VillageCameraOverlay;
    TSharedPtr<class STextBlock> VillageCameraCaption;
    TWeakObjectPtr<class UFPSCombatHealthComponent> VillageBuilderHealth;
    bool PreparePreviewAssets();
    TSharedPtr<struct FStreamableHandle> PreviewAssetHandle;
    TSharedPtr<struct FStreamableHandle> SurfaceAssetHandle;
    bool bSurfaceAssetsRequested=false;
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> BuildWorld;
    TWeakObjectPtr<ATemperateHillsWorld> VillageWorld;
    void RefreshVillageConstructionAccess();
    UPROPERTY() TObjectPtr<UVoxelBuildWidget> Widget;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Preview;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> VillageGatePreviewParts;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> GatePreviewLeaf;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> EntrancePreview;
    FName EntrancePreviewRecipe;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> WallCutPreview;
    TArray<FTransform> WallCutBars;
    int64 WallCutSelection=-1;
    TArray<FTransform> DisplayedWallCutBars;
    void UpdateWallCutPreview();
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> SiegeRangeDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SiegeRangeMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> SiegeRangeMaterial;
    FName SiegeRangeRecipe;
    uint64 SiegeRangeRanks=MAX_uint64;
    uint64 SiegeRangeExtraRanks=MAX_uint64;
    double SiegeRangeOuter=-1.,SiegeRangeInner=-1.,SiegeGroundElevCm=0.;
    FVector SiegeRangeCenter=FVector(TNumericLimits<double>::Max());
    FVector SiegeGroundSampleXY=FVector(TNumericLimits<double>::Max());
    bool bSiegeRangeValid=false;
    void UpdateSiegeRangePreview(FName Recipe,const FVector& SiteWorld,bool bValid);
    void HideSiegeRangePreview();
    FName PreviewGateAssembly;
    UPROPERTY() TObjectPtr<UStaticMesh> GhostMesh;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> FoundationPreview;
    /** 2026-10-14 屋顶阶梯族的逐格 ghost：斜坡/山墙/金字塔的真实排列预览（整体拉伸盒在
     *  斜坡上看起来就是一面墙，无法表达阶梯）。与 FoundationPreview 分开，避免与贴地
     *  角标/地基柱互相覆盖；材质与整体盒共用 PreviewMID（红绿有效色一致）。 */
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> CellGhost;
    /** 2026-10-15 楔形切割坡的逐格 ghost：45°/26°下/26°上三种预览网格（SM_VoxelWedge*，
     *  由 UVoxelSurfaceLibrary::CreateExampleMeshCut 离线烘焙，几何与放置后一致）。
     *  实例按切口方向带 yaw 旋转；缺资产时回落 CellGhost 立方体。 */
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> CellCutGhost45;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> CellCutGhost26L;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> CellCutGhost26U;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> CellCutGhostTent;
    UPROPERTY() TObjectPtr<AActor> PreviewActor;
    /**
     * 贴边金色高亮的缓存。2026-09-16 清理：这些原先是文件级全局 + 函数 static，既会在 PIE 双开、
     * 预览世界与游戏世界并存时串味，也把 UObject 指针放在 UPROPERTY 之外（GC 风险），现收进成员。
     */
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> AimEdgeComponent;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> AimEdgeMaterial;
    FIntVector AimEdgeCell=FIntVector(INT32_MAX);
    uint32 AimEdgeSignature=0;
    int32 AimEdgeCount=-1;
    bool bAimEdgeGold=false;
    /** 上一次定位是否走了锥形吸附兜底（诊断用）。 */
    bool LastAimWasAssisted=false;
    bool GrowUpPlan=false;
    /** 2026-10-19：本次放置计划是否走了"同平面续坡"（诊断/提交追踪用）。 */
    bool bPlacementContinued=false;
    double LastSnapTime=-10.,GroundSampleAt=-10.,LastAimLog=-10.;
    /** 审计 U3（2026-09-23）：抽屉持焦时消费键的帧戳。原为文件级 static，PIE 双开互相吞键；收进成员。 */
    uint64 DrawerKeyFrame=0;
    /** 审计 U1（2026-09-23）：UpdateWidget 生产端签名——廉价分量键 + 结构 Revision，都没变就整段跳过字符串构造。 */
    uint64 LastWidgetCheapKey=MAX_uint64,LastWidgetRevision=MAX_uint64;
    /** 幽灵框只在光标/计划框真的移动时重建。 */
    FVector LastCursorPoint=FVector(TNumericLimits<double>::Max());
    FVector LastCursorNormal=FVector::ZeroVector,LastPlanMin=FVector::ZeroVector,LastPlanMax=FVector::ZeroVector;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> PreviewMID;
    FName SelectedMaterial=TEXT("wood");
    FName SelectedComponent;
    TWeakObjectPtr<AActor> AimedPrefab;
    FIntVector PrefabCell=FIntVector::ZeroValue;
    // Quarter turns for lattice/socket addressing. Free castle pieces use a separate exact angle.
    int32 PrefabPlanYaw=0;
    TWeakObjectPtr<class AVillageDefenseSection> DefenseDockTarget;
    TOptional<FTransform> DefenseDockPose;
    TOptional<FTransform> SiegeFloorPreview;
    int32 DefenseDockSocket=INDEX_NONE;
    FString PrefabMessage;
    FHitResult Hit;
    FVoxelBuildKey HitCell;
    FGuid PlacementVolume;
    FVector PlacementOrigin=FVector::ZeroVector;
    FName PlacementMaterial;
    bool bPlacementSnap=true;
    TArray<FIntVector> Placement;
    /** 与 Placement 前段（笔刷格）平行的楔形切割字节；地基柱等后附格没有对应条目（提交时按 0 补齐）。 */
    TArray<uint8> PlacementCuts;    TArray<FIntVector> Removal;
    FString TargetMessage;
    FString Feedback;
    FString InitializationMessage=TEXT("正在准备世界");
    float FeedbackTime=0;
    float InitializeCountdown=0;
    bool bInitializeFailed=false;
    bool bActive=false;
    bool bCanPlace=false;
    bool bFeedbackValid=false;
    bool bSnapEnabled=true;
    /** 2026-10-15：R 键旋转从两态升级四态（0/90/180/270°）——楔形切割坡需要四个爬升方向
     *  （山墙双坡），旧两态只覆盖 +X/+Y。 */
    int32 BrushRotation=0;
    bool bUndoModifier=false;
    bool bPanelOpen=false;
    int32 ComponentYaw=0;
    int32 GroundYawDegrees=0;
    int32 PlannedGroundYaw() const;
    int32 Brush=0;
    float NoticeRisk=0;
    /** 最近一次放置扣料失败的原因。 */
    FString BlockMessage;
    bool bPrefabValid=false;
    bool bPrefabAimHit=false;
    void TryInitializeWorld();
    void UpdateTarget();
    const FVoxelBuildPrefab* SelectedPrefab() const;
    /** Wheel order and 其他构造 submenu share this one shape table (single source of truth). */
    static int32 ShapeCount();
    /** Rotation=0..3（90° 步进；奇数步交换包围盒 X/Y）。 */
    static FIntVector ShapeSize(int32 Shape,int32 Rotation=0);
    static const TCHAR* ShapeName(int32 Shape);
    /** 2026-10-14 屋顶阶梯族：该形状是否为非 Box 的格子排列形状（预览走逐格 ghost 而不是整体盒）。 */
    static bool ShapeIsStaircase(int32 Shape);
    /** 2026-10-16：是否斜坡刷（行进轴不居中、低边锚在瞄准格）。 */
    static bool ShapeIsSlope(int32 Shape);
    /** 2026-10-19：斜坡刷的爬升比（0=非坡；1=45°；2≈26°）。连续平面续接只处理 45°。 */
    static int32 ShapeSlopeRise(int32 Shape);
    /** 该形状的全部格子（以包围盒最小角为原点；Rotation 见 ShapeSize，变换后重排保证
     * 首格=包围盒最小角）。FillBrush、面板图标与诊断共用这一个真源。 */
    static void ShapeCells(int32 Shape,int32 Rotation,TArray<FIntVector>& OutCells);
    /** 与 ShapeCells 输出按下标平行的楔形切割字节（VoxelCut 编码；非 Slope 形状全 0）。
     *  坡向随 Rotation：0=+X 1=+Y 2=-X 3=-Y；45° 整格切，26° 下/上半格交替。 */
    static void ShapeCuts(int32 Shape,int32 Rotation,const TArray<FIntVector>& Cells,TArray<uint8>& OutCuts);
    /** 调试/验收出口：返回形状的格子排列（commandlet 里核对阶梯形状用，不依赖瞄准与放置）。 */
    UFUNCTION(BlueprintPure,Category="Building|Debug") static void DebugShapeCells(int32 Shape,bool bRotate,TArray<FIntVector>& OutCells);
    /** 调试/验收出口（2026-10-15 四态旋转+楔形切割）：格子与平行的切割字节一起返回。 */
    UFUNCTION(BlueprintPure,Category="Building|Debug") static void DebugShapePlan(int32 Shape,int32 Rotation,TArray<FIntVector>& OutCells,TArray<uint8>& OutCuts);
    /** 诊断（2026-10-17）：当前放置计划/切割/笔刷/旋转的现场状态——排查"切割未落盘"。 */
    UFUNCTION(BlueprintPure,Category="Building|Debug") FString DebugPlacementState() const
    {
        FString S=FString::Printf(TEXT("brush=%d rot=%d place=%d cuts=%d nonzero=%d cont=%d"),
            Brush,BrushRotation,Placement.Num(),PlacementCuts.Num(),
            FMath::CountBits(0)+[&]{int32 N=0;for(const uint8 C:PlacementCuts)if(C)++N;return N;}(),
            bPlacementContinued?1:0);
        return S;
    }
    void UpdatePrefabTarget(bool bHit);
    void RefreshPlacementInput();
    void UpdatePrefabPreview();
    void UpdateEntrancePreview(FName Recipe, bool bValid);
    void ValidatePlacement();
    void UpdatePreview(FIntVector Size);
    void UpdateWidget();
    void PushPanelContent();
    /** 金色贴边高亮的组件/清理（签名保持与旧文件级函数一致，调用点无需改动）。 */
    class UInstancedStaticMeshComponent* FindAimEdge(class AActor* PreviewActorArg);
    void ClearAimHighlight(class AActor* PreviewActorArg);
    void PlacePrefab();
    /** 拆除出来的体素直接进背包；放不下的变成脚下的方块掉落并在提示栏播报。 */
    void GrantDismantledBlocks(const TMap<FName,int32>& Removed);
    /** 放置消耗体素块（背包优先、仓库兜底）；不足时返回 false 并写入 BlockMessage。 */
    bool ConsumePlacementBlocks(FName Material,int32 Count);
    void RefundPlacementBlocks(FName Material,int32 Count);
    /** 开发面板开关：开启时放置不扣体块，扣料与退回同时跳过。 */
    bool IsFreeBuilding() const;
    /** 结构预警：跨过 85% / 100% 各播报一次提示栏，回落到 80% 以下重新武装。 */
    void UpdateStructureWarning(class AVoxelBuildWorld& World);
    /** Removes plan cells that sit inside the local player so a brush can still be placed around them.
     *  ParallelCuts（可空）随格同步裁剪，保持楔形切割字节与幸存格按下标对齐。 */
    int32 ClipLocalPlayerCells(TArray<FIntVector>& Cells,FVector Origin,TArray<uint8>* ParallelCuts=nullptr) const;
    FIntVector BrushSize() const;
    /** Base 是斜坡刷的低边（檐口）格：负向坡在内部回让 (Size-1) 格，使四个旋转都
     *  从瞄准格起坡（2026-10-19 连续平面）。放置、拆除与幽灵共用这一口径。 */
    void FillBrush(FIntVector Base,TArray<FIntVector>& Result,TArray<uint8>* OutCuts=nullptr) const;
    double PlacementCheckAt=0;
    double TargetUpdateAt=0;
    uint64 CheckedRevision=MAX_uint64;
    FName CheckedMaterial;
    FGuid CheckedVolume;
    FVector CheckedOrigin=FVector::ZeroVector;
    TArray<FIntVector> CheckedCells;
    TArray<uint8> CheckedCuts;
    FString CheckedMessage;
    bool bCheckedSnap=true,bCheckedValid=false;
};
