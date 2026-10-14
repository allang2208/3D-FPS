#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "MonsterAPSMigration.generated.h"

UCLASS()
class FPSGAME_API UMonsterAPSMigration : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Commandlet-only: replace each APS-configured agent's saved nav actor, rebuild and save the map. */
    UFUNCTION(BlueprintCallable, Category="Monsters|Navigation")
    static FString MigrateNavigationToAPS(const FString& MapPackageName);
};
