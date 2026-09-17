#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "PreviewScene.h"
#include "VoxelBuildIcons.generated.h"

class UDirectionalLightComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class USceneCaptureComponent2D;
class UStaticMesh;
class UStaticMeshComponent;
class UTextureCube;
class UTextureRenderTarget2D;

/** One thumbnail: a static-mesh piece, or a voxel construction drawn as one 20 cm block per cell. */
struct FVoxelBuildIconRequest
{
    FString Key;
    TSoftObjectPtr<UStaticMesh> Mesh;
    TSoftObjectPtr<UMaterialInterface> Surface;
    TArray<FIntVector> Cells;
    /** Placement pivot offset in cm; the icon applies the same offset so it matches the mesh origin. */
    FVector PivotOffsetCm=FVector::ZeroVector;
};

/**
 * Drawer thumbnails for the building panel.
 *
 * Same recipe as the workbench preview (Docs/UI/gunsmith-preview-quality-20260913.md): a preview scene
 * with the shared studio environment, an orthographic colour pass resolved through the existing
 * M_WeaponPreviewResolved UI material, and a second unlit coverage pass for the alpha. Every icon uses
 * one camera direction and one framing rule (largest bounding-box edge fills the same fraction of the
 * frame), so all cards read at the same size.
 */
UCLASS()
class FPSGAME_API UVoxelBuildIcons : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual void Deinitialize() override;
    virtual void Tick(float DeltaTime) override;
    virtual bool IsTickable() const override {return !Queue.IsEmpty();}
    virtual TStatId GetStatId() const override {RETURN_QUICK_DECLARE_CYCLE_STAT(UVoxelBuildIcons,STATGROUP_Tickables);}
    virtual UWorld* GetTickableGameObjectWorld() const override {return GetWorld();}
    /** Queue one thumbnail; repeated requests for the same key are ignored. */
    void Request(const FVoxelBuildIconRequest& Request);
    /** Ready-to-draw UI material for a card image, or null while its job is still queued. */
    UMaterialInterface* Find(const FString& Key) const;
    /**
     * 抽屉当前显示的缩略图键。这些键不参与 LRU 淘汰，所以展开多栏材质时不会把先出图的
     * 木制条目回收掉（2026-09-17：三栏全展开需要 18 张图，旧上限 16 会淘汰最早的两张）。
     * 重建卡片时整体替换；不再显示的键随下一次淘汰回收。
     */
    void SetVisibleKeys(const TSet<FString>& Keys);
    static FString KeyForShape(FName MaterialId,int32 Shape);
    static FString KeyForPiece(FName PieceId);
private:
    struct FJob {FVoxelBuildIconRequest Request;};
    void EnsureStudio();
    bool Build(const FVoxelBuildIconRequest& Request);
    void ReleaseEntry(const FString& Key);
    UStaticMeshComponent* TakePoolComponent();
    TUniquePtr<FPreviewScene> Studio;
    TArray<FJob> Queue;
    TSet<FString> Pending,Failed;
    TSet<FString> VisibleKeys;
    mutable uint64 Serial=0;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ResolvedMaterial;
    UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> ColorCapture;
    UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> CoverageCapture;
    UPROPERTY(Transient) TObjectPtr<UDirectionalLightComponent> StudioFill;
    UPROPERTY(Transient) TObjectPtr<UTextureCube> StudioSky;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Pool;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTextureRenderTarget2D>> ColorTargets;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTextureRenderTarget2D>> CoverageTargets;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UMaterialInstanceDynamic>> Materials;
    /** Least-recently-used bookkeeping; Find() touches it, so it must stay mutable. */
    mutable TMap<FString,uint64> Uses;
};
