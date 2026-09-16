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
    /** Number row 1/2/3-9/0 in the drawer: pick and return to building. */
    bool HandlePanelKey(const FKey& Key);
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
    bool bPrefabValid=false;
    bool bPrefabAimHit=false;
    void TryInitializeWorld();
    void UpdateTarget();
    const FVoxelBuildPrefab* SelectedPrefab() const;
    void UpdatePrefabTarget(bool bHit);
    void UpdatePrefabPreview();
    void ValidatePlacement();
    void UpdatePreview(FIntVector Size);
    void UpdateWidget();
    void PushPanelContent();
    void PlacePrefab();
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
