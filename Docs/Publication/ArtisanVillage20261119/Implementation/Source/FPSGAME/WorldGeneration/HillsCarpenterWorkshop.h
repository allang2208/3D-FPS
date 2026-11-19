#pragma once

#include "../Building/VoxelBuildPrefabActor.h"
#include "HillsCarpenterWorkshop.generated.h"

class ATemperateHillsWorld;
class AVillageCarpenterResident;

/** The authored workbench is the interaction target. The house and yard are separate scenery. */
UCLASS()
class FPSGAME_API AHillsCarpenterWorkshop : public AVoxelBuildPrefabActor
{
    GENERATED_BODY()
public:
    AHillsCarpenterWorkshop();
    UPROPERTY(EditAnywhere, Category="Village") TObjectPtr<UStaticMesh> StationMesh;
    UPROPERTY(EditAnywhere, Category="Village") TArray<TObjectPtr<AActor>> ShopAssemblies;
    UPROPERTY(EditAnywhere, Category="Village") FVector RepairAreaCenter = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, Category="Village") FVector RepairAreaHalfExtent = FVector(450., 550., 500.);
    /** Floor-level standing pose in the workbench's local space. */
    UPROPERTY(EditAnywhere, Category="Village") FTransform ResidentPose;

    void ApplyVillageState();
    bool RepairAreaOccupied() const;
    virtual bool IsSceneStationAvailable() const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnRep_Owner() override;
    virtual void OnRep_Configuration() override;
private:
    void BindVillage();
    void RefreshRegistration();
    void UpdateResident(bool bRepaired);
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TWeakObjectPtr<AVillageCarpenterResident> Resident;
    FTimerHandle BindTimer;
};
