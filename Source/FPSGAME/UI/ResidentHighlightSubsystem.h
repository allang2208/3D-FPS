#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "ResidentHighlightSubsystem.generated.h"

class APlayerController;
class ISceneViewExtension;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UMeshComponent;
class FSceneView;
enum class ERendererStencilMask : uint8;
struct FStreamableHandle;

/** Local camera focus on the resident's actual animated and clothed geometry. */
UCLASS()
class UResidentHighlightSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    void SetFocus(APlayerController* Player, AActor* Target);
    static void RegisterShopkeeper(AActor& Resident);
    virtual void Deinitialize() override;

private:
    struct FMeshState
    {
        TWeakObjectPtr<UMeshComponent> Mesh;
        int32 Stencil;
        ERendererStencilMask Mask;
    };
    struct FResident
    {
        TWeakObjectPtr<AActor> Actor;
        TArray<FMeshState> Meshes;
        int32 Viewers = 0;
        bool bShopLighting = false;
        int32 Stencil = INDEX_NONE;
    };
    TArray<FResident> Residents;
    TMap<TWeakObjectPtr<APlayerController>, int32> Viewers;
    TSharedPtr<ISceneViewExtension, ESPMode::ThreadSafe> HairExtension;
    FDelegateHandle FocusViewHandle;
    TSharedPtr<FStreamableHandle> Load;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FocusParameters;
    TArray<TWeakObjectPtr<AActor>> Shopkeepers;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ShopResponse;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ShopParameters;
    uint32 LastShopMask = 0;
    TSharedPtr<FStreamableHandle> ShopLoad;
    FTimerHandle ShopTimer;
    FDelegateHandle ShopViewHandle;
    void UpdateShopkeepers();
    void ApplyShopResponse(FVector Eye, FSceneView* View);
    void ShopMaterialLoaded();
    int32 FindOrAddResident(AActor* Actor);
    void RefreshMeshes(FResident& Entry);
    void UpdateStencil(int32 Slot);
    void Release(int32 Slot);
    void RemoveViewer(APlayerController* Player);
    void ApplyFocus(FVector Eye, FSceneView* View);
    void MaterialLoaded();
    UFUNCTION() void PlayerEnded(AActor* Actor, EEndPlayReason::Type Reason);
};
