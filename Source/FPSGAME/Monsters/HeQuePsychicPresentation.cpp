#include "HeQueMonster.h"
#include "HeQuePsychicTiming.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

void AHeQueMonster::OnRep_Psychic()
{
    RefreshPoseTick();if(GetNetMode()==NM_DedicatedServer)return;
    const bool Active=Psychic.Active&&!Dead();
    if(Active)
    {
        PsychicWaveMIDs.SetNum(3);
        for(int32 I=0;I<3;++I)
        {
            PsychicWaves[I]->SetStaticMesh(PsychicWaveMesh);
            if(!PsychicWaveMIDs[I]&&PsychicWaveMaterial)PsychicWaveMIDs[I]=PsychicWaves[I]->CreateDynamicMaterialInstance(0,PsychicWaveMaterial);
        }
        if(!PsychicCoreMID&&PsychicCoreMaterial)PsychicCoreMID=UMaterialInstanceDynamic::Create(PsychicCoreMaterial,this);
        if(PsychicCoreMID&&GetMesh()->GetOverlayMaterial(true,PsychicBodyMaterialSlot)!=PsychicCoreMID)
        {
            PreviousPsychicOverlay=GetMesh()->GetOverlayMaterial(true,PsychicBodyMaterialSlot);
            GetMesh()->SetOverlayMaterial(PsychicCoreMID,true,PsychicBodyMaterialSlot);
        }
    }
    if(PresentedPsychicSerial!=Psychic.Serial)
    {
        PresentedPsychicSerial=Psychic.Serial;PsychicVoice->Stop();
        if(Active&&PsychicSound&&PsychicAge()<HeQuePsychicTiming::End)
        {PsychicVoice->SetSound(PsychicSound);PsychicVoice->AttenuationSettings=PsychicAttenuation;PsychicVoice->Play(PsychicAge());}
    }
    if(!Active)
    {
        PsychicVoice->Stop();
        for(const auto& Wave:PsychicWaves)Wave->SetVisibility(false);
        if(PsychicCoreMID&&GetMesh()->GetOverlayMaterial(true,PsychicBodyMaterialSlot)==PsychicCoreMID)
            GetMesh()->SetOverlayMaterial(PreviousPsychicOverlay,true,PsychicBodyMaterialSlot);
        PreviousPsychicOverlay=nullptr;
    }
}
void AHeQueMonster::PresentPsychic(float Age)
{
    static const FName AlphaName(TEXT("PulseAlpha")),PhaseName(TEXT("PulsePhase"));
    const FVector Core=PsychicCore();
    float Beat=0.f;
    for(float Release:HeQuePsychicTiming::Releases)
        Beat+=FMath::SmoothStep(Release,Release+.045f,Age)*(1.f-FMath::SmoothStep(Release+.08f,Release+.30f,Age));
    const float Charge=FMath::SmoothStep(.15f,1.4f,Age)*(1.f-FMath::SmoothStep(3.f,4.6f,Age));
    if(PsychicCoreMID)
    {
        PsychicCoreMID->SetScalarParameterValue(AlphaName,FMath::Clamp(Charge*.32f+Beat,0.f,1.f));
        PsychicCoreMID->SetScalarParameterValue(PhaseName,Age);
    }
    for(int32 I=0;I<3;++I)
    {
        const float Flight=Age-HeQuePsychicTiming::Releases[I];
        const bool Visible=Flight>=0.f&&Flight<HeQuePsychicTiming::WaveSeconds+HeQuePsychicTiming::FadeSeconds;
        auto* Wave=PsychicWaves[I].Get();Wave->SetVisibility(Visible&&PsychicWaveMIDs[I]);
        if(!Visible||!PsychicWaveMIDs[I])continue;
        const FVector Origin=(Psychic.ReleasedMask&(1<<I))&&Psychic.Origins.IsValidIndex(I)?Psychic.Origins[I]:
            PsychicReleasePoints.IsValidIndex(I)?GetMesh()->GetComponentTransform().TransformPosition(PsychicReleasePoints[I]):Core;
        const float Radius=FMath::Max(1.f,PsychicRadius*FMath::Clamp(Flight/HeQuePsychicTiming::WaveSeconds,0.f,1.f));
        Wave->SetWorldLocationAndRotation(Origin,FRotator::ZeroRotator);Wave->SetWorldScale3D(FVector(Radius/100.f));
        const float Alpha=1.f-FMath::SmoothStep(HeQuePsychicTiming::WaveSeconds,HeQuePsychicTiming::WaveSeconds+HeQuePsychicTiming::FadeSeconds,Flight);
        PsychicWaveMIDs[I]->SetScalarParameterValue(AlphaName,Alpha);
        PsychicWaveMIDs[I]->SetScalarParameterValue(PhaseName,Flight);
        PsychicWaveMIDs[I]->SetScalarParameterValue(TEXT("WaveSeed"),float(I)*.73f);
        PsychicWaveMIDs[I]->SetScalarParameterValue(TEXT("WaveRadiusCm"),Radius);
    }
}
