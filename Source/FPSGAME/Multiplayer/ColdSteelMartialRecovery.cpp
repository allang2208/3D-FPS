#include "ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelProfileRecovery.h"
#include "../FPSGAMECharacter.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

void UColdSteelStatusModel::SyncMartialCooldowns(bool Immediate)
{
    if(!CurrentPawn.IsValid()||!CurrentPawn->IsLocallyControlled()||CurrentPawn->GetNetMode()!=NM_Client)return;
    if(auto* PS=CurrentPawn->GetPlayerState<AColdSteelPlayerState>())PS->SyncMartialCooldowns(Current,Immediate);
}
void AColdSteelPlayerState::SyncMartialCooldowns(const FColdSteelProfile& Profile,bool Immediate)
{
    if(GetNetMode()!=NM_Client||!GetPawn())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(!Immediate&&Now<MartialPublishAt)return;
    MartialPublishAt=Now+.25;
    const auto* GS=GetWorld()->GetGameState();
    ServerMartialCooldowns(GetPawn(),Profile.MartialCooldownRevision,Profile.WhirlwindCooldown,
        Profile.WhirlwindCooldownDuration,Profile.SwordUppercutCooldown,Profile.SwordUppercutCooldownDuration,
        GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds());
}
void AColdSteelPlayerState::ServerMartialCooldowns_Implementation(APawn* SourcePawn,int64 Revision,
    float Whirlwind,float WhirlwindDuration,float Uppercut,float UppercutDuration,double CapturedAt)
{
    if(!HasAuthority()||!ShadowModel||!SourcePawn||SourcePawn!=GetPawn()||Revision<0||!FMath::IsFinite(CapturedAt))return;
    const auto Valid=[](float Remaining,float Duration)
    {return FMath::IsFinite(Remaining)&&FMath::IsFinite(Duration)&&Remaining>=0.f&&Duration>=Remaining&&Duration<=300.f;};
    if(!Valid(Whirlwind,WhirlwindDuration)||!Valid(Uppercut,UppercutDuration))return;
    auto State=ShadowModel->Snapshot();auto Incoming=State;
    Incoming.MartialCooldownRevision=Revision;Incoming.WhirlwindCooldown=Whirlwind;
    Incoming.WhirlwindCooldownDuration=WhirlwindDuration;Incoming.SwordUppercutCooldown=Uppercut;
    Incoming.SwordUppercutCooldownDuration=UppercutDuration;
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    ColdSteelProfileRecovery::MartialCooldowns(State,Incoming,float(FMath::Max(0.,Now-CapturedAt)));
    ShadowModel->AdoptNetMirror(State);bServerDirty=true;
}
