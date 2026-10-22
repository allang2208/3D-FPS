#include "FPSMeteorStrike.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

void AFPSMeteorStrike::PrepareScorch()
{
    if(!ScorchMaterial||ScorchDecal||bWaterContact)return;
    ScorchDecal=NewObject<UDecalComponent>(this,TEXT("MeteorScorch"));
    AddInstanceComponent(ScorchDecal);
    const float Radius=FMath::Clamp(CastSnapshot.Radius*.48f,180.f,420.f);
    ScorchDecal->DecalSize=FVector(20.f,Radius,Radius);
    ScorchDecal->SetDecalMaterial(ScorchMaterial);
    ScorchDecal->SetWorldLocation(Destination+Normal*3.f);
    ScorchDecal->SetWorldRotation(FRotationMatrix::MakeFromX(-Normal).Rotator());
    ScorchDecal->SetFadeScreenSize(.003f);
    ScorchDecal->RegisterComponent();
    ScorchMID=ScorchDecal->CreateDynamicMaterialInstance();
    if(ScorchMID)
    {
        ScorchMID->SetVectorParameterValue(TEXT("ImpactCenter"),FLinearColor(Destination));
        ScorchMID->SetVectorParameterValue(TEXT("SurfaceNormal"),FLinearColor(Normal));
        ScorchMID->SetScalarParameterValue(TEXT("ImpactSeed"),float(FMath::Fmod(FMath::Max(0.,NetStartedAt)*.1237,1.)));
        ScorchMID->SetScalarParameterValue(TEXT("ImpactHeat"),FMath::Exp(-FMath::Max(0.f,Age-CastSnapshot.FallSeconds)*1.7f));
    }
}

void AFPSMeteorStrike::UpdateImpactPresentation()
{
    if(bImpactBreakPending&&LavaAge>=.035f)
    {
        bImpactBreakPending=false;Rock->SetVisibility(false);BreakRock();
    }
    if(ScorchMID)
    {
        ScorchMID->SetScalarParameterValue(TEXT("ImpactHeat"),LavaAge<3.f?FMath::Exp(-LavaAge*1.7f):0.f);
        ScorchMID->SetScalarParameterValue(TEXT("ScarFade"),FMath::Clamp((CastSnapshot.Duration-LavaAge)/.75f,0.f,1.f));
    }
}
