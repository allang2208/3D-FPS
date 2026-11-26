#include "RingChainRebound.h"
#include "RuneSwordComponent.h"
#include "GunsmithSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

void URuneSwordComponent::ClearRingChainProgress()
{
    const APawn* Pawn=Cast<APawn>(GetOwner());
    if(RingChainGrant && Pawn && Pawn->HasAuthority() && !Pawn->IsLocallyControlled())
        ClientRingChainWindow(RingChainWeapon,0,-1.);
    RingChainProgress={};
    RingChainGrant=RingChainAcknowledged=0;
    if(!RingChainWeapon.IsEmpty())NetworkHeavyReleaseUntil=-1.;
    RingSweepReleaseSerial=0;RingSweepTargets.Reset();
    RingChainEquippedAt=OathClock();
}

void URuneSwordComponent::RefreshRingChain(const FColdSteelItem* Item)
{
    bool Installed=false;
    if(Item&&Item->Definition==TEXT("ue_forged_steel_greatsword"))
        if(const auto* Smith=GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>())
            Installed=Smith->Installed(*Item).FindRef(TEXT("pommel"))==TEXT("ring_chain_pommel");
    if(Installed?RingChainWeapon==Item->InstanceId:RingChainWeapon.IsEmpty())return;
    ClearRingChainProgress();
    RingChainWeapon=Installed?Item->InstanceId:FString();
}

void URuneSwordComponent::PlayRingChainReady() const
{
    // Held by the existing hatchet charm CDO. Never synchronously load audio on a hit.
    static const FSoftObjectPath SoundPath(TEXT("/Game/Weapons/TacticalHatchet20261101/ExclusivePendants/S_Hatchet_EmberClink.S_Hatchet_EmberClink"));
    if(auto* Cue=Cast<USoundBase>(SoundPath.ResolveObject()))UGameplayStatics::PlaySound2D(this,Cue,.6f,1.f);
}

void URuneSwordComponent::ConfirmRingChainHit(const FString& Weapon,uint32 Swing)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->HasAuthority()||Weapon.IsEmpty()||Weapon!=RingChainWeapon)return;
    if(const auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP&&HP->IsDead())return;
    if(!RingChainProgress.Hit(Swing,OathClock()))return;
    RingChainGrant=Swing;
    if(Pawn->IsLocallyControlled())
    {
        RingChainAcknowledged=Swing;
        PlayRingChainReady();
    }
    else
    {
        RingChainAcknowledged=0;
        ClientRingChainWindow(Weapon,Swing,RingChainProgress.ReadyUntil);
    }
}

void URuneSwordComponent::ClientRingChainWindow_Implementation(const FString& Weapon,uint32 Swing,double Until)
{
    if(Weapon!=RingChainWeapon)return;
    if(!Swing)
    {
        ClearRingChainProgress();
        return;
    }
    if(Until<OathClock())return;
    RingChainGrant=RingChainAcknowledged=Swing;
    RingChainProgress.ReadyUntil=Until;
    PlayRingChainReady();
    // This reliable ack precedes the owner's next heavy-begin RPC on this same
    // component. A hold started before the cue cannot spend an unseen grant.
    ServerAcknowledgeRingChain(Weapon,Swing);
}

void URuneSwordComponent::ServerAcknowledgeRingChain_Implementation(const FString& Weapon,uint32 Swing)
{
    if(Weapon==RingChainWeapon&&Swing==RingChainGrant)
        RingChainAcknowledged=Swing;
}

bool URuneSwordComponent::RingChainReadyAt(const FColdSteelItem& Item,double StartedAt) const
{
    if(!RingChainGrant||RingChainAcknowledged!=RingChainGrant||RingChainWeapon!=Item.InstanceId
        ||Item.Definition!=TEXT("ue_forged_steel_greatsword"))return false;
    const auto* HP=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    return (!HP||!HP->IsDead())&&RingChainProgress.IsReady(StartedAt>=0.?StartedAt:OathClock());
}

bool RingChainRebound::IsReady(APawn* Pawn,const FColdSteelItem& Item,double StartedAt)
{
    const auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    return Sword&&Sword->RingChainReadyAt(Item,StartedAt);
}

bool RingChainRebound::Consume(APawn* Pawn,const FColdSteelItem& Item,double StartedAt)
{
    auto* Sword=Pawn?Pawn->FindComponentByClass<URuneSwordComponent>():nullptr;
    if(!Sword||!Sword->RingChainReadyAt(Item,StartedAt))return false;
    Sword->RingChainProgress.ReadyUntil=-1.;
    Sword->RingChainGrant=Sword->RingChainAcknowledged=0;
    return true;
}
