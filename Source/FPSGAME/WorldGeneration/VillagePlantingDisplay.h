#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TemperateHillsWorld.h"
#include "VillagePlantingDisplay.generated.h"
class ATemperateHillsWorld;
class UPrimitiveComponent;
namespace HillsVegetation {struct FNeighborhood;}

/** Small authored village palette, with its own skyline cull distance. */
UCLASS(Transient)
class AVillagePlantingDisplay : public AActor
{
    GENERATED_BODY()
public:
    AVillagePlantingDisplay();
    void Initialize(ATemperateHillsWorld* Source);
    virtual void Tick(float Delta) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    int32 PlantCount=0;
private:
    UFUNCTION() void SourceDestroyed(AActor* Source);
    TWeakObjectPtr<ATemperateHillsWorld> Hills;
    TSharedPtr<HillsVegetation::FNeighborhood> Neighborhood;
    FBox Area=FBox(ForceInit),Cell=FBox(ForceInit);
    double NextY=0.;
    bool RelationshipsReady=false;
    TArray<FTemperatePlacement> Pending;
    int32 PendingIndex=0;
    // Registered instance components are retained by this actor. Keep trees
    // spatially grouped so a close tree does not pin distant rows to near detail.
    TMap<TPair<FIntPoint,FSoftObjectPath>,TObjectPtr<UPrimitiveComponent>> Groups;
};
