#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildComponent.generated.h"

class AVoxelBuildWorld;
class UVoxelBuildPalette;
class UVoxelBuildWidget;
class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
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
    bool HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> BuildWorld;
    UPROPERTY() TObjectPtr<UVoxelBuildWidget> Widget;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Preview;
    UPROPERTY() TObjectPtr<UStaticMesh> GhostMesh;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> FoundationPreview;
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
    double LastSnapTime=-10.,GroundSampleAt=-10.,LastAimLog=-10.;
    /** 幽灵框只在光标/计划框真的移动时重建。 */
    FVector LastCursorPoint=FVector(TNumericLimits<double>::Max());
    FVector LastCursorNormal=FVector::ZeroVector,LastPlanMin=FVector::ZeroVector,LastPlanMax=FVector::ZeroVector;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> PreviewMID;
    FName SelectedMaterial=TEXT("wood");
    FName SelectedComponent;
    TWeakObjectPtr<AActor> AimedPrefab;
    FIntVector PrefabCell=FIntVector::ZeroValue;
    FString PrefabMessage;
    FHitResult Hit;
    FVoxelBuildKey HitCell;
    FGuid PlacementVolume;
    FVector PlacementOrigin=FVector::ZeroVector;
    FName PlacementMaterial;
    bool bPlacementSnap=true;
    TArray<FIntVector> Placement;
    TArray<FIntVector> Removal;
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
    bool bRotate=false;
    bool bUndoModifier=false;
    bool bPanelOpen=false;
    int32 ComponentYaw=0;
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
    static FIntVector ShapeSize(int32 Shape,bool bRotate=false);
    static const TCHAR* ShapeName(int32 Shape);
    void UpdatePrefabTarget(bool bHit);
    void UpdatePrefabPreview();
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
    /** 结构预警：跨过 85% / 100% 各播报一次提示栏，回落到 80% 以下重新武装。 */
    void UpdateStructureWarning(class AVoxelBuildWorld& World);
    /** Removes plan cells that sit inside the local player so a brush can still be placed around them. */
    int32 ClipLocalPlayerCells(TArray<FIntVector>& Cells,FVector Origin) const;
    FIntVector BrushSize() const;
    void FillBrush(FIntVector Base,TArray<FIntVector>& Result) const;
    double PlacementCheckAt=0;
    double TargetUpdateAt=0;
    uint64 CheckedRevision=MAX_uint64;
    FName CheckedMaterial;
    FGuid CheckedVolume;
    FVector CheckedOrigin=FVector::ZeroVector;
    TArray<FIntVector> CheckedCells;
    FString CheckedMessage;
    bool bCheckedSnap=true,bCheckedValid=false;
};
