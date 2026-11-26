#include "ColdSteelStatusModel.h"
#include "../Movement/StableHorseGear.h"
#include "../Movement/StableHorseAffixes.h"
#include "ColdSteelCurrency.h"
#include "GameFramework/GameStateBase.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelProfileRecovery.h"
#include "../Monsters/FPSCombatHealthComponent.h"

bool UColdSteelStatusModel::ApplyNetworkInventoryReply(const UColdSteelInventoryReply* Reply,APawn* ExpectedPawn)
{
    if(!Reply||!Reply->bSuccess||Reply->Revision<Current.CampfireInventoryRevision)return false;
    SyncRuntime();auto Next=Snapshot();
    if(Reply->MountPotionRoster.Revision>Next.MountRoster.Revision)Next.MountRoster=Reply->MountPotionRoster;
    else if(!Reply->MountPotionRoster.Horses.IsEmpty())StableHorseGear::CopyEquipment(Next.MountRoster,Reply->MountPotionRoster);
    if(Reply->FoodClockId.IsValid()&&FMath::IsFinite(Reply->FoodClockDay)&&Reply->FoodClockDay>=0.)
    {
        Next.FoodClockDay=Next.FoodClockId==Reply->FoodClockId?FMath::Max(Next.FoodClockDay,Reply->FoodClockDay):Reply->FoodClockDay;
        Next.FoodClockId=Reply->FoodClockId;Next.FoodVersion=1;
    }
    auto Ledger=Next;Ledger.ServerSoulCredits=Reply->ServerSoulCredits;Ledger.ServerSoulDebits=Reply->ServerSoulDebits;
    if(!ColdSteelCurrency::MergeServerCredits(Next,Ledger))return false;
    // A full mirror may already have delivered the item revision, but resources
    // still come from this once-only receipt (health/survival use their replicas).
    if(Reply->Revision!=Current.CampfireInventoryRevision)
    {
    Next.Items.RemoveAll([&](const auto& I){return Reply->Removed.Contains(I.InstanceId);});
    for(const auto& Item:Reply->Changed)
    {
        if(auto* Existing=Next.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;}))
        {
            auto Changed=Item;
            if(Existing->Place==1&&Item.Place==1)
            ColdSteelProfileRecovery::LoadedAmmo(Changed,*Existing);
            *Existing=MoveTemp(Changed);
        }
        else Next.Items.Add(Item);
    }
    for(const auto& Pair:Reply->PouchDelta)
        Next.AmmoPouch.FindOrAdd(Pair.Key)=FMath::Max<int64>(0,Next.AmmoPouch.FindRef(Pair.Key)+Pair.Value);
    Next.CampfireInventoryRevision=Reply->Revision;
    Next.CampfireWorldReceipts=Reply->WorldReceipts;
    if(Reply->bEquipmentChanged){Next.ActiveWeaponSlot=Reply->ActiveWeaponSlot;Next.ActiveProductionTool=Reply->ActiveProductionTool;}
    }
    // A full mirror can arrive first. Even at an equal revision this receipt
    // still retires bindings to removed instances; pouch deltas remain once-only.
    for(auto& Binding:Next.QuickBindings)if(Reply->Removed.Contains(Binding.ItemId))Binding=FColdSteelQuickBinding();
    for(int32 N=0;N<Next.Hotbar.Num();++N)if(Reply->Removed.Contains(Next.Hotbar[N]))
    {Next.Hotbar[N].Reset();if(Next.HotbarDefinitions.IsValidIndex(N))Next.HotbarDefinitions[N].Reset();}
    if(Reply->Removed.Contains(Next.ActiveProductionTool))Next.ActiveProductionTool.Reset();
    const auto* Health=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool SameLivingPawn=CurrentPawn.Get()==ExpectedPawn&&Health&&!Health->IsDead();
    if(SameLivingPawn&&Reply->ElementManaSpent>0.f)Next.Mana=FMath::Max(0.f,Next.Mana-Reply->ElementManaSpent);
    if(SameLivingPawn&&Reply->bIlluminationArrow)
    {
        const auto* GS=GetWorld()->GetGameState();
        Next.IlluminationArrowCooldown=FMath::Clamp(float(Reply->ElementCooldownEnd-(GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds())),0.f,Reply->ElementCooldown);
        Next.IlluminationArrowCooldownDuration=Reply->ElementCooldown;
    }
    if(SameLivingPawn&&ElementalArrow::IsElement(Reply->ArrowElement))
    {
        const auto* GS=GetWorld()->GetGameState();
        const float Remaining=FMath::Clamp(float(Reply->ElementCooldownEnd-(GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds())),0.f,Reply->ElementCooldown);
        if(Reply->ArrowElement==EArrowElement::Fire){Next.FireballCooldown=Remaining;Next.FireballCooldownDuration=Reply->ElementCooldown;}
        else if(Reply->ArrowElement==EArrowElement::Ice){Next.IceSpikeCooldown=Remaining;Next.IceSpikeCooldownDuration=Reply->ElementCooldown;}
        else {Next.LightningCooldown=Remaining;Next.LightningCooldownDuration=Reply->ElementCooldown;}
    }
    if(Reply->bResourcesChanged&&SameLivingPawn)
    {Next.Mana=FMath::Min(float(ResourceMaximum(Next,true)),Next.Mana+Reply->ManaRestored);}
    if(SameLivingPawn&&Reply->StaminaSpent>0.f)
    {Next.Stamina=FMath::Max(0.f,Next.Stamina-Reply->StaminaSpent);Next.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;}
    if(Reply->bWorldAction){Next.DungeonRun=Reply->DungeonRun;Next.ForgeJob=Reply->ForgeJob;Next.GunAssemblyJob=Reply->GunAssemblyJob;Next.WoodworkingJob=Reply->WoodworkingJob;Next.AlchemyJob=Reply->AlchemyJob;Next.EnhancementItem=Reply->EnhancementItem;}
    ColdSteelProfileRecovery::StationProgress(Next,Current);
    FString Reason;
    if(!ColdSteelInventory::Validate(Next,Reason))
    {
        if(IsAudit())
        {
            UE_LOG(LogTemp,Display,TEXT("INVENTORY_REPLY_AUDIT invalid revision=%lld old=%lld items=%d hotbar=%d definitions=%d attributes=%d hp=%f mana=%f reason=%s"),Next.CampfireInventoryRevision,Current.CampfireInventoryRevision,Next.Items.Num(),Next.Hotbar.Num(),Next.HotbarDefinitions.Num(),Next.Attributes.Num(),Next.Health,Next.Mana,*Reason);
            for(const auto& I:Current.Items)UE_LOG(LogTemp,Display,TEXT("INVENTORY_REPLY_AUDIT before %s %s place=%d cell=%d size=%dx%d"),*I.InstanceId,*I.Definition,I.Place,I.Cell,I.Width,I.Height);
            for(const auto& I:Next.Items)UE_LOG(LogTemp,Display,TEXT("INVENTORY_REPLY_AUDIT after %s %s place=%d cell=%d size=%dx%d"),*I.InstanceId,*I.Definition,I.Place,I.Cell,I.Width,I.Height);
        }
        Message=Reason;return false;
    }
    AdoptNetMirror(Next,true);
    if(bMountBagOpen)
    {
        FGuid OpenMountId;
        if(!StableHorseAffixes::TryParseBagContainer(ActiveContainer,OpenMountId) || !Current.MountRoster.Find(OpenMountId))
            EndMountBagSession();
    }
    // Publish immediately; the normal local save policy persists the receipt.
    if(SameLivingPawn)ApplyToPawn();
    OnChanged.Broadcast();
    return PersistState(Snapshot(),false);
}
