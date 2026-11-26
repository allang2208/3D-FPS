#include "VillageInteriorLighting.h"
#include "../Weapons/Staff/StaffIlluminationProfile.h"
#include "Components/PointLightComponent.h"

namespace
{
constexpr float ShopBrightness = .8f;
}

FLinearColor UVillageInteriorLighting::GlowTint()
{
    return FLinearColor(1.f, .70f, .32f);
}

float UVillageInteriorLighting::FullLumens()
{
    return ShopBrightness * UStaffIlluminationProfile::FullLumens;
}

float UVillageInteriorLighting::GetEmissionStrength()
{
    return ShopBrightness * UStaffIlluminationProfile::EmissionStrength;
}

void UVillageInteriorLighting::Configure(UPointLightComponent* Light, float Level)
{
    if (!Light) return;
    UStaffIlluminationProfile::ApplyToPointLight(Light, ShopBrightness * FMath::Clamp(Level, 0.f, 1.f));
    Light->SetLightColor(GlowTint());
}

void UVillageInteriorLighting::ApplyAppearance(UPointLightComponent* Light)
{
    if (!Light) return;
    Light->SetLightColor(GlowTint());
    Light->SetIntensity(FullLumens());
}
