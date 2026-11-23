#pragma once

#include "Components/ActorComponent.h"
#include "VillageExteriorDetail.generated.h"

class ULevel;
class UStaticMesh;
class UMaterialInterface;
class UStaticMeshComponent;
struct FStreamableHandle;

UCLASS()
class UVillageExteriorDetail : public UActorComponent
{
    GENERATED_BODY()
public:
    UVillageExteriorDetail();
    static void BindLevel(ULevel& Level);
    static void BindGateTimber(UStaticMeshComponent& Left, UStaticMeshComponent& Right);
protected:
    virtual void OnRegister() override;
    virtual void OnUnregister() override;
    virtual void TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    TArray<TWeakObjectPtr<UStaticMeshComponent>> Parts;
    struct FSourceAppearance
    {
        TWeakObjectPtr<UStaticMesh> Mesh;
        TArray<TWeakObjectPtr<UMaterialInterface>> Materials;
        TArray<FTransform> Placements;
    };
    TArray<FSourceAppearance> Appearances;
    TArray<bool> DepthPass;
    FSoftObjectPath Asset;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Proxy;
    TSharedPtr<FStreamableHandle> Loading;
    FVector LocalCenter = FVector::ZeroVector;
    double Radius = 0.;
    TAtomic<bool> bSourcesChanged{true};
    bool bWasEligible = false;
    bool bSourcesMatch = true;
    bool bShowingProxy = false;
    bool SourcesStillMatch() const;
    static void BindPreparedLevel(ULevel& Level);
    void PrepareProxy();
    void Display(bool bUseProxy);
};
