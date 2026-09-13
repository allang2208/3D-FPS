#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "ProductionTreeCutProfile.generated.h"

/** The authored stump rim in the source tree's local centimetres. */
UCLASS()
class FPSGAME_API UProductionTreeCutProfile : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FVector2D> Rim;
};
