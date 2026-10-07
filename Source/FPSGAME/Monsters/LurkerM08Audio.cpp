#include "LurkerM08Monster.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

// Polls the replicated wolf state on every machine. Authority sees the real
// transition in its own Tick; clients see it after OnRep_State, so one-shots
// stay in sync without touching the shared canine base class.
void ALurkerM08Monster::UpdateM08Audio()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    if (!bAudioVoicesSet)
    {
        bAudioVoicesSet = true;
        if (IdleVoice) IdleVoice->SetSound(IdleSound);
        if (CrawlVoice) CrawlVoice->SetSound(CrawlSound);
    }
    if (State != LastAudioState)
    {
        const EWolfState Entered = State;
        LastAudioState = Entered;
        USoundBase* Cue = nullptr;
        FVector At = GetActorLocation();
        float Falloff = 2400.f;
        switch (Entered)
        {
        case EWolfState::Bite:
            Cue = BiteSound;
            At = GetMesh()->GetSocketLocation(TEXT("head"));
            break;
        case EWolfState::Pounce:
            Cue = PounceSound;
            At = GetMesh()->GetSocketLocation(TEXT("pelvis"));
            break;
        case EWolfState::Stagger:
            Cue = HitSound;
            At = GetMesh()->GetSocketLocation(TEXT("chest"));
            Falloff = 1400.f;
            break;
        case EWolfState::Dying:
            Cue = DeathSound;
            At = GetMesh()->GetSocketLocation(TEXT("chest"));
            break;
        default:
            break;
        }
        if (Cue) UGameplayStatics::PlaySoundAtLocation(this, Cue, At, .95f, 1.f, 0.f, M08OneShotAttenuation(Falloff));
    }
    const bool Alive = !Dead();
    if (IdleVoice)
    {
        if (Alive && IdleVoice->Sound) { if (!IdleVoice->IsPlaying()) IdleVoice->Play(); }
        else if (IdleVoice->IsPlaying()) IdleVoice->Stop();
    }
    if (CrawlVoice)
    {
        const bool BusyAction = State == EWolfState::Bite || State == EWolfState::Pounce || State == EWolfState::Stagger;
        const bool Moving = Alive && !BusyAction && GetVelocity().Size() > 6.f;
        if (Moving && CrawlVoice->Sound) { if (!CrawlVoice->IsPlaying()) CrawlVoice->Play(); }
        else if (CrawlVoice->IsPlaying()) CrawlVoice->Stop();
    }
}

USoundAttenuation* ALurkerM08Monster::M08OneShotAttenuation(float Falloff) const
{
    auto* Attenuation = NewObject<USoundAttenuation>(const_cast<ALurkerM08Monster*>(this));
    Attenuation->Attenuation.bAttenuate = true;
    Attenuation->Attenuation.bSpatialize = true;
    Attenuation->Attenuation.FalloffDistance = Falloff;
    return Attenuation;
}
