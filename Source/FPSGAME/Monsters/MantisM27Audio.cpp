#include "MantisM27Monster.h"
#include "HumanoidKnockdownComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Sound/SoundBase.h"

void AMantisM27Monster::InitializeMantisAudio()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    const auto CreateVoice = [this](FName Name, float Radius, float Falloff)
    {
        auto* Voice = NewObject<UAudioComponent>(this, Name);
        Voice->SetupAttachment(GetRootComponent());
        Voice->bAutoActivate = false;
        Voice->bAutoDestroy = false;
        Voice->bStopWhenOwnerDestroyed = true;
        Voice->bOverrideAttenuation = true;
        Voice->AttenuationOverrides.bAttenuate = true;
        Voice->AttenuationOverrides.bSpatialize = true;
        Voice->AttenuationOverrides.AttenuationShapeExtents = FVector(Radius,0,0);
        Voice->AttenuationOverrides.FalloffDistance = Falloff;
        Voice->RegisterComponent();
        return Voice;
    };
    // Four reusable voices, no runtime loading or per-event components. Quiet
    // body/cloak detail has a much shorter audible range than attack warnings.
    MantisActionVoice = CreateVoice(TEXT("M27ActionVoice"),150.f,1850.f);
    MantisAccentVoice = CreateVoice(TEXT("M27AccentVoice"),100.f,1300.f);
    MantisAmbientVoice = CreateVoice(TEXT("M27AmbientVoice"),60.f,590.f);
    MantisContactVoice = CreateVoice(TEXT("M27ContactVoice"),100.f,1300.f);
    MantisContactVoice->SetAbsolute(true,false,false);
}

void AMantisM27Monster::PlayMantisVoice(UAudioComponent* Voice, FName CueRole, float Volume, float StartTime)
{
    if (!Voice || GetNetMode() == NM_DedicatedServer) return;
    const auto* Found = MantisSounds.Find(CueRole);
    USoundBase* Sound = Found ? Found->Get() : nullptr;
    if (!Sound || StartTime < 0.f || StartTime >= Sound->GetDuration()) return;
    Voice->Stop();
    Voice->SetSound(Sound);
    Voice->SetVolumeMultiplier(Volume);
    Voice->SetPitchMultiplier(1.f); // State-start cues retain their authored contact time.
    Voice->Play(StartTime);
}

void AMantisM27Monster::MulticastMantisAccent_Implementation(FName CueRole, double StartedAt)
{
    if (State == ENurseState::Dead || GetNetMode() == NM_DedicatedServer) return;
    const float Age = FMath::Max(0.f,float(ServerClock()-StartedAt));
    if (Age > .35f) return; // Do not replay a stale transformation/hurt event.
    if (CueRole == TEXT("PounceLand") && MantisActionVoice) MantisActionVoice->Stop();
    // Gunfire cannot obscure the short cloak/ambush warning already sounding.
    if (CueRole == TEXT("Hurt") && MantisAccentVoice && MantisAccentVoice->IsPlaying()) return;
    PlayMantisVoice(MantisAccentVoice, CueRole, CueRole == TEXT("Hurt") ? .48f : .88f, Age);
}

void AMantisM27Monster::MulticastMantisContact_Implementation(FVector_NetQuantize Location, double StartedAt, bool Alternate)
{
    if (!MantisContactVoice || GetNetMode() == NM_DedicatedServer) return;
    const float Age = FMath::Max(0.f,float(ServerClock()-StartedAt));
    if (Age > .20f) return;
    MantisContactVoice->SetWorldLocation(Location);
    PlayMantisVoice(MantisContactVoice, Alternate ? TEXT("ScytheHitA") : TEXT("ScytheHitB"), .85f, Age);
}

void AMantisM27Monster::UpdateMantisAudio()
{
    if (!MantisActionVoice || GetNetMode() == NM_DedicatedServer) return;
    const bool Dead = State == ENurseState::Dead;
    if (State != LastMantisAudioState)
    {
        LastMantisAudioState = State;
        if (Dead)
        {
            StopMantisAudio();
            PlayMantisVoice(MantisActionVoice,TEXT("Death"),.8f);
        }
    }
    if (Dead) return;
    const bool Controlled = State == ENurseState::Stagger || (Knockdown && Knockdown->IsControlling());
    if (State == ENurseState::Attack && !Controlled && !bCloaked)
    {
        if (PouncePhase == EM27PouncePhase::None)
        {
            const float Age = float(ServerClock()-AttackStartedAt);
            if (AttackSequence != LastMantisAudioAttack && Age >= 0.f && Age < GetAttackDuration())
            {
                LastMantisAudioAttack = AttackSequence;
                PlayMantisVoice(MantisActionVoice,(AttackSequence & 1) ? TEXT("SlashLeft") : TEXT("SlashRight"),.9f,Age);
            }
        }
        else if (PouncePhase != LastMantisAudioPounce || PouncePhaseStartedAt != LastMantisAudioPhaseAt)
        {
            const float Age = float(ServerClock()-PouncePhaseStartedAt);
            if (Age >= 0.f)
            {
                LastMantisAudioPounce = PouncePhase;
                LastMantisAudioPhaseAt = PouncePhaseStartedAt;
                MantisActionVoice->Stop();
                FName CueRole = NAME_None;
                if (PouncePhase == EM27PouncePhase::Windup) CueRole = TEXT("PounceWindup");
                else if (PouncePhase == EM27PouncePhase::Flight) CueRole = TEXT("PounceFlight");
                // Actual ground contact emits the landing accent separately,
                // including a dodged/parried impact that cancels this phase.
                if (!CueRole.IsNone()) PlayMantisVoice(MantisActionVoice,CueRole,1.f,Age);
            }
        }
    }
    else if (MantisActionVoice->IsPlaying()) MantisActionVoice->Stop();
    if (PouncePhase == EM27PouncePhase::None)
    {
        LastMantisAudioPounce = EM27PouncePhase::None;
        LastMantisAudioPhaseAt = -1.;
    }

    // Only the existing actor tick drives these cosmetic edges. No attack
    // timers, montage notifies or damage clock are introduced for sound.
    FName Ambient = NAME_None;
    if (bCloaked) Ambient = TEXT("CloakLoop");
    else if (!Controlled && State == ENurseState::Idle) Ambient = TEXT("Idle");
    else if (!Controlled && State == ENurseState::Chase && GetVelocity().SizeSquared2D() > FMath::Square(14.f)) Ambient = TEXT("Move");
    if (Ambient != MantisAmbientRole)
    {
        MantisAmbientRole = Ambient;
        if (Ambient.IsNone()) MantisAmbientVoice->FadeOut(.06f,0.f);
        else
        {
            const auto* Found = MantisSounds.Find(Ambient);
            MantisAmbientVoice->Stop();
            if (Found && *Found)
            {
                MantisAmbientVoice->SetSound(Found->Get());
                MantisAmbientVoice->SetPitchMultiplier(1.f);
                MantisAmbientVoice->FadeIn(.12f,Ambient == TEXT("CloakLoop") ? .23f : .32f);
            }
        }
    }
}

void AMantisM27Monster::StopMantisAudio()
{
    for (UAudioComponent* Voice : {MantisActionVoice.Get(),MantisAccentVoice.Get(),MantisAmbientVoice.Get(),MantisContactVoice.Get()})
        if (Voice) Voice->Stop();
    MantisAmbientRole = NAME_None;
}

void AMantisM27Monster::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    StopMantisAudio();
    Super::EndPlay(EndPlayReason);
}
