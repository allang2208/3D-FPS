#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/StatusEffectsComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"

bool URuneSwordComponent::HasGaleGuard(const FColdSteelItem* Item) const
{
    return Item && Item->Definition==TEXT("ue_highland_claymore") && GetWorld() && GetWorld()->GetGameInstance()
        && GaleWing::Installed(GetWorld()->GetGameInstance()->GetSubsystem<UGunsmithSystem>(),Item);
}

void URuneSwordComponent::AccumulateGaleCharge(float Paid)
{
    if(bCharging && GetOwner()->HasAuthority())GaleChargePaid+=Paid;
}

float URuneSwordComponent::TakeGaleCharge()
{
    const float Paid=GaleChargePaid;
    GaleChargePaid=0.f;
    return Paid;
}

void URuneSwordComponent::RecordGalePayment(uint64 Key,const FString& Weapon,float Paid,bool bPartialCharge)
{
    if(!Key || !GetOwner()->HasAuthority())return;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=Model && !Model->ActiveProductionTool()?Model->Equipped():nullptr;
    if(!HasGaleGuard(Item) || Item->InstanceId!=Weapon)return;

    const double Now=OathClock();
    for(auto It=GalePayments.CreateIterator();It;++It)
        if(Now-It.Value().RecordedAt>30.)It.RemoveCurrent();
    auto& Payment=GalePayments.FindOrAdd(Key);
    if(Payment.Weapon.IsEmpty()){Payment.Weapon=Weapon;Payment.RecordedAt=Now;}
    if(Payment.Weapon!=Weapon)return;
    bool& Recorded=bPartialCharge?Payment.bHasPartialCharge:Payment.bHasStrikeCost;
    if(Recorded)return;
    Recorded=true;
    if(Payment.bKillRefunded)CreditGaleStamina(Model,Paid);
    else Payment.Unreturned+=FMath::Max(0.f,Paid);
}

bool URuneSwordComponent::HasGalePayment(uint64 Key,const FString& Weapon) const
{
    const auto* Payment=GalePayments.Find(Key);
    return Payment && Payment->bHasStrikeCost && Payment->Weapon==Weapon && OathClock()-Payment->RecordedAt<=30.;
}

void URuneSwordComponent::ConfirmGaleKill(uint64 Key,const FString& Weapon)
{
    if(!GetOwner()->HasAuthority() || !HasGalePayment(Key,Weapon))return;
    // A released sword wave carries the weapon and payment that spawned it.
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!Model || (Health && Health->IsDead()))return;
    auto& Payment=GalePayments.FindChecked(Key);
    if(!Payment.bKillRefunded)
    {
        Payment.bKillRefunded=true;
        const float Due=Payment.Unreturned;
        Payment.Unreturned=0.f;
        CreditGaleStamina(Model,Due);
    }
    GaleSwiftUntil=OathClock()+GaleWing::Duration;
    OnRep_GaleSwiftUntil();
    GetOwner()->ForceNetUpdate();
}

void URuneSwordComponent::CreditGaleStamina(UColdSteelStatusModel* Model,float Amount)
{
    if(Amount<=0.f)return;
    const double Total=Model->RefundOathStamina(Amount);
    if(!Character->IsLocallyControlled())
        if(auto* PS=Character->GetPlayerState<AColdSteelPlayerState>())
            PS->ClientGaleCredit(Model->ConfirmedMartialStaminaSpent(),Total);
}

void URuneSwordComponent::TickGaleSwift()
{
    if(GaleSwiftUntil<=0. || !GetOwner()->HasAuthority())return;
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(GaleSwiftRemaining()>0.f && !(Health && Health->IsDead()))return;
    GaleSwiftUntil=0.;
    OnRep_GaleSwiftUntil();
    GetOwner()->ForceNetUpdate();
}

float URuneSwordComponent::GaleSwiftRemaining() const
{
    return GaleSwiftUntil>0. ? float(FMath::Max(0.,GaleSwiftUntil-OathClock())) : 0.f;
}

void URuneSwordComponent::OnRep_GaleSwiftUntil()
{
    UStatusEffectsComponent::Notify(GetOwner());
}
