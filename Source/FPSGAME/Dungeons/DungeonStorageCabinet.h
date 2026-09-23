#pragma once
#include "../UI/ColdSteelWarehouseChest.h"
#include "DungeonStorageCabinet.generated.h"
class UStaticMeshComponent;

/** The authored red cabinet uses the existing shared warehouse UI and save model. */
UCLASS()
class FPSGAME_API ADungeonStorageCabinet : public AColdSteelWarehouseChest
{
    GENERATED_BODY()
public:
    ADungeonStorageCabinet();
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Dungeon") TObjectPtr<UStaticMeshComponent> CabinetMesh;
};
