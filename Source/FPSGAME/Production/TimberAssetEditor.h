#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "TimberAssetEditor.generated.h"

class UMaterialExpression;

/** Native authoring bridge for material inputs hidden from UE Python. */
UCLASS()
class FPSGAME_API UTimberAssetEditor : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Timber|Authoring")
    static bool PrepareFallAttributeInputs(UMaterialExpression* Expression);
};
