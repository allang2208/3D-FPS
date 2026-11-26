#pragma once

#include "../Building/VoxelBuildPrefabActor.h"
#include "Engine/StaticMeshActor.h"
#include "SmithYardFurnace.generated.h"

UCLASS()
class ASmithYardFurnace : public AVoxelBuildPrefabActor
{
    GENERATED_BODY()
public:
    ASmithYardFurnace();
    void OpenBay(int32 Bay);
    virtual bool IsSceneStation() const override { return true; }
    virtual bool IsSceneStationAvailable() const override;
    virtual void OnRep_Owner() override;
    virtual void OnRep_Configuration() override;
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RegisterBay();
};

UCLASS()
class ASmithYardShelter : public AStaticMeshActor
{
    GENERATED_BODY()
public:
    ASmithYardShelter();
};
