#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CastingToolRackComponent.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
struct FStreamableHandle;

/** Four cosmetic pendulums, registered by the placed casting station. */
UCLASS()
class FPSGAME_API UCastingToolRackComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UCastingToolRackComponent();
    void Configure(UStaticMeshComponent* Station);
    virtual void TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick) override;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
private:
    void AssetsReady();
    void ResetMotion();
    UPROPERTY() TArray<TSoftObjectPtr<UStaticMesh>> RackAssets;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> HangingTools;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> OriginalMesh;
    TWeakObjectPtr<UStaticMeshComponent> Body;
    TSharedPtr<FStreamableHandle> AssetLoad;
    FVector2D Angles[4]={},Speeds[4]={};
    FVector LocalWind=FVector::ZeroVector;
    FTransform LastMount=FTransform::Identity;
    float WindClock=0;
    bool bMotionReady=false;
};
