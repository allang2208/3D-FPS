#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "VillageInteriorLighting.generated.h"

class UPointLightComponent;

UCLASS()
class FPSGAME_API UVillageInteriorLighting : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintPure, Category="Lighting|Village Interior")
    static FLinearColor GlowTint();

    UFUNCTION(BlueprintPure, Category="Lighting|Village Interior")
    static float GetEmissionStrength();

    UFUNCTION(BlueprintCallable, Category="Lighting|Village Interior")
    static void Configure(UPointLightComponent* Light, float Level = 1.f);

    static float FullLumens();
    // Saved fixtures already carry their radius, exposure compensation and shadow settings.
    static void ApplyAppearance(UPointLightComponent* Light);
};
