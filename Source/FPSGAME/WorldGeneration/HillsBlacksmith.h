#pragma once
#include "CoreMinimal.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "HillsBlacksmith.generated.h"

class ATemperateHillsWorld;
class AVillageBlacksmithResident;
class ASmithYardFurnace;
class AStaticMeshActor;
class UStaticMesh;
class UNiagaraSystem;

/** Authored village shop. The hills save owns restoration; existing forge gameplay owns crafting. */
UCLASS()
class FPSGAME_API AHillsBlacksmith : public AVoxelBuildPrefabActor
{
    GENERATED_BODY()
public:
    AHillsBlacksmith();
    UPROPERTY(EditAnywhere,Category="Village") TObjectPtr<UStaticMesh> StationMesh;
    UPROPERTY(EditAnywhere,Category="Village") TObjectPtr<UNiagaraSystem> InteriorTorchFlame;
    // Separate scenery actors keep house-wall hits out of the forge interaction trace.
    UPROPERTY(EditAnywhere,Category="Village") TArray<TObjectPtr<AActor>> ShopAssemblies;
    UPROPERTY(EditAnywhere,Category="Village") FVector RepairAreaCenter=FVector::ZeroVector;
    UPROPERTY(EditAnywhere,Category="Village") FVector RepairAreaHalfExtent=FVector(370,370,500);
    void ApplyVillageState();
    bool RepairAreaOccupied() const;
    virtual bool IsSceneStation() const override { return true; }
    virtual bool IsSceneStationAvailable() const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnRep_Owner() override;
    virtual void OnRep_Configuration() override;
private:
    void BindVillage();
    void RegisterStation();
    void UpdateResident(bool bRepaired);
    void UpdateSmeltingYard(bool bRepaired);
    TWeakObjectPtr<ASmithYardFurnace> YardFurnaces[2];
    TWeakObjectPtr<AStaticMeshActor> YardShelter;
    TWeakObjectPtr<AVillageBlacksmithResident> Resident;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    FTimerHandle BindTimer;
};
