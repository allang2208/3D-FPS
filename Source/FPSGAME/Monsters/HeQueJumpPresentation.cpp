#include "HeQueMonster.h"
#include "HeQueJumpTiming.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

void AHeQueMonster::OnRep_JumpSlam()
{
    RefreshPoseTick();if(GetNetMode()==NM_DedicatedServer)return;
    const bool Active=IsJumpSlamming();
    if(PresentedJumpSerial!=JumpSlam.Serial)
    {
        PresentedJumpSerial=JumpSlam.Serial;JumpVoice->Stop();
        USoundBase* Voice=JumpSlam.Phase==EHeQueJumpPhase::Charge?JumpChargeSound.Get():
            (JumpSlam.Phase==EHeQueJumpPhase::Rising||JumpSlam.Phase==EHeQueJumpPhase::Falling)?JumpAirSound.Get():nullptr;
        if(Active&&Voice)
        {
            JumpVoice->SetSound(Voice);JumpVoice->AttenuationSettings=JumpAttenuation;
            JumpVoice->Play(JumpAge()+(JumpSlam.Phase==EHeQueJumpPhase::Falling?.5f:0.f));
        }
        if(Active&&JumpSlam.Phase==EHeQueJumpPhase::Recovery)
        {
            JumpWave->SetStaticMesh(JumpWaveMesh);JumpImpact->SetStaticMesh(JumpImpactMesh);
            if(!JumpWaveMID&&JumpWaveMaterial)JumpWaveMID=JumpWave->CreateDynamicMaterialInstance(0,JumpWaveMaterial);
            if(!JumpImpactMID&&JumpImpactMaterial)JumpImpactMID=JumpImpact->CreateDynamicMaterialInstance(0,JumpImpactMaterial);
            if(JumpImpactSound&&JumpAge()<HeQueJumpTiming::Recovery)
            {
                JumpImpactVoice->SetWorldLocation(JumpSlam.ImpactPoint);JumpImpactVoice->SetSound(JumpImpactSound);
                JumpImpactVoice->AttenuationSettings=JumpAttenuation;JumpImpactVoice->Play(JumpAge());
            }
        }
    }
    if(!Active){JumpWave->SetVisibility(false);JumpImpact->SetVisibility(false);JumpVoice->Stop();JumpImpactVoice->Stop();}
}
void AHeQueMonster::PresentJumpSlam(float Age)
{
    if(JumpSlam.Phase!=EHeQueJumpPhase::Recovery||Dead())return;
    const FVector Normal=JumpSlam.ImpactNormal,Point=JumpSlam.ImpactPoint+Normal*3.f;
    const FRotator Orientation=FRotationMatrix::MakeFromZ(Normal).Rotator();
    const float Radius=FMath::Max(5.f,JumpWaveRadius*FMath::Clamp(Age/HeQueJumpTiming::WaveSeconds,0.f,1.f));
    const float Alpha=1.f-FMath::SmoothStep(HeQueJumpTiming::WaveSeconds,HeQueJumpTiming::WaveSeconds+HeQueJumpTiming::WaveFade,Age);
    JumpWave->SetVisibility(JumpWaveMID&&Alpha>.001f);
    if(JumpWaveMID&&Alpha>.001f)
    {
        JumpWave->SetWorldLocationAndRotation(Point,Orientation);JumpWave->SetWorldScale3D(FVector(Radius/100.f,Radius/100.f,1.f));
        JumpWaveMID->SetScalarParameterValue(TEXT("WaveRadiusCm"),Radius);JumpWaveMID->SetScalarParameterValue(TEXT("PulseAlpha"),Alpha);
        JumpWaveMID->SetScalarParameterValue(TEXT("PulsePhase"),Age);
        JumpWaveMID->SetVectorParameterValue(TEXT("WaveOrigin"),FLinearColor(Point.X,Point.Y,Point.Z,0));
        JumpWaveMID->SetVectorParameterValue(TEXT("GroundNormal"),FLinearColor(Normal.X,Normal.Y,Normal.Z,0));
    }
    const float Burst=1.f-FMath::SmoothStep(.18f,.85f,Age);
    JumpImpact->SetVisibility(JumpImpactMID&&Burst>.001f);
    if(JumpImpactMID&&Burst>.001f)
    {
        // Fast contact displacement, followed by a slower dusty settling tail.
        const float Size=Age<.12f?FMath::Lerp(1.2f,2.7f,FMath::SmoothStep(0.f,.12f,Age)):
            FMath::Lerp(2.7f,3.3f,FMath::SmoothStep(.12f,.60f,Age));
        JumpImpact->SetWorldLocationAndRotation(Point,Orientation);JumpImpact->SetWorldScale3D(FVector(Size,Size,1.f));
        JumpImpactMID->SetScalarParameterValue(TEXT("PulseAlpha"),Burst);JumpImpactMID->SetScalarParameterValue(TEXT("PulsePhase"),Age);
    }
}
