#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VoxelBuildComponent.generated.h"

class AVoxelBuildWorld;
class UVoxelBuildPalette;
class UVoxelBuildWidget;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
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
    UFUNCTION(BlueprintCallable,Category="Building") void SelectMaterial(FName Id);
    UFUNCTION(BlueprintPure,Category="Building") bool IsBuilding() const { return bActive; }
    bool HandleInput(const FInputKeyEventArgs& Event,bool bMenuOpen);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<UVoxelBuildPalette> Palette;
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> BuildWorld;
    UPROPERTY() TObjectPtr<UVoxelBuildWidget> Widget;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Preview;
    UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> PreviewMID;
    FName SelectedMaterial=TEXT("wood");
    FHitResult Hit;
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
    bool bRotate=false;
    bool bUndoModifier=false;
    int32 Brush=0;
    void TryInitializeWorld();
    void UpdateTarget();
    void UpdateWidget();
    FIntVector BrushSize() const;
    void FillBrush(FIntVector Base,TArray<FIntVector>& Result) const;
};
