#include "SpellbookComponent.h"
#include "SpellbookFocusMotion.h"
#include "SpellbookFocusInterruptMotion.h"
#include "../Staff/StaffCatalog.h"
#include "../../FPSGAMECharacter.h"
#include "../../Combat/CombatStatusFormula.h"
#include "../../Monsters/FPSCombatHealthComponent.h"
#include "../../Multiplayer/ColdSteelPlayerState.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

bool USpellbookComponent::UsesNetFocusAuthority() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    return Character&&Character->HasAuthority()&&!Character->IsLocallyControlled();
}

bool USpellbookComponent::NetFocusEquipmentValid() const
{
    const auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* Profile=Character?Character->GetNetShadowProfile():nullptr;
    if(!Profile)return false;
    const auto* EquippedBook=Profile->ActiveSpellbook();
    const auto* Staff=Profile->Equipped();
    return EquippedBook&&Staff&&ColdSteelStaff::IsStaff(*Staff)&&
        EquippedBook->InstanceId==NetFocusBook&&Staff->InstanceId==NetFocusStaff;
}

bool USpellbookComponent::IsFocusActive() const
{
    if(UsesNetFocusAuthority())return NetFocusEquipmentValid()&&
        (NetFocusStartedAt>=0.0||GetWorld()->GetTimeSeconds()<NetFocusBusyUntil);
    return FocusAge>=0.f;
}

bool USpellbookComponent::IsConcentrating() const
{
    if(UsesNetFocusAuthority())return NetFocusStartedAt>=0.0&&NetFocusEquipmentValid();
    return FocusAge>=0.f&&!bFocusClosing&&!bFocusInterrupted;
}

void USpellbookComponent::SendFocusRequest(uint8 State)
{
    auto* Character=Cast<AFPSGAMECharacter>(GetOwner());
    if(bApplyingFocusReply||!Character||!Character->IsLocallyControlled()||GetNetMode()!=NM_Client)return;
    if(auto* NetState=Character->GetPlayerState<AColdSteelPlayerState>())
    {
        if(State==1)++FocusSession;
        NetState->ServerSetSpellbookFocus(Character,FocusSession,State);
    }
}

void USpellbookComponent::ApplyNetFocusRequest(uint32 Session,uint8 State)
{
    if(!UsesNetFocusAuthority()||State>2)return;
    auto* Character=CastChecked<AFPSGAMECharacter>(GetOwner());
    auto* NetState=Character->GetPlayerState<AColdSteelPlayerState>();
    auto* Profile=Character->GetNetShadowProfile();
    const double Now=GetWorld()->GetTimeSeconds();
    if(State==1)
    {
        if(Session<=NetFocusSession)return;
        NetFocusSession=Session;
        const auto* EquippedBook=Profile?Profile->ActiveSpellbook():nullptr;
        const auto* Staff=Profile?Profile->Equipped():nullptr;
        const auto* Health=Character->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!EquippedBook||!Staff||!ColdSteelStaff::IsStaff(*Staff)||(Health&&Health->IsDead())||
            Character->IsTraversing()||Character->IsSwitchingWeapon()||Character->IsDoorPushActive()||
            NetFocusStartedAt>=0.0||Now<NetFocusBusyUntil)
        {
            if(NetState)NetState->NotifySpellbookFocusStopped(Character,Session,false);
            return;
        }
        NetFocusBook=EquippedBook->InstanceId;NetFocusStaff=Staff->InstanceId;
        FocusMoveMultiplier=Profile->SpellbookFocusMovementMultiplier();
        NetFocusStartedAt=Now;NetFocusBusyUntil=0.0;
        UCombatStatusFormula::GetOrAdd(Character);
        return;
    }
    if(Session!=NetFocusSession)return;
    // Closing removes the benefits immediately, but retains quick-melee occupancy.
    if(State==2&&NetFocusStartedAt>=0.0)
        NetFocusBusyUntil=Now+FMath::Clamp(Now-NetFocusStartedAt,0.0,double(SpellbookFocusMotion::OpenLength));
    if(State==0)NetFocusBusyUntil=0.0;
    NetFocusStartedAt=-1.0;
}

void USpellbookComponent::AdvanceNetFocus()
{
    if(NetFocusStartedAt<0.0&&NetFocusBusyUntil<=0.0)return;
    const auto* Character=CastChecked<AFPSGAMECharacter>(GetOwner());
    const auto* Health=Character->FindComponentByClass<UFPSCombatHealthComponent>();
    if(!NetFocusEquipmentValid()||(Health&&Health->IsDead())||Character->IsTraversing()||
        Character->IsSwitchingWeapon()||Character->IsDoorPushActive())
    {StopNetFocus(false);return;}
    if(NetFocusStartedAt<0.0&&GetWorld()->GetTimeSeconds()>=NetFocusBusyUntil)
        NetFocusBusyUntil=0.0;
}

void USpellbookComponent::StopNetFocus(bool Interrupted)
{
    if(NetFocusStartedAt<0.0&&NetFocusBusyUntil<=0.0)return;
    auto* Character=CastChecked<AFPSGAMECharacter>(GetOwner());
    const double Now=GetWorld()->GetTimeSeconds();
    const float Age=float(FMath::Max(0.0,Now-NetFocusStartedAt));
    NetFocusStartedAt=-1.0; // Clear before the mana notification can re-enter equipment code.
    NetFocusBusyUntil=0.0;
    if(Interrupted)
    {
        const float Source=SpellbookFocusMotion::SourceTime(Age);
        const float Recovery=Source<SpellbookFocusMotion::Detach?Age:
            SpellbookFocusInterruptMotion::Catch+
            SpellbookFocusInterruptMotion::NormalReturnStart(SpellbookFocusInterruptMotion::CatchSource);
        NetFocusBusyUntil=Now+Recovery;
        if(auto* Profile=Character->GetNetShadowProfile())Profile->ApplySpellbookFocusBreak();
    }
    if(auto* NetState=Character->GetPlayerState<AColdSteelPlayerState>())
        NetState->NotifySpellbookFocusStopped(Character,NetFocusSession,Interrupted);
}

void USpellbookComponent::InterruptFocusFromDamage()
{
    // Damage is authoritative. The owner's RPC below only plays the reaction;
    // its resource correction has an independent, idempotent profile ledger.
    if(!GetOwner()->HasAuthority()||!IsConcentrating())return;
    if(UsesNetFocusAuthority()){StopNetFocus(true);return;}
    BeginFocusInterruptPresentation();
    if(Model.IsValid())Model->ApplySpellbookFocusBreak();
}

void USpellbookComponent::ReceiveNetFocusStopped(uint32 Session,bool Interrupted)
{
    if(Session!=FocusSession)return;
    TGuardValue<bool> ApplyingReply(bApplyingFocusReply,true);
    if(Interrupted&&FocusAge>=0.f)BeginFocusInterruptPresentation();
    else CancelFocus();
}

void AColdSteelPlayerState::ServerSetSpellbookFocus_Implementation(AFPSGAMECharacter* Character,uint32 Session,uint8 State)
{
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!Character||!PC||PC->GetPawn()!=Character)return;
    if(auto* Spellbook=Character->FindComponentByClass<USpellbookComponent>())
        Spellbook->ApplyNetFocusRequest(Session,State);
}

void AColdSteelPlayerState::NotifySpellbookFocusStopped(AFPSGAMECharacter* Character,uint32 Session,bool Interrupted)
{
    if(!HasAuthority())return;
    const double Total=ShadowModel?ShadowModel->SpellbookFocusManaLossTotal():0.0;
    if(Interrupted){bServerDirty=true;ShadowMirrorTimer=3.f;}
    ClientSpellbookFocusStopped(Character,Session,Interrupted,Total);
}

void AColdSteelPlayerState::ClientSpellbookFocusStopped_Implementation(AFPSGAMECharacter* Character,uint32 Session,bool Interrupted,double ManaLossTotal)
{
    // The loss still applies after a weapon switch or respawn; the old pawn's
    // animation response must never cancel a new pawn or a new focus session.
    if(auto* GI=GetGameInstance())if(auto* Profile=GI->GetSubsystem<UColdSteelStatusModel>())
        Profile->ReconcileSpellbookFocusManaLoss(ManaLossTotal);
    const auto* PC=Cast<APlayerController>(GetOwner());
    if(!Character||!PC||PC->GetPawn()!=Character)return;
    if(auto* Spellbook=Character->FindComponentByClass<USpellbookComponent>())
        Spellbook->ReceiveNetFocusStopped(Session,Interrupted);
}
