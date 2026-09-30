#include "ForgeInteraction.h"
#include "VoxelBuildPrefabActor.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"

void AForgeInteraction::PresentQuench(float Age,FTransform& Work,FTransform& Tool)
{
    auto Ease=[](float T){return FMath::SmoothStep(0.f,1.f,T);};
    const float Lift=Ease(Age/.55f),Transfer=Ease((Age-.5f)/1.0f);
    const float Dip=Ease((Age-1.5f)/.65f),Raise=Ease((Age-3.95f)/.7f);
    const FQuat Flat(FVector::UpVector,FMath::DegreesToRadians(WorkYaw));
    // Near-vertical immersion: the 30 cm blade tip clears the bottom and stays inside the tub.
    const FVector Above=QuenchSurface+FVector(7.3,0,42);
    Work.SetLocation(FMath::Lerp(FVector(29,22,91)+FVector(0,0,14)*Lift,Above,Transfer)
        +FVector(0,0,-30*Dip+27*Raise));
    Work.SetRotation(FQuat(FVector::YAxisVector,FMath::DegreesToRadians(-76.f*Transfer))*Flat);
    Tool=HammerFrame(Point(Aim),-1);Tool.AddToTranslation(FVector(-12,-6,-12)*Lift);

    // Camera motion precedes contact. Solve arms afterwards against this camera,
    // retaining both authored tool grips and the existing elbow constraints.
    const float Look=Ease((Age-.35f)/1.25f);
    const FVector CameraAt=FMath::Lerp(FVector(29,-43,148),QuenchSurface+FVector(-8,-42,70),Look);
    const FVector Target=FMath::Lerp(FVector(29,22,92),QuenchSurface+FVector(4,5,12),Look);
    Camera->SetRelativeLocation(CameraAt);Camera->SetRelativeRotation((Target-CameraAt).Rotation());
    Camera->SetFieldOfView(FMath::Lerp(67.f,63.f,Look));
}

void AForgeInteraction::UpdateQuenchContact(const FTransform& Work,double Now)
{
    const FVector Tip=Work.TransformPosition(FVector(30,0,.475));
    const FVector Heel=Work.TransformPosition(FVector(-21,0,.475));
    QuenchImmersion=0;
    if(Tip.Z<QuenchSurface.Z&&Heel.Z>QuenchSurface.Z)
    {
        const float T=(QuenchSurface.Z-Tip.Z)/(Heel.Z-Tip.Z);
        const FVector Crossing=FMath::Lerp(Tip,Heel,T);
        if(FVector::DistSquared2D(Crossing,QuenchSurface)<19.5*19.5)
        {
            QuenchImmersion=FMath::Clamp(float((QuenchSurface.Z-Tip.Z)/18.),0.f,1.f);
            SteamOrigin=FVector(Crossing.X,Crossing.Y,QuenchSurface.Z+.8);
            if(QuenchContactAt<0)
            {
                QuenchContactAt=Now;FumeSpawnClock=.1f;
                if(QuenchWaterMaterial)
                {
                    QuenchWaterMaterial->SetScalarParameterValue(TEXT("QuenchTime"),GetWorld()->GetTimeSeconds());
                    const FVector Local=Crossing-QuenchSurface;
                    QuenchWaterMaterial->SetVectorParameterValue(TEXT("QuenchPoint"),FLinearColor(Local.X,Local.Y,0));
                }
            }
        }
    }
    if(QuenchWaterMaterial)QuenchWaterMaterial->SetScalarParameterValue(TEXT("Immersion"),QuenchImmersion);
}

void AForgeInteraction::RestoreQuenchWater()
{
    if(Station.IsValid()&&QuenchWaterMaterial&&QuenchWaterSlot!=INDEX_NONE)
    {
        auto* Body=Station->Body();
        if(Body->GetMaterial(QuenchWaterSlot)==QuenchWaterMaterial)Body->SetMaterial(QuenchWaterSlot,PreviousWaterMaterial);
    }
    QuenchWaterMaterial=nullptr;PreviousWaterMaterial=nullptr;QuenchWaterSlot=INDEX_NONE;
}
