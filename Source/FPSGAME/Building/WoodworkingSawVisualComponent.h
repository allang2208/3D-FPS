#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "WoodworkingSawVisualComponent.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
struct FStreamableHandle;

/** Local cosmetic blade; cutting and rewards remain owned by UWoodworkingSystem. */
UCLASS()
class FPSGAME_API UWoodworkingSawVisualComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UWoodworkingSawVisualComponent();
    void Configure(UStaticMeshComponent* Station);
    void SetPowered(bool bInPowered,bool Adjusting=false);
    virtual void TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick) override;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
private:
    void AssetsReady();
    TWeakObjectPtr<UStaticMeshComponent> Body;
    TSharedPtr<FStreamableHandle> AssetLoad;
    double Angle=0;
    bool bPowered=false,bAdjusting=false;
    UPROPERTY() TSoftObjectPtr<UStaticMesh> BodyAsset;
    UPROPERTY() TSoftObjectPtr<UStaticMesh> BladeAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> OriginalMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
};
