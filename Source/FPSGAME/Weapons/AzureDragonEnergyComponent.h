#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AzureDragonEnergyComponent.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

/** Owner-only camera-space energy vessel. Gameplay owns charge; this component presents it. */
UCLASS()
class FPSGAME_API UAzureDragonEnergyComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UAzureDragonEnergyComponent();
    void Configure(bool Enabled);
    void SetEnergy(float NormalizedEnergy,bool Summoned=false,bool ContactPulse=true);
    void ClearEnergy();
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RequestAssets();
    void CreateDisplay();
    void HideDisplay();
    bool bEnabled=false,bRequested=false,bHaveYaw=false;
    float TargetEnergy=0.f,DisplayEnergy=0.f,Age=0.f,EntryAge=0.f;
    float HitAge=10.f,FlareAge=10.f,LastYaw=0.f,Sway=0.f;
    TSharedPtr<FStreamableHandle> AssetLoad;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ColumnMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> FlameMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ColumnMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> FlameMaterial;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Column;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Flame;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ColumnMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FlameMID;
    // V6 adds a modeled dragon crest and an independently orbiting glyph helix.
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> CrestMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> HelixMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> CrestMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> HelixMaterial;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Crest;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Helix;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CrestMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HelixMID;
};
