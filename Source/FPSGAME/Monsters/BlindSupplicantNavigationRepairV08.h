#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlindSupplicantNavigationRepairV08.generated.h"

/** Background-only production of the M07 agent's saved navigation tiles. */
UCLASS()
class FPSGAME_API UBlindSupplicantNavigationRepairV08 : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Monsters|M07|Authoring")
    static FString BuildAndSaveMapNavigation(const FString& MapPackageName);
};
