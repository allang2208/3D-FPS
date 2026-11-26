#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HillsNightPortal.generated.h"

struct FStreamableHandle;
UCLASS()
class FPSGAME_API AHillsNightPortal : public AActor
{
    GENERATED_BODY()
public:
    AHillsNightPortal();
    static void AddAssetPaths(TArray<FSoftObjectPath>& Paths);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void Tick(float Delta) override;
    UPROPERTY(ReplicatedUsing=OnRep_Presentation) double OpenedAt=0.;
    UPROPERTY(ReplicatedUsing=OnRep_Presentation) double ClosedAt=-1.;
    void ClosePortal();
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Frame;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> Curtain;
    UPROPERTY() TObjectPtr<class UStaticMeshComponent> SkyBeam;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> Energy;
    UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> BeamEnergy;
    UPROPERTY() TObjectPtr<class UPointLightComponent> Glow;
    UFUNCTION() void OnRep_Presentation();
    void AssetsReady();
    TSharedPtr<FStreamableHandle> AssetLoad;
    double ServerTime() const;
};
