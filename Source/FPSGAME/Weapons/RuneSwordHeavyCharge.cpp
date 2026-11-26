#include "RuneSwordComponent.h"
#include "EagleTalonGuardComponent.h"
#include "RingChainRebound.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GameFramework/GameStateBase.h"

double URuneSwordComponent::HeavyReleaseCost(const FColdSteelItem* Item,const UColdSteelStatusModel* Model) const
{
    return ColdSteelMelee::HeavyReleaseStamina(Item,Model)*(bReboundHeavyCharge?1.15:1.);
}

bool URuneSwordComponent::PrepareHeavyCharge(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double Start,double& Duration)
{
    const double ServerStart=OathClock()-(GetWorld()->GetTimeSeconds()-Start);
    const bool Ready=bRingInputInstalled&&RingChainRebound::IsReady(Character.Get(),Item,ServerStart);
    const double Release=ColdSteelMelee::HeavyReleaseStamina(&Item,Model);
    if(!Model->CanSpendStamina(Ready?Release*1.15:Release))return false;
    const auto Stats=ColdSteelMelee::Evaluate(Item,Model);
    bReboundHeavyCharge=Ready&&RingChainRebound::Consume(Character.Get(),Item,ServerStart);
    Duration=Stats.HeavyChargeSeconds*(bReboundHeavyCharge?.5:1.);
    RingChargeFullAt=Start+Duration;
    RingChargeBilledAt=bRingInputInstalled?Start:-1.;
    // Keep a free hold free when the attack and release edges arrive on different network channels.
    RingChargeStaminaScale=UEagleTalonGuardComponent::Ready(Model,&Item)?0.f:Stats.Modifiers.Stamina;
    return true;
}

float URuneSwordComponent::TakeRingChainChargeDrain(double BaseRate)
{
    if(!IsBillingRingChainCharge())return 0.f;
    const bool Remote=Character.IsValid()&&!Character->IsLocallyControlled()&&ServerHeavyChargeReceivedAt>=0.;
    const double Transit=Remote?ServerHeavyChargeReceivedAt-ServerHeavyChargeStartedAt:0.;
    return BillRingChargeUntil(FMath::Max(RingChargeBilledAt,GetWorld()->GetTimeSeconds()-Transit),BaseRate);
}

float URuneSwordComponent::BillRingChargeUntil(double End,double BaseRate)
{
    const double Seconds=End-RingChargeBilledAt;
    // Fit the original charge work into half the time. Holding beyond full
    // costs one ordinary second per second. The surcharge applies to both.
    const double Accelerated=bReboundHeavyCharge?
        FMath::Min(End,RingChargeFullAt)-FMath::Min(RingChargeBilledAt,RingChargeFullAt):0.;
    RingChargeBilledAt=End;
    return float((Seconds+Accelerated)*BaseRate*RingChargeStaminaScale*(bReboundHeavyCharge?1.15:1.));
}

void URuneSwordComponent::SettleRingChainCharge(UColdSteelStatusModel* Model)
{
    if(!IsBillingRingChainCharge()||!Model)return;
    const float Due=FMath::Min(Model->Stamina(),TakeRingChainChargeDrain(Model->HeavyChargeStaminaPerSecond()));
    if(Due>0.f)Model->SpendStamina(Due);
}

void URuneSwordComponent::SettleNetworkRingHold(UColdSteelStatusModel* Model,double Held)
{
    const float Due=BillRingChargeUntil(ServerHeavyChargeStartedAt+Held,Model->HeavyChargeStaminaPerSecond());
    if(Due<0.f)Model->RestoreCombatStamina(-Due);
    else if(Due>0.f)Model->SpendStamina(FMath::Min(Due,Model->Stamina()));
}

float URuneSwordComponent::HeavyChargeFraction() const
{
    const UWorld* World=GetWorld();
    if(!bCharging||!World)return 0.f;
    // Elapsed is a position in the current animation; each blade can have a
    // different clip length. Drive the HUD from the hold used at release.
    const bool bServerHold=ServerHeavyChargeStartedAt>=0.&&Character.IsValid()&&!Character->IsLocallyControlled();
    const double Start=bServerHold?ServerHeavyChargeStartedAt:ChargeStartedAt;
    const double Duration=bServerHold?ServerHeavyRequiredSeconds:RequiredChargeSeconds;
    return float(FMath::Clamp((World->GetTimeSeconds()-Start)/FMath::Max(.001,Duration),0.,1.));
}

bool URuneSwordComponent::CanMaintainHeavyCharge() const
{
    const auto* Pawn=Character.Get();const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Model?Model->Equipped():nullptr;
    return Pawn&&Item&&Item->InstanceId==InstanceId&&ColdSteelInventory::IsTwoHandedSword(*Item)
        &&!Model->ActiveProductionTool()&&Model->MasteryProgress(TEXT("heavyStrike")).Level>=1
        &&!UBoundCongregateCaptureComponent::IsCaptured(Pawn)&&CanUse()&&!Pawn->IsCastBlockingLeftHandAction();
}

double URuneSwordComponent::HeavyInputReleaseStamp() const
{
    // GameState smooths its server-clock offset throughout a hold. Keep the offset
    // sent with this press so the release reports exactly the duration the owner paid.
    if(bRingInputInstalled&&Character.IsValid()&&Character->IsLocallyControlled()&&!Character->HasAuthority()
        &&ServerHeavyChargeLastStartedAt>0.)
        return ServerHeavyChargeLastStartedAt+(GetWorld()->GetTimeSeconds()-ChargeStartedAt);
    return OathClock();
}

void URuneSwordComponent::SetHeavyCharging(bool Charging,bool bReleasedHeavy,uint32 PartialSwingSerial)
{
    if(bCharging==Charging)return;
    if(!Charging)
    {
        SettleRingChainCharge(ColdSteelAuthority::ForPawn(Character.Get()));
        RingChargeBilledAt=-1.;bReboundHeavyCharge=false;
    }
    bCharging=Charging;
    if(!Charging&&!bReleasedHeavy)ClearOath();
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority())
    {
        const auto* World=GetWorld();const auto* GS=World->GetGameState();
        const double ServerNow=GS?GS->GetServerWorldTimeSeconds():World->GetTimeSeconds();
        const double PressStamp=ServerNow-(World->GetTimeSeconds()-ChargeStartedAt);
        if(Charging&&bRingInputInstalled)ServerHeavyChargeLastStartedAt=PressStamp;
        const double ReleaseStamp=bReleasedHeavy&&OathReleaseStamp>0.?OathReleaseStamp:HeavyInputReleaseStamp();
        ServerSetSwordHeavyCharge(InstanceId,Charging,bReleasedHeavy,Charging?PressStamp:ReleaseStamp,
            Charging?0:bReleasedHeavy?NetworkBladeSerial:PartialSwingSerial);
    }
}

void URuneSwordComponent::CancelHeavyCharge()
{
    if(!bCharging)return;
    RingPrimaryDownAt=-1.;
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
    {
        ClearOath();SetHeavyCharging(false);ServerHeavyChargeStartedAt=-1.;ClientCancelSwordHeavyCharge(InstanceId);return;
    }
    ReturnFromCharge();
}

bool URuneSwordComponent::IsNetworkHeavyReleaseWindowOpen(const FString& Weapon) const
{
    const auto* Owner=GetOwner();
    const auto* World=GetWorld();
    return Owner&&Owner->HasAuthority()&&World&&World->GetTimeSeconds()<=NetworkHeavyReleaseUntil
        &&(Weapon.IsEmpty()||Weapon==InstanceId);
}

const FColdSteelItem* URuneSwordComponent::ForgedHeavyContactItem(const FString& Weapon,uint32 Serial,AActor* Target) const
{
    return ForgedHeavyItem&&ForgedHeavyItem->InstanceId==Weapon&&Serial&&Serial==ForgedHeavySerial
        &&IsNetworkHeavyReleaseWindowOpen(Weapon)&&IsValid(Target)&&!ForgedHeavyTargets.Contains(Target)
        ?ForgedHeavyItem.Get():nullptr;
}

bool URuneSwordComponent::ConsumeNetworkHeavyChargeForRelease(const FString& Weapon,double ReleasedAt,uint32 Serial)
{
    if(!GetOwner()||!GetOwner()->HasAuthority()||Weapon!=InstanceId||!GetWorld())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if(!bCharging||ServerHeavyChargeStartedAt<0.
        ||Now-ServerHeavyChargeStartedAt<FMath::Max(0.1,ServerHeavyRequiredSeconds-0.15))return false;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    if(!Model||!CanMaintainHeavyCharge())return false;
    // The stamina tick only bills after the begin RPC arrives. Settle the
    // missing part of a successful hold with the release, exactly once.
    const bool RingBill=IsBillingRingChainCharge();
    if(RingBill)
    {
        // Use the same two input edges as the owner. Network transit does not
        // count as either charge work or holding time after the charge is full.
        if(!FMath::IsFinite(ReleasedAt)||ReleasedAt>Now+.1||(ReleasedAt>0.&&Now-ReleasedAt>.9))return false;
        const double Held=ReleasedAt>0.?ReleasedAt-ServerHeavyChargeLastStartedAt:Now-ServerHeavyChargeReceivedAt;
        if(Held+.00001<ServerHeavyRequiredSeconds)return false;
        SettleNetworkRingHold(Model,Held);
    }
    const double UnbilledSeconds=!RingBill&&ServerHeavyChargeReceivedAt>=0.?FMath::Max(0.,
        FMath::Min(ServerHeavyRequiredSeconds,Now-ServerHeavyChargeStartedAt)-(Now-ServerHeavyChargeReceivedAt)):0.;
    const double Release=HeavyReleaseCost(Model->Equipped(),Model);
    const double Cost=Release+
        UnbilledSeconds*Model->HeavyChargeStaminaPerSecond();
    if(!Model->CanSpendStamina(Cost))return false;
    // Hold one authoritative configuration for every target reached by this release.
    const auto* ReleasedItem=Model->Equipped();
    if(ReleasedItem&&ReleasedItem->Definition==TEXT("ue_forged_steel_greatsword"))
    {
        ForgedHeavyItem=MakeShared<FColdSteelItem>(*ReleasedItem);
        ForgedHeavySerial=Serial;
        ForgedHeavyTargets.Reset();
    }
    const float Before=Model->Stamina();
    Model->SpendStamina(Cost);
    UEagleTalonGuardComponent::Commit(GetOwner(),Weapon,EEagleStrike::Heavy,Serial);
    RecordGalePayment(GaleWing::Key(GaleWing::EAttack::Heavy,Serial),Weapon,TakeGaleCharge()+Before-Model->Stamina());
    OathPaidRelease=FMath::Min(float(Release),FMath::Max(0.f,Before-Model->Stamina()));
    CommitOathRelease(ReleasedAt,Serial);
    if(RingBill)
    {
        RingChargeBilledAt=-1.;
        RingSweepReleaseSerial=Serial;RingSweepTargets.Reset();
    }
    SetHeavyCharging(false,true);ServerHeavyChargeStartedAt=-1.;
    NetworkHeavyReleaseUntil=Now+.6;
    GrantBroadbladeSweep(Weapon);
    return true;
}

void URuneSwordComponent::ConsumeNetworkHeavyReleaseWindow()
{
    if(GetOwner()&&GetOwner()->HasAuthority())NetworkHeavyReleaseUntil=0.;
}

void URuneSwordComponent::ServerSetSwordHeavyCharge_Implementation(const FString& Weapon,bool Charging,bool bReleasedHeavy,double ClientStartedAt,uint32 AttackSerial)
{
    const auto* Pawn=Character.Get();
    if(!Pawn||!Pawn->HasAuthority()||Pawn->IsLocallyControlled())return;
    if(Weapon!=InstanceId)
    {
        if(Charging)ClientCancelSwordHeavyCharge(Weapon);
        return;
    }
    if(!Charging)
    {
        if(!bReleasedHeavy&&IsBillingRingChainCharge()&&ServerHeavyChargeStartedAt>=0.)
        {
            const double Now=GetWorld()->GetTimeSeconds();
            if(FMath::IsFinite(ClientStartedAt)&&ClientStartedAt>=ServerHeavyChargeLastStartedAt
                &&ClientStartedAt<=Now+.1&&Now-ClientStartedAt<=.9)
                if(auto* Model=ColdSteelAuthority::ForPawn(Pawn))
                {
                    // The light follow-through and a cancelled hold settle on the same two
                    // input edges as a heavy. Arrival jitter is not extra charge work.
                    SettleNetworkRingHold(Model,ClientStartedAt-ServerHeavyChargeLastStartedAt);
                    RingChargeBilledAt=-1.;
                }
        }
        // Opening the release receipt only after a real, long enough hold is
        // what lets hit/rift validation distinguish heavy from a light swing.
        // A short hold becomes a light swing. Its debit and contact use the player
        // state channel, while both ends of the hold arrive in order on this one.
        if(!bReleasedHeavy && bCharging && AttackSerial)
            RecordGalePayment(GaleWing::Key(GaleWing::EAttack::Swing,AttackSerial),Weapon,TakeGaleCharge(),true);
        if(bReleasedHeavy && bCharging && !ConsumeNetworkHeavyChargeForRelease(Weapon,ClientStartedAt,AttackSerial))
            ClientCancelSwordHeavyCharge(Weapon);
        if(bReleasedHeavy && IsNetworkHeavyReleaseWindowOpen(Weapon))CommitOathRelease(ClientStartedAt,AttackSerial);
        else if(!bReleasedHeavy || OathState.Phase!=2)ClearOath();
        SetHeavyCharging(false,bReleasedHeavy);ServerHeavyChargeStartedAt=-1.;
        return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    // Use the same bounded, synchronized clock as the one-handed heavy charge.
    // A repeated begin cannot restart or backdate an active/cancelled hold.
    if(bCharging||!FMath::IsFinite(ClientStartedAt)||ClientStartedAt<=0.||
        ClientStartedAt>Now+.1||Now-ClientStartedAt>.9||ClientStartedAt<=ServerHeavyChargeLastStartedAt)return;
    auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    const double Start=FMath::Min(ClientStartedAt,Now);
    if(!CanMaintainHeavyCharge()||!Model||(Model->Stamina()<=0.f&&!UEagleTalonGuardComponent::Ready(Model))||
        !PrepareHeavyCharge(*Model->Equipped(),Model,Start,ServerHeavyRequiredSeconds))
    {
        bCharging=false;ServerHeavyChargeStartedAt=-1.;ClientCancelSwordHeavyCharge(Weapon);return;
    }
    // The shadow profile's normal stamina tick consumes the same rate as the owner.
    // No per-frame RPC, client-supplied cost, or animation progress drives payment.
    if(!bCharging)
    {
        ServerHeavyChargeStartedAt=Start;
        ServerHeavyChargeLastStartedAt=ClientStartedAt;ServerHeavyChargeReceivedAt=Now;
        NetworkHeavyReleaseUntil=-1.;
    }
    bCharging=true;
    RefreshOath(Model->Equipped());
    // Billing uses time physically elapsed on the authority. Judge the two
    // validated input stamps on their shared clock, including positive skew.
    BeginOathCharge(ClientStartedAt,ServerHeavyRequiredSeconds);
}

void URuneSwordComponent::TickNetworkHeavyCharge()
{
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    if(GetOwner()->HasAuthority()&&bCharging&&(!CanMaintainHeavyCharge()||!Model||(Model->Stamina()<=0.f&&!UEagleTalonGuardComponent::Ready(Model))))
    {
        CancelHeavyCharge();
    }
}

void URuneSwordComponent::ClientCancelSwordHeavyCharge_Implementation(const FString& Weapon)
{
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority()&&Weapon==InstanceId)
    {
        ClearOath();
        if(bCharging)CancelHeavyCharge();
    }
}
