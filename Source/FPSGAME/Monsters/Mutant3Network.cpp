#include "Mutant3.h"
#include "FatZombieAnimInstance.h"
#include "HumanoidKnockdownComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"

void AMutant3::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AMutant3, NetworkFeral);
}

void AMutant3::PublishFeralPhase(UAnimSequence* Clip, float BlendSeconds)
{
    if (!HasAuthority()) return;
    NetworkFeral.Phase=FeralPhase;
    NetworkFeral.Clip=Clip;
    NetworkFeral.StartedAt=GetWorld()->GetTimeSeconds();
    NetworkFeral.BlendSeconds=BlendSeconds;
    NetworkFeral.FlightSeconds=PounceFlightSeconds;
    ForceNetUpdate();
}

void AMutant3::OnRep_FeralState()
{
    FeralPhase=NetworkFeral.Phase;
    PresentNetworkFeralPhase();
}

void AMutant3::PresentNetworkFeralPhase()
{
    if (HasAuthority() || State!=ENurseState::Attack || NetworkFeral.Phase==EMutant3FeralPhase::None
        || !NetworkFeral.Clip || (Knockdown && Knockdown->IsControlling())) return;
    FeralPhase=NetworkFeral.Phase;
    AttackClip=NetworkFeral.Clip;
    if (FeralPhase==EMutant3FeralPhase::Recovery)
        TransitionFeralLocomotion(AttackClip,1.f,NetworkFeral.BlendSeconds);
    else if (auto* Animation=GetBlendedAnimation())
    {
        FMonsterClipTransition Settings;
        Settings.bGroundLowerBody=FeralPhase==EMutant3FeralPhase::Landing;
        Animation->TransitionTo(AttackClip,false,true,NetworkFeral.BlendSeconds,Settings);
    }
    TickNetworkFeralPhase();
}

void AMutant3::TickNetworkFeralPhase()
{
    if (!NetworkFeral.Clip || (Knockdown && Knockdown->IsControlling())) return;
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    FeralTime=FMath::Max(0.,Now-NetworkFeral.StartedAt);
    if (NetworkFeral.Phase==EMutant3FeralPhase::Recovery) return;
    const float Sample=NetworkFeral.Phase==EMutant3FeralPhase::Flight
        ? FeralTime/FMath::Max(.2f,NetworkFeral.FlightSeconds)*NetworkFeral.Clip->GetPlayLength() : FeralTime;
    SetAttackAnimationTime(FMath::Min(Sample,NetworkFeral.Clip->GetPlayLength()));
}
