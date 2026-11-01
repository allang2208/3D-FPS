#include "ProductionToolComponent.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerThrow.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"

bool UProductionToolComponent::IsThunderRecallLocked() const
{
    const auto* Health=GetOwner()?GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(Health&&Health->IsDead())return false;
    return (bThunderRecallPending&&IsThunderHammerAway()) ||
        (IsValid(ThrownHammer)&&(ThrownHammer->IsReturning()||ThrownHammer->IsCatching())) ||
        (ThunderCatchStartedAt>=0.&&RuneboundClock()-ThunderCatchStartedAt<ThunderHammerThrow::CatchSeconds);
}

bool UProductionToolComponent::QueueThunderWeaponSwitch()
{
    if(!IsThunderRecallLocked())return false;
    bThunderSwitchQueued=true;return true; // Repeated wheel input stores one switch.
}

bool UProductionToolComponent::ValidateThunderEquipmentChange(const FColdSteelProfile& Before,const FColdSteelProfile& After,FString& Reason) const
{
    if(After.Health<=0.f||!IsThunderRecallLocked())return true;
    const FString& Instance=IsValid(ThrownHammer)?ThrownHammer->Instance():ThunderActionInstance;
    const auto* Hammer=After.Items.FindByPredicate([&](const auto& Item){return Item.InstanceId==Instance&&Item.Place==1;});
    // Leaving equipment is always permitted: the successful transaction will
    // remove the combat actor immediately, including during an active recall.
    if(!Hammer)return true;
    const bool Changed=Before.ActiveWeaponSlot!=After.ActiveWeaponSlot||Before.ActiveProductionTool!=After.ActiveProductionTool||
        Hammer->Cell!=After.ActiveWeaponSlot;
    if(Changed){Reason=TEXT("正在召回或接住雷神之锤，接稳后切换武器");return false;}
    return true;
}

void UProductionToolComponent::CommitThunderEquipmentChange(const FColdSteelProfile& State)
{
    if(GetOwner()->HasAuthority()&&IsValid(ThrownHammer)&&!ThrownHammer->IsStillEquipped(State))
        ThrownHammer->ReturnToStorage();
    if(!ThunderActionInstance.IsEmpty()&&!State.Items.ContainsByPredicate([&](const auto& Item)
        {return Item.InstanceId==ThunderActionInstance&&Item.Place==1;}))
    {
        // The flight actor retires early in the catch. Unequipping during its
        // remaining hand animation must also discard that receipt/queued switch.
        ThunderActionInstance.Reset();ThunderCatchStartedAt=-100.;ThunderCatchAge=ThunderReachAge=-1.f;
        bThunderRecallPending=bThunderSwitchQueued=false;
        if(GetOwner()->HasAuthority())GetOwner()->ForceNetUpdate();
    }
}

void UProductionToolComponent::ServiceThunderLifecycle()
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->IsLocallyControlled())return;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead()){bThunderSwitchQueued=false;return;}
    if(bThunderSwitchQueued&&!IsThunderRecallLocked())
    {
        bThunderSwitchQueued=false;
        if(auto* Profile=ColdSteelAuthority::ForPawn(Pawn))Profile->CycleWeapon();
    }
}
