#include "FPSElectricMagicComponent.h"
#include "FPSFireballComponent.h"
#include "NetCastUtils.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "Sound/SoundBase.h"

double UFPSElectricMagicComponent::DomainClock() const
{
    const auto* State=GetWorld()?GetWorld()->GetGameState<AGameStateBase>():nullptr;
    return State?State->GetServerWorldTimeSeconds():GetWorld()?GetWorld()->GetTimeSeconds():0.;
}

void UFPSElectricMagicComponent::StartDomain(const FElectricMagicCast& Spell,uint32 CastId,UColdSteelStatusModel* RewardModel)
{
    FinishDomain(true);
    if(!CastId){CastId=++DomainAuthoritySerial;if(!CastId)CastId=++DomainAuthoritySerial;}
    DomainCast=Spell;DomainCastId=CastId;DomainRewardModel=RewardModel;
    DomainRewards={};DomainAge=DomainVisualAge=NextStrike=0;
    DomainStartedAt=DomainClock();DomainEndedAt=0;
    bDomainActive=true;bDomainFading=false;
    if(GetOwner()->HasAuthority())
    {
        NetDomain.Cast=Spell;NetDomain.CastId=CastId;NetDomain.StartedAt=DomainStartedAt;
        NetDomain.EndedAt=0;NetDomain.bActive=true;GetOwner()->ForceNetUpdate();
    }
    SpawnDomainFX();PlayDomainStartSound();
    Strike();NextStrike=DomainCast.StrikeSeconds;
}

void UFPSElectricMagicComponent::SettleDomainRewards()
{
    auto* Profile=DomainRewardModel.Get();
    auto Rewards=MoveTemp(DomainRewards);DomainRewards={};DomainRewardModel.Reset();
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(GetOwner()->HasAuthority()&&Profile&&(!Health||!Health->IsDead()))
        Profile->FinishElectricMagicCast(TEXT("stormDomain"),Rewards);
}

void UFPSElectricMagicComponent::FadeDomain()
{
    if(!bDomainActive||bDomainFading)return;
    bDomainFading=true;DomainEndedAt=DomainStartedAt+DomainCast.Duration;
    SettleDomainRewards();
    if(GetOwner()->HasAuthority())
    {
        NetDomain.bActive=false;NetDomain.EndedAt=DomainEndedAt;GetOwner()->ForceNetUpdate();
    }
    if(CloudFX)CloudFX->SetVariableFloat(TEXT("User.CloudEmission"),0.f);
}

void UFPSElectricMagicComponent::FinishDomain(bool bTrain)
{
    if(bTrain)SettleDomainRewards();else{DomainRewards={};DomainRewardModel.Reset();}
    bDomainActive=bDomainFading=false;
    if(GetOwner()->HasAuthority()&&NetDomain.bActive)
    {
        NetDomain.bActive=false;NetDomain.EndedAt=DomainClock();GetOwner()->ForceNetUpdate();
    }
    if(CloudFX){CloudFX->DestroyComponent();CloudFX=nullptr;}
}

void UFPSElectricMagicComponent::FinishDomainForRemoval()
{
    if(GetOwner()->HasAuthority())FinishDomain(true);
}

void UFPSElectricMagicComponent::ConfirmDomainRelease(uint32 CastId)
{
    if(!CastId||CastId!=DomainLocalCastId||DomainConfirmedCastId==CastId)return;
    DomainConfirmedCastId=CastId;
    if(auto* Profile=Model())Profile->CommitElectricMagicRelease(TEXT("stormDomain"));
}

void UFPSElectricMagicComponent::OnRep_Domain()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!NetDomain.CastId)return;
    if(!Pawn->HasAuthority()&&Pawn->IsLocallyControlled())
    {
        if(NetDomain.CastId!=DomainLocalCastId)return;
        ConfirmDomainRelease(NetDomain.CastId);
        if(DomainCancelledCastId==NetDomain.CastId)return;
    }
    // A late observer of an already-ended cast must not restart its cloud.
    if(!NetDomain.bActive&&(!bDomainActive||DomainCastId!=NetDomain.CastId))return;
    const bool Changed=DomainCastId!=NetDomain.CastId;
    if(Changed&&CloudFX){CloudFX->DestroyComponent();CloudFX=nullptr;}
    DomainCast=NetDomain.Cast;DomainCastId=NetDomain.CastId;
    DomainStartedAt=NetDomain.StartedAt;DomainEndedAt=NetDomain.EndedAt;
    DomainAge=FMath::Max(0.f,float(DomainClock()-DomainStartedAt));
    bDomainActive=true;bDomainFading=!NetDomain.bActive||DomainAge>=DomainCast.Duration;
    if(bDomainFading&&DomainEndedAt<=0)DomainEndedAt=DomainStartedAt+DomainCast.Duration;
    if(bDomainFading&&DomainClock()>=DomainEndedAt+.6){FinishDomain(false);return;}
    if(Changed)DomainVisualAge=0;
    if(!CloudFX)SpawnDomainFX();
    if(CloudFX)CloudFX->SetVariableFloat(TEXT("User.CloudEmission"),bDomainFading?0.f:1.f);
    PlayDomainStartSound();
}

void UFPSElectricMagicComponent::PlayDomainStartSound()
{
    if(!bDomainActive||bDomainFading||!DomainCastId||DomainSoundCastId==DomainCastId||GetNetMode()==NM_DedicatedServer)return;
    auto* Sound=Assets.IsValidIndex(5)?Cast<USoundBase>(Assets[5]):nullptr;
    if(!Sound)return;
    DomainSoundCastId=DomainCastId;
    if(DomainClock()-DomainStartedAt>1.25)return;
    UGameplayStatics::PlaySoundAtLocation(this,Sound,GetOwner()->GetActorLocation(),.6f);
}

void UFPSElectricMagicComponent::MulticastDomainStrikeSound_Implementation(FVector_NetQuantize Point)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Sound=Assets.IsValidIndex(5)?Cast<USoundBase>(Assets[5]):nullptr)
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Point,.35f);
}

void UFPSElectricMagicComponent::NetDomainCastResult(uint8 Phase,uint8 Code,uint32 CastId)
{
    if(!CastId||CastId!=DomainLocalCastId)return;
    if(Code==0){if(Phase==1)ConfirmDomainRelease(CastId);return;}
    if(Phase>1||DomainConfirmedCastId==CastId)return;
    const bool Pending=CommittedSkill==TEXT("stormDomain");
    const bool Cancelled=DomainCancelledCastId==CastId;
    DomainCancelledCastId=CastId;
    if(auto* Profile=Model())Profile->RefundUnreleasedCast(0.f,TEXT("stormDomain"));
    if(DomainCastId==CastId)FinishDomain(false);
    if(Pending)
    {
        CommittedSkill=NAME_None;bNetPaid=false;
        if(auto* H=Hands()){H->TakeGesturePayment();H->CancelSpellGesture(this);}
    }
    if(QueuedSkill==TEXT("stormDomain"))QueuedSkill=NAME_None;
    if(!Cancelled)Feedback(TEXT("stormDomain"),TEXT("施法失败，已退还消耗"));
}
