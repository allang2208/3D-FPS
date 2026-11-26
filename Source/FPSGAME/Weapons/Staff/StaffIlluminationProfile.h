#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "StaffIlluminationProfile.generated.h"

class UPointLightComponent;

/** The apprentice staff's G light, also used by authored village interiors. */
UCLASS()
class FPSGAME_API UStaffIlluminationProfile : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    static constexpr float FullLumens = 1000.f;
    static constexpr float RadiusCm = 800.f;
    static constexpr float EmissionStrength = 3.f;
    UFUNCTION(BlueprintPure, Category="Lighting|Staff")
    static FLinearColor GlowTint();
    UFUNCTION(BlueprintPure, Category="Lighting|Staff")
    static float GetEmissionStrength() { return EmissionStrength; }
    UFUNCTION(BlueprintCallable, Category="Lighting|Staff")
    static void ApplyToPointLight(UPointLightComponent* Light, float Level = 1.f);
};
