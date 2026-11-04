#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "TacticalHatchetImportLibrary.generated.h"

class UStaticMesh;

/** Background authoring step for the user-supplied hatchet; no gameplay or audit execution. */
UCLASS()
class FPSGAME_API UTacticalHatchetImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Weapon Authoring")
    static bool FinalizeMesh(UStaticMesh* Mesh);
};
