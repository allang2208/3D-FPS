#include "HandBrainFearComponent.h"
#include "HeQueMonster.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"

// Presentation rides the existing, replicated fear lifetime. It never adds a
// second status, movement lock or timer, and does not alter HandBrain's fear.
void UHandBrainFearComponent::UpdatePsychicFeedback(float Dt)
{
    const auto* Character=Cast<ACharacter>(GetOwner());
    const auto* Source=Cast<AHeQueMonster>(Threat.Get());
    if(!Character||!Character->IsLocallyControlled()||!Source){StopPsychicFeedback();return;}
    if(PsychicFeedbackSource.Get()!=Source)
    {
        StopPsychicFeedback();PsychicFeedbackSource=Threat;PsychicFeedbackAge=0.f;
        if(Source->PsychicFearViewMaterial)
        {
            PsychicView=UMaterialInstanceDynamic::Create(Source->PsychicFearViewMaterial,this);
            TInlineComponentArray<UCameraComponent*> Cameras(GetOwner());
            for(auto* Camera:Cameras)if(Camera->IsActive())
            {Camera->AddOrUpdateBlendable(PsychicView,1.f);PsychicCamera=Camera;break;}
        }
        if(Source->PsychicFearSound)
        {
            if(!PsychicEarVoice)
            {
                PsychicEarVoice=NewObject<UAudioComponent>(GetOwner());PsychicEarVoice->bAutoActivate=false;
                PsychicEarVoice->bAllowSpatialization=false;PsychicEarVoice->bIsUISound=true;
                GetOwner()->AddInstanceComponent(PsychicEarVoice);PsychicEarVoice->RegisterComponent();
            }
            PsychicEarVoice->SetSound(Source->PsychicFearSound);PsychicEarVoice->SetVolumeMultiplier(.45f);PsychicEarVoice->Play();
        }
    }
    PsychicFeedbackAge+=FMath::Max(0.f,Dt);
    if(PsychicView)
    {
        const float Strength=FMath::SmoothStep(0.f,.18f,PsychicFeedbackAge)*FMath::SmoothStep(0.f,.35f,GetRemainingSeconds());
        PsychicView->SetScalarParameterValue(TEXT("FearStrength"),Strength);
        PsychicView->SetScalarParameterValue(TEXT("FearPhase"),PsychicFeedbackAge);
    }
}
void UHandBrainFearComponent::StopPsychicFeedback()
{
    if(PsychicCamera.IsValid()&&PsychicView)PsychicCamera->RemoveBlendable(PsychicView);
    PsychicCamera.Reset();PsychicView=nullptr;PsychicFeedbackSource.Reset();PsychicFeedbackAge=0.f;
    if(PsychicEarVoice)PsychicEarVoice->Stop();
}
