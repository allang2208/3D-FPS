#include "StaffIlluminationProfile.h"
#include "Components/PointLightComponent.h"

FLinearColor UStaffIlluminationProfile::GlowTint()
{
    return FLinearColor(1.f, .94f, .82f);
}

void UStaffIlluminationProfile::ApplyToPointLight(UPointLightComponent* Light, float Level)
{
    if (!Light) return;
    Light->SetIntensityUnits(ELightUnits::Lumens);
    Light->SetInverseExposureBlend(1.f);
    Light->SetAttenuationRadius(RadiusCm);
    Light->SetSourceRadius(3.f);
    Light->SetSoftSourceRadius(5.f);
    Light->SetSourceLength(0.f);
    Light->SetSpecularScale(1.f);
    Light->SetCastShadows(true);
    Light->SetVolumetricScatteringIntensity(.15f);
    Light->SetUseTemperature(false);
    Light->SetLightColor(GlowTint());
    Light->SetIntensity(FullLumens * FMath::Clamp(Level, 0.f, 1.f));
}
