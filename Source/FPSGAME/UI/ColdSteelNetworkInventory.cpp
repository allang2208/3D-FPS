#include "ColdSteelStatusModel.h"
#include "ColdSteelCurrency.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelProfileRecovery.h"
#include "../Monsters/FPSCombatHealthComponent.h"

bool UColdSteelStatusModel::ApplyNetworkInventoryReply(const UColdSteelInventoryReply* Reply,APawn* ExpectedPawn)
{
    if(!Reply||!Reply->bSuccess||Reply->Revision<Current.CampfireInventoryRevision)return false;
    SyncRuntime();auto Next=Snapshot();
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
    const auto* Health=CurrentPawn.IsValid()?CurrentPawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool SameLivingPawn=CurrentPawn.Get()==ExpectedPawn&&Health&&!Health->IsDead();
    if(Reply->bResourcesChanged&&SameLivingPawn)
    {Next.Mana=FMath::Min(float(ResourceMaximum(Next,true)),Next.Mana+Reply->ManaRestored);}
    if(SameLivingPawn&&Reply->StaminaSpent>0.f)
    {Next.Stamina=FMath::Max(0.f,Next.Stamina-Reply->StaminaSpent);Next.StaminaRecoveryDelay=StaminaTuning.RecoveryDelay;}
    if(Reply->bWorldAction){Next.DungeonRun=Reply->DungeonRun;Next.ForgeJob=Reply->ForgeJob;Next.GunAssemblyJob=Reply->GunAssemblyJob;Next.WoodworkingJob=Reply->WoodworkingJob;Next.AlchemyJob=Reply->AlchemyJob;}
    ColdSteelProfileRecovery::AlchemyProgress(Next,Current);
    FString Reason;
    if(!ColdSteelInventory::Validate(Next,Reason)){Message=Reason;return false;}
    AdoptNetMirror(Next,true);
    // Publish immediately; the normal local save policy persists the receipt.
    if(SameLivingPawn)ApplyToPawn();
    OnChanged.Broadcast();
    return PersistState(Snapshot(),false);
}
