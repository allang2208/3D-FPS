#pragma once

#include "Components/ActorComponent.h"
#include "UObject/SoftObjectPath.h"
#include "VillagePortcullisHoist.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMesh;

/** Cosmetic return chain and counterweights driven by the owning gate's visual lift. */
UCLASS()
class UVillagePortcullisHoist : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillagePortcullisHoist();
    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);
    static bool AssetsReady();
    void Initialize(bool bWest);
    void FollowGate(float Height, bool bIntact);
    void Release(float ImpactLift);
    void Reattach(float Lift);
    virtual void TickComponent(float Delta, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
private:
    UInstancedStaticMeshComponent* CreateBatch(UStaticMesh* Mesh);
    void Draw(float Lift);
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Chains;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Wheels;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Weights;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Bearings;
    TArray<FTransform> LinkPoses;
    TArray<FTransform> WheelPoses;
    TArray<FTransform> WeightPoses;
    int32 LinksPerRun = 0;
    float LinkPitch = 0.f;
    float EyeX = 0.f;
    float EyeZ = 0.f;
    float AxleZ = 0.f;
    float Travel = 0.f;
    float LastLift = -1.f;
    float ReleaseVelocity = 0.f;
    bool bDetached = false;
    bool bObservedBreach = false;
};
