#include "VillageInteriorLighting.h"
#include "../Weapons/Staff/StaffIlluminationProfile.h"
#include "Components/PointLightComponent.h"
#include "HAL/IConsoleManager.h"

namespace
{
constexpr float ShopBrightness = .8f;
int32 GInteriorLightShadows = 0;
int32 GInteriorLightVolumetric = 0;

FAutoConsoleVariableRef CVarInteriorLightShadows(
    TEXT("fps.Hills.InteriorLightShadows"),
    GInteriorLightShadows,
    TEXT("0 = disable VSM shadow maps on village interior point lights (default), 1 = enable."),
    ECVF_Default);

FAutoConsoleVariableRef CVarInteriorLightVolumetric(
    TEXT("fps.Hills.InteriorLightVolumetric"),
    GInteriorLightVolumetric,
    TEXT("0 = disable volumetric fog scattering on village interior point lights (default), 1 = enable."),
    ECVF_Default);
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
    Light->SetCastShadows(GInteriorLightShadows != 0);
    Light->SetVolumetricScatteringIntensity(GInteriorLightVolumetric != 0 ? .035f : 0.f);
}

void UVillageInteriorLighting::ApplyVolumetricBudget(UPointLightComponent* Light)
{
    if (!Light) return;
    Light->SetVolumetricScatteringIntensity(GInteriorLightVolumetric != 0 ? .15f : 0.f);
}

void UVillageInteriorLighting::ApplyAppearance(UPointLightComponent* Light)
{
    if (!Light) return;
    Light->SetLightColor(GlowTint());
    Light->SetIntensity(FullLumens());
    Light->SetCastShadows(GInteriorLightShadows != 0);
    Light->SetVolumetricScatteringIntensity(GInteriorLightVolumetric != 0 ? .035f : 0.f);
}
