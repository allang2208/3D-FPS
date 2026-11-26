#include "VillageDefenseState.h"
#include "VillageSiegeUpgrades.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelCurrency.h"
#include "../UI/ColdSteelStatusModel.h"

namespace { FString Slot(const FGuid& Id){return TEXT("VillageDefenses_")+Id.ToString(EGuidFormats::Digits);} }
UVillageDefenseSave* UVillageDefenseState::Load(const FGuid& Id)
{
    if(auto* Existing=Saves.Find(Id))return *Existing;
    auto* Save=Cast<UVillageDefenseSave>(UGameplayStatics::LoadGameFromSlot(Slot(Id),0));
    if(!Save||Save->WorldId!=Id||Save->Version!=1)
    {Save=NewObject<UVillageDefenseSave>(this);Save->WorldId=Id;}
    Saves.Add(Id,Save);return Save;
}
uint16 UVillageDefenseState::SelectGeneration(const FGuid& Id,const FGuid& Generation)
{
    auto* Save=Load(Id);
    if(Save->Generation==Generation)
    {
        if(!bPurchasing && Save->PendingRepair.IsPending())RecoverRepair(*Save);
        return Save->SiegeRanks;
    }
    // The hills slot has already committed this reset. Even after an interrupted
    // sidecar write, that slot selects a fresh set of health values on reload.
    Save->Generation=Generation;
    Save->DamagedSections.Reset();
    Save->SiegeRanks=0;
    if(!Save->PendingRepair.PlacedId.IsValid())Save->PendingRepair={};
    else if(!bPurchasing)RecoverRepair(*Save);
    WriteNow(*Save);
    return Save->SiegeRanks;
}
bool UVillageDefenseState::WriteNow(UVillageDefenseSave& Save)
{
    if(UGameplayStatics::SaveGameToSlot(&Save,Slot(Save.WorldId),0))
    {Dirty.Remove(Save.WorldId);return true;}
    Dirty.Add(Save.WorldId);
    GetWorld()->GetTimerManager().SetTimer(SaveTimer,this,&ThisClass::Flush,2.f,false);
    return false;
}

void UVillageDefenseState::RecoverRepair(UVillageDefenseSave& Save)
{
    const FVillagePendingRepair& Pending=Save.PendingRepair;
    if(!Pending.IsPending())return;
    const FString Receipt=Slot(Save.WorldId);
    int64 Committed=0;
    if(Pending.bGuest)
    {
        if(UGameplayStatics::DoesSaveGameExist(Pending.PlayerSlot,0))
        {
            const auto* Profile=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(Pending.PlayerSlot,0));
            if(!Profile)return;
            Committed=Profile->Profile.CampfireWorldReceipts.FindRef(Receipt);
        }
    }
    else
    {
        const auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        if(!Model||Model->ProfileSlot()!=Pending.PlayerSlot||Model->HasUnconfirmedTransactionSave())return;
        Committed=Model->Snapshot().CampfireWorldReceipts.FindRef(Receipt);
    }
    if(Pending.ProfileRevision<=0||Committed>Pending.ProfileRevision)return;
    if(Committed==Pending.ProfileRevision)
        ApplyPaidWork(Save);
    Save.PendingRepair={};
    WriteNow(Save);
}

void UVillageDefenseState::ApplyPaidWork(UVillageDefenseSave& Save)
{
    const auto& Work=Save.PendingRepair;
    if(VillageSiegeUpgrades::Valid(Work.UpgradeIndex))
    {
        if(VillageSiegeUpgrades::Rank(Save.SiegeRanks,Work.UpgradeIndex)<VillageSiegeUpgrades::MaxRank)
            Save.SiegeRanks+=uint16(1u << (2*Work.UpgradeIndex));
    }
    else if(Work.PlacedId.IsValid())Save.DamagedPlacedSections.Remove(Work.PlacedId);
    else Save.DamagedSections.Remove(Work.Section);
}

bool UVillageDefenseState::PurchaseUpgrade(const FGuid& Id,int32 Index,int32 ExpectedRank,APawn* Payer,FText& Failure)
{
    if(!VillageSiegeUpgrades::Valid(Index) || !VillageSiegeUpgrades::Price(ExpectedRank))
    { Failure=FText::FromString(TEXT("该项目无法继续升级。")); return false; }
    FVillagePendingRepair Work;
    Work.UpgradeIndex=Index;
    return Purchase(Id,Payer,VillageSiegeUpgrades::Price(ExpectedRank),Work,ExpectedRank,Failure);
}

bool UVillageDefenseState::PurchaseRepair(const FGuid& Id,int32 Section,APawn* Payer,int32 Cost,FText& Failure,const FGuid& PlacedId,float ExpectedHealth)
{
    FVillagePendingRepair Work;
    Work.Section=Section;
    Work.PlacedId=PlacedId;
    return Purchase(Id,Payer,Cost,Work,ExpectedHealth,Failure);
}

bool UVillageDefenseState::Purchase(const FGuid& Id,APawn* Payer,int32 Cost,const FVillagePendingRepair& Work,float Expected,FText& Failure)
{
    Failure=FText::GetEmpty();
    auto* Controller=Payer?Cast<APlayerController>(Payer->GetController()):nullptr;
    if(!Controller||Controller->GetPawn()!=Payer||!Payer->HasAuthority()||Payer->GetWorld()!=GetWorld()||
        !Id.IsValid()||!Work.IsPending()||Cost<=0||bPurchasing)
    {Failure=FText::FromString(TEXT("暂时无法结算城防费用。"));return false;}
    TGuardValue<bool> Guard(bPurchasing,true);
    auto* Model=ColdSteelAuthority::ForPawn(Payer);
    const bool bGuest=!Controller->IsLocalController();
    auto* PS=Payer->GetPlayerState<AColdSteelPlayerState>();
    if(!Model||Model->IsStagingNetworkContainer()||Model->HasUnconfirmedTransactionSave()||
        (bGuest&&(!PS||!PS->IsGuestInitialized()||PS->GetShadowModel()!=Model)))
    {Failure=FText::FromString(TEXT("灵魂档案尚未就绪。"));return false;}
    const FString PlayerSlot=bGuest?PS->CampfireGuestSlot():Model->ProfileSlot();
    auto* Save=Load(Id);
    if(Save->PendingRepair.IsPending())RecoverRepair(*Save);
    if(PlayerSlot.IsEmpty() || Save->PendingRepair.IsPending())
    {Failure=FText::FromString(TEXT("城防账本正在结算。"));return false;}
    if(Work.UpgradeIndex!=INDEX_NONE)
    {
        if(VillageSiegeUpgrades::Rank(Save->SiegeRanks,Work.UpgradeIndex)!=int32(Expected))
        {Failure=FText::FromString(TEXT("该项目等级已变更，请按最新报价升级。"));return false;}
    }
    else
    {
        const float* Damage=Work.PlacedId.IsValid()?Save->DamagedPlacedSections.Find(Work.PlacedId):Save->DamagedSections.Find(Work.Section);
        if(!Damage || FMath::Max(0.f,*Damage)!=Expected)
        {Failure=FText::FromString(TEXT("城防存档尚未准备好修复。"));return false;}
    }
    Model->SyncRuntime();
    auto Profile=Model->Snapshot();
    if(Profile.CampfireInventoryRevision==MAX_int64||(bGuest&&Profile.ServerSoulDebits>ColdSteelCurrency::MaxSouls-Cost))
    {Failure=FText::FromString(TEXT("灵魂账本无法结算。"));return false;}
    if(!ColdSteelCurrency::Debit(Profile,Cost))
    {Failure=FText::FromString(TEXT("灵魂不足。"));return false;}
    if(bGuest)Profile.ServerSoulDebits+=Cost;

    Save->PendingRepair=Work;
    Save->PendingRepair.PlayerSlot=PlayerSlot;
    Save->PendingRepair.bGuest=bGuest;
    Save->PendingRepair.ProfileRevision=Profile.CampfireInventoryRevision+1;
    if(!WriteNow(*Save))
    {
        Save->PendingRepair={};
        Failure=FText::FromString(TEXT("城防记录未能保存。"));return false;
    }
    if(!Model->CommitCampfireState(MoveTemp(Profile),Slot(Id),bGuest?PlayerSlot:FString()))
    {
        if(!Model->HasUnconfirmedTransactionSave())
        {
            Save->PendingRepair={};
            WriteNow(*Save);
        }
        Failure=FText::FromString(Model->ResultMessage());return false;
    }
    // The paid receipt and the durable intent can replay the wall even if this
    // final checkpoint fails. Further hits update the same cached world state.
    ApplyPaidWork(*Save);
    Save->PendingRepair={};
    WriteNow(*Save);
    return true;
}
float UVillageDefenseState::Restore(const FGuid& Id,int32 Section,float Default,const FGuid& PlacedId)
{
    if(!Id.IsValid())return Default;
    auto* Save=Load(Id);
    const float* Value=PlacedId.IsValid()?Save->DamagedPlacedSections.Find(PlacedId):Save->DamagedSections.Find(Section);
    return Value?FMath::Clamp(*Value,0.f,Default):Default;
}
void UVillageDefenseState::Record(const FGuid& Id,int32 Section,float Health,const FGuid& PlacedId)
{
    if(!Id.IsValid()||GetWorld()->GetNetMode()==NM_Client)return;
    auto* Save=Load(Id);
    if(PlacedId.IsValid())Save->DamagedPlacedSections.Add(PlacedId,Health);
    else Save->DamagedSections.Add(Section,Health);
    Dirty.Add(Id);
    if(Health<=0.f)Flush();
    else if(!GetWorld()->GetTimerManager().IsTimerActive(SaveTimer))
        GetWorld()->GetTimerManager().SetTimer(SaveTimer,this,&UVillageDefenseState::Flush,2.f,false);
}
void UVillageDefenseState::ForgetPlaced(const FGuid& Id,const TSet<FGuid>& Removed)
{
    auto* Save=Load(Id);
    int32 Forgotten=0;
    for(const auto& RemovedId:Removed)Forgotten+=Save->DamagedPlacedSections.Remove(RemovedId);
    if(Forgotten)WriteNow(*Save);
}
void UVillageDefenseState::Flush()
{
    for(auto It=Dirty.CreateIterator();It;++It)
        if(UGameplayStatics::SaveGameToSlot(Saves.FindChecked(*It),Slot(*It),0))It.RemoveCurrent();
        else UE_LOG(LogTemp,Error,TEXT("VILLAGE_DEFENSE save failed world=%s"),*It->ToString());
    if(!Dirty.IsEmpty())
        GetWorld()->GetTimerManager().SetTimer(SaveTimer,this,&ThisClass::Flush,2.f,false);
}
void UVillageDefenseState::Deinitialize()
{Flush();GetWorld()->GetTimerManager().ClearTimer(SaveTimer);Super::Deinitialize();}
