#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GrassDeformTestField.generated.h"

class UHierarchicalInstancedStaticMeshComponent;

/** Authored tall-grass instances, baked into the test map; no runtime scatter or tick. */
UCLASS()
class FPSGAME_API AGrassDeformTestField : public AActor
{
    GENERATED_BODY()
public:
    AGrassDeformTestField();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grass Test")
    TObjectPtr<UHierarchicalInstancedStaticMeshComponent> TallGrassA;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Grass Test")
    TObjectPtr<UHierarchicalInstancedStaticMeshComponent> TallGrassB;
};
