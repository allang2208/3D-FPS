#include "BlindSupplicantMonster.h"
#include "HumanoidKnockdownComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundAttenuation.h"

// Polls the replicated nurse state on every machine. Authority sees the real
// transition in its own Tick; clients see it after OnRep_State. Attack kind is
// authority-only inside PrepareAttack, so AudioAttackKind/AudioMagicReleased
// carry it to remote clients; a short pending window absorbs rep ordering.
void ABlindSupplicantMonster::UpdateM07Audio()
{
    if (GetNetMode() == NM_DedicatedServer) return;
    if (!bAudioVoicesSet)
    {
        bAudioVoicesSet = true;
        if (IdleVoice) IdleVoice->SetSound(IdleSound);
        if (ChaseVoice) ChaseVoice->SetSound(ChaseSound);
    }
    const bool Alive = State != ENurseState::Dead && !(Knockdown && Knockdown->IsFrozen());
    const int32 Kind = HasAuthority()
        ? (IsMagicAttack() ? 2 : (ActiveAttack != EAttack::None ? 1 : 0))
        : int32(AudioAttackKind);
    const bool Released = bMagicReleaseStarted || AudioMagicReleased;
    auto FireAttackCue = [&](int32 AttackKind)
    {
        if (AttackKind == 2)
        {
            bMagicReleaseHeard = false;
            if (MagicGatherSound)
                GatherVoice = UGameplayStatics::SpawnSoundAttached(MagicGatherSound, GetMesh(),
                    NAME_None, CastingSpellPosition(), EAttachLocation::KeepWorldPosition, true);
        }
        else if (AttackKind == 1 && MeleeSound)
        {
            UGameplayStatics::PlaySoundAtLocation(this, MeleeSound, AttackClawPosition(),
                .95f, 1.f, 0.f, M07OneShotAttenuation(2400.f));
        }
    };
    if (State != LastAudioState)
    {
        const ENurseState Entered = State;
        LastAudioState = Entered;
        USoundBase* Cue = nullptr;
        FVector At = GetActorLocation() + FVector(0, 0, 140);
        float Falloff = 2400.f;
        switch (Entered)
        {
        case ENurseState::Attack:
            bPendingAttackCue = Kind == 0;
            PendingAttackCueAt = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.;
            if (Kind != 0) FireAttackCue(Kind);
            break;
        case ENurseState::Stagger:
            Cue = HitSound;
            Falloff = 1400.f;
            break;
        case ENurseState::Dead:
            Cue = DeathSound;
            break;
        default:
            break;
        }
        if (Entered != ENurseState::Attack) bPendingAttackCue = false;
        if (Cue) UGameplayStatics::PlaySoundAtLocation(this, Cue, At, .95f, 1.f, 0.f, M07OneShotAttenuation(Falloff));
    }
    if (bPendingAttackCue)
    {
        const bool Expired = !GetWorld() || GetWorld()->GetTimeSeconds() - PendingAttackCueAt > .6;
        if (Kind != 0) { bPendingAttackCue = false; FireAttackCue(Kind); }
        else if (Expired || State != ENurseState::Attack) bPendingAttackCue = false;
    }
    if (State == ENurseState::Attack && Kind == 2)
    {
        if (Released && !bMagicReleaseHeard)
        {
            bMagicReleaseHeard = true;
            if (GatherVoice && GatherVoice->IsPlaying()) GatherVoice->Stop();
            if (MagicReleaseSound)
                UGameplayStatics::PlaySoundAtLocation(this, MagicReleaseSound, CastingSpellPosition(),
                    .95f, 1.f, 0.f, M07OneShotAttenuation(2400.f));
        }
    }
    else if (GatherVoice && GatherVoice->IsPlaying()) GatherVoice->Stop();
    if (GatherVoice && !GatherVoice->IsPlaying()) GatherVoice = nullptr;
    if (IdleVoice)
    {
        if (Alive && State == ENurseState::Idle && IdleVoice->Sound)
        { if (!IdleVoice->IsPlaying()) IdleVoice->Play(); }
        else if (IdleVoice->IsPlaying()) IdleVoice->Stop();
    }
    if (ChaseVoice)
    {
        const bool Moving = Alive && State == ENurseState::Chase && GetVelocity().Size2D() > 4.f;
        if (Moving && ChaseVoice->Sound) { if (!ChaseVoice->IsPlaying()) ChaseVoice->Play(); }
        else if (ChaseVoice->IsPlaying()) ChaseVoice->Stop();
    }
}

USoundAttenuation* ABlindSupplicantMonster::M07OneShotAttenuation(float Falloff) const
{
    auto* Attenuation = NewObject<USoundAttenuation>(const_cast<ABlindSupplicantMonster*>(this));
    Attenuation->Attenuation.bAttenuate = true;
    Attenuation->Attenuation.bSpatialize = true;
    Attenuation->Attenuation.FalloffDistance = Falloff;
    return Attenuation;
}
