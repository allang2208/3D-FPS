#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "BlindSupplicantNavigationAuthoring.generated.h"

class UWorld;

/** Offline navigation production; never starts a gameplay world. */
UCLASS()
class FPSGAME_API UBlindSupplicantNavigationAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Monsters|M07|Authoring")
    static FString BuildAndSaveNavigation(UWorld* World);

    /** Headless map load/build/save without LevelEditorSubsystem or GEditor. */
    UFUNCTION(BlueprintCallable, Category="Monsters|M07|Authoring")
    static FString BuildAndSaveMapNavigation(const FString& MapPackageName);
};
