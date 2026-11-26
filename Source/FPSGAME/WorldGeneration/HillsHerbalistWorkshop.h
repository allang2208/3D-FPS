#pragma once

#include "../Building/VoxelBuildPrefabActor.h"
#include "HillsHerbalistWorkshop.generated.h"

class ATemperateHillsWorld;
class AVillageHerbalist;

/** A level-authored potion workbench and the shop assemblies that share its restoration. */
UCLASS()
class FPSGAME_API AHillsHerbalistWorkshop : public AVoxelBuildPrefabActor
{
    GENERATED_BODY()
public:
    AHillsHerbalistWorkshop();

    UPROPERTY(EditAnywhere, Category="Village") TObjectPtr<UStaticMesh> StationMesh;
    UPROPERTY(EditAnywhere, Category="Village") TArray<TObjectPtr<AActor>> ShopAssemblies;
    /** Construction footprint in the authored workbench's local space, in cm. */
    UPROPERTY(EditAnywhere, Category="Village") FVector RepairAreaCenter = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Village") FVector RepairAreaHalfExtent = FVector(450., 450., 260.);

    bool CanRepair(FText& FailureReason) const;
    void ApplyVillageState();
    virtual bool IsSceneStation() const override { return true; }
    virtual bool IsSceneStationAvailable() const override;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnRep_Configuration() override;
    virtual void OnRep_Owner() override;

private:
    void BindVillage();
    void RefreshStation();
    void UpdateResident(bool bRepaired);
    FIntVector StationCell() const;
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AVillageHerbalist> Resident;
    FTimerHandle BindTimer;
};
