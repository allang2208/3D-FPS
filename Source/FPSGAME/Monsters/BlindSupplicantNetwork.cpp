#include "BlindSupplicantMonster.h"
#include "HumanoidKnockdownComponent.h"
#include "BlindSupplicantAnimInstance.h"
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

void ABlindSupplicantMonster::ApplyNetworkAttack()
{
    if (HasAuthority() || NetworkAttack.StartedAt<0.) return;
    ActiveAttack=static_cast<EAttack>(NetworkAttack.Kind);
    if (!IsMagicAttack() && NetworkAttack.Clip) AttackClip=NetworkAttack.Clip;
    ActiveAttackDuration=NetworkAttack.Duration;
    ActiveGatherDuration=NetworkAttack.GatherDuration;
    ActiveMeleePlaybackRate=NetworkAttack.MeleeRate;
    bMagicReleaseStarted=false;
    bAttackCancelled=false;
    PresentedNetworkAttackAt=NetworkAttack.StartedAt;
}

void ABlindSupplicantMonster::OnRep_AttackPresentation()
{
    if (State!=ENurseState::Attack || (Knockdown && Knockdown->IsControlling())) return;
    if (PresentedNetworkAttackAt!=NetworkAttack.StartedAt)
    {
        StartStateAnimation(AttackClip,false);
        SetAttackAnimationTime(0.f);
    }
    if (NetworkAttack.bChargeStopped) StopMagicCharge();
}

void ABlindSupplicantMonster::OnRep_WallListening()
{
    if (State!=ENurseState::Idle || (Knockdown && Knockdown->IsControlling())) return;
    bPresentingWallListen=bNetworkWallListening && WallListenClip;
    if (auto* Animation=PosePlayer())
        Animation->TransitionTo(bPresentingWallListen?WallListenClip.Get():IdleClip.Get(),true,false,.3f);
    if (!bPresentingWallListen) StopWallMimic();
}

void ABlindSupplicantMonster::MulticastWallMimic_Implementation(double StartedAt)
{
    if (GetNetMode()==NM_DedicatedServer || State!=ENurseState::Idle || !WallMimicSound || !WallMimicVoice
        || (Knockdown && Knockdown->IsControlling())) return;
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    if (Now-StartedAt>.6 || WallMimicVoice->IsPlaying()) return;
    WallMimicVoice->SetSound(WallMimicSound);
    WallMimicVoice->SetVolumeMultiplier(WallMimicVolume);
    WallMimicVoice->FadeIn(.35f);
}
