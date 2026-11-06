#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GameFramework/GameStateBase.h"

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

void URuneSwordComponent::SetHeavyCharging(bool Charging,bool bReleasedHeavy)
{
    if(bCharging==Charging)return;
    bCharging=Charging;
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority())
    {
        const auto* World=GetWorld();const auto* GS=World->GetGameState();
        ServerSetSwordHeavyCharge(InstanceId,Charging,bReleasedHeavy,
            GS?GS->GetServerWorldTimeSeconds():World->GetTimeSeconds());
    }
}

void URuneSwordComponent::CancelHeavyCharge()
{
    if(!bCharging)return;
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->HasAuthority()&&!Pawn->IsLocallyControlled())
    {
        bCharging=false;ServerHeavyChargeStartedAt=-1.;ClientCancelSwordHeavyCharge(InstanceId);return;
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

bool URuneSwordComponent::ConsumeNetworkHeavyChargeForRelease(const FString& Weapon)
{
    if(!GetOwner()||!GetOwner()->HasAuthority()||Weapon!=InstanceId||!GetWorld())return false;
    const double Now=GetWorld()->GetTimeSeconds();
    if(!bCharging||ServerHeavyChargeStartedAt<0.
        ||Now-ServerHeavyChargeStartedAt<FMath::Max(0.1,ServerHeavyRequiredSeconds-0.15))return false;
    auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    if(!Model||!CanMaintainHeavyCharge())return false;
    // The stamina tick only bills after the begin RPC arrives. Settle the
    // missing part of a successful hold with the release, exactly once.
    const double UnbilledSeconds=ServerHeavyChargeReceivedAt>=0.?FMath::Max(0.,
        FMath::Min(ServerHeavyRequiredSeconds,Now-ServerHeavyChargeStartedAt)-(Now-ServerHeavyChargeReceivedAt)):0.;
    const double Cost=ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model)+
        UnbilledSeconds*Model->HeavyChargeStaminaPerSecond();
    if(!Model->CanSpendStamina(Cost))return false;
    Model->SpendStamina(Cost);
    bCharging=false;ServerHeavyChargeStartedAt=-1.;
    NetworkHeavyReleaseUntil=Now+.6;
    GrantBroadbladeSweep(Weapon);
    return true;
}

void URuneSwordComponent::ConsumeNetworkHeavyReleaseWindow()
{
    if(GetOwner()&&GetOwner()->HasAuthority())NetworkHeavyReleaseUntil=0.;
}

void URuneSwordComponent::ServerSetSwordHeavyCharge_Implementation(const FString& Weapon,bool Charging,bool bReleasedHeavy,double ClientStartedAt)
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
        // Opening the release receipt only after a real, long enough hold is
        // what lets hit/rift validation distinguish heavy from a light swing.
        if(bReleasedHeavy && bCharging && !ConsumeNetworkHeavyChargeForRelease(Weapon))
            ClientCancelSwordHeavyCharge(Weapon);
        bCharging=false;ServerHeavyChargeStartedAt=-1.;
        return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    // Use the same bounded, synchronized clock as the one-handed heavy charge.
    // A repeated begin cannot restart or backdate an active/cancelled hold.
    if(bCharging||!FMath::IsFinite(ClientStartedAt)||ClientStartedAt<=0.||
        ClientStartedAt>Now+.1||Now-ClientStartedAt>.9||ClientStartedAt<=ServerHeavyChargeLastStartedAt)return;
    const auto* Model=ColdSteelAuthority::ForPawn(Pawn);
    if(!CanMaintainHeavyCharge()||!Model||Model->Stamina()<=0.f||
        !Model->CanSpendStamina(ColdSteelMelee::HeavyReleaseStamina(Model->Equipped(),Model)))
    {
        bCharging=false;ServerHeavyChargeStartedAt=-1.;ClientCancelSwordHeavyCharge(Weapon);return;
    }
    // The shadow profile's normal stamina tick consumes the same rate as the owner.
    // No per-frame RPC, client-supplied cost, or animation progress drives payment.
    if(!bCharging)
    {
        ServerHeavyChargeStartedAt=FMath::Min(ClientStartedAt,Now);
        ServerHeavyChargeLastStartedAt=ClientStartedAt;ServerHeavyChargeReceivedAt=Now;
        NetworkHeavyReleaseUntil=-1.;
        if(const auto* Item=Model->Equipped())
            ServerHeavyRequiredSeconds=float(ColdSteelMelee::Evaluate(*Item,Model).HeavyChargeSeconds);
    }
    bCharging=true;
}

void URuneSwordComponent::TickNetworkHeavyCharge()
{
    const auto* Model=ColdSteelAuthority::ForPawn(Character.Get());
    if(GetOwner()->HasAuthority()&&bCharging&&(!CanMaintainHeavyCharge()||!Model||Model->Stamina()<=0.f))
    {
        bCharging=false;ServerHeavyChargeStartedAt=-1.;ClientCancelSwordHeavyCharge(InstanceId);
    }
}

void URuneSwordComponent::ClientCancelSwordHeavyCharge_Implementation(const FString& Weapon)
{
    const auto* Pawn=Character.Get();
    if(Pawn&&Pawn->IsLocallyControlled()&&!Pawn->HasAuthority()&&Weapon==InstanceId&&bCharging)
        CancelHeavyCharge();
}
