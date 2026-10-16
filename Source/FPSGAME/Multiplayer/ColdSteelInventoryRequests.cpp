#include "ColdSteelPlayerState.h"
#include "../Building/AlchemySystem.h"
#include "../UI/ColdSteelShopModel.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Building/WoodworkingSystem.h"
#include "ColdSteelProfileTransfer.h"
#include "ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelPickup.h"
#include "../UI/ColdSteelWarehouseChest.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/NetConnection.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/SecureHash.h"

bool AColdSteelPlayerState::RequestInventoryAction(EColdSteelInventoryAction Action,const FString& Item,AActor* Target)
{
    FColdSteelInventoryRequest Request;Request.Action=Action;Request.Item=Item;Request.Target=Target;
    return RequestInventoryAction(Request);
}
TArray<uint8> AColdSteelPlayerState::InventoryBaseline(const FColdSteelProfile& Profile)
    {
        auto* Save=NewObject<UColdSteelProfileSave>();
        Save->Profile.Items=Profile.Items;Save->Profile.AmmoPouch=Profile.AmmoPouch;
        for(auto& Item:Save->Profile.Items)Item.Cooldown=0.f;
        Save->Profile.ActiveWeaponSlot=Profile.ActiveWeaponSlot;Save->Profile.ActiveProductionTool=Profile.ActiveProductionTool;
        Save->Profile.CampfireInventoryRevision=Profile.CampfireInventoryRevision;
        TArray<uint8> Blob;ColdSteelProfileTransfer::SaveToBlob(Save,Blob);return Blob;
    }
bool AColdSteelPlayerState::RequestInventoryAction(FColdSteelInventoryRequest Request)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(GetNetMode()==NM_Standalone||!PC||!PC->IsLocalController()||!PC->GetPawn()||!Model
        ||bInventoryRequestPending||bCampfirePending)return false;
    if(TeamTravelId.IsValid()){Model->PostNotice(TEXT("队伍换图"),TEXT("正在保存档案，请稍候"));return false;}
    Request.Sequence=++InventoryRequestSequence;
    if(!Request.Sequence)Request.Sequence=++InventoryRequestSequence;
    Request.Revision=Model->Snapshot().CampfireInventoryRevision;
    Request.Pawn=PC->GetPawn();
    bInventoryRequestPending=true;
    InventoryRequestPawn=PC->GetPawn();
    InventoryReplyIncoming.Reset();InventoryReplyTotal=0;
    PendingInventoryRequest=Request;
    if(HasAuthority()){ServerInventoryAction_Implementation(Request);return true;}
    // Don't allow a pre-transaction snapshot to finish after the item receipt.
    Model->SyncRuntime();
    const auto Baseline=InventoryBaseline(Model->Snapshot());
    const auto Currency=Model->Snapshot();
    const bool TradeReady=Request.Action!=EColdSteelInventoryAction::Shop||(Currency.Souls==ConfirmedSouls&&Currency.ServerSoulCredits==ConfirmedSoulCredits&&Currency.ServerSoulDebits==ConfirmedSoulDebits);
    if(TradeReady&&!Baseline.IsEmpty()&&Baseline==AcknowledgedInventoryBaseline)
    {
        PendingUpload.Reset();PendingNormBlob.Reset();
        Model->SetCampfireInventoryPending(true);PendingInventoryRequest=Request;
        ServerInventoryAction(Request);return true;
    }
    if(Request.Action==EColdSteelInventoryAction::BowShot)
    {
        bInventoryRequestPending=false;InventoryRequestPawn.Reset();HeartbeatTimer=0.f;
        Model->PostNotice(TEXT("装备正在同步"),TEXT("请稍后重新拉弓"));return false;
    }
    if(!ScratchSave)ScratchSave=NewObject<UColdSteelProfileSave>();
    ScratchSave->Profile=Model->Snapshot();
    PendingUpload.Reset();PendingNormBlob.Reset();
    if(!ColdSteelProfileTransfer::SaveToBlob(ScratchSave,PendingUpload))
    {bInventoryRequestPending=false;InventoryRequestPawn.Reset();return false;}
    PendingNormBlob=PendingUpload;PendingUploadId=++UploadCounter;NextChunkIndex=0;
    PendingSuper90Revision=Super90AppliedRevision;PendingUploadPawn=PC->GetPawn();
    PendingTotalChunks=FMath::DivideAndRoundUp(PendingUpload.Num(),ProfileChunkSize);
    bInventoryWaitingUpload=true;PendingInventoryRequest=Request;
    Model->SetCampfireInventoryPending(true);
    return true;
}
void AColdSteelPlayerState::SendInventoryBaseline()
{
    if(!ShadowModel)return;
    const auto Blob=InventoryBaseline(ShadowModel->Snapshot());
    FSHAHash Hash;FSHA1::HashBuffer(Blob.GetData(),Blob.Num(),Hash.Hash);
    const auto P=ShadowModel->Snapshot();
    ClientInventoryBaseline(Hash.ToString(),P.Souls,P.ServerSoulCredits,P.ServerSoulDebits);
}
void AColdSteelPlayerState::ClientInventoryBaseline_Implementation(const FString& Digest,int64 Souls,int64 Credits,int64 Debits)
{
    if(bInventoryRequestPending||bCampfirePending)return;
    ConfirmedSouls=Souls;ConfirmedSoulCredits=Credits;ConfirmedSoulDebits=Debits;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        Model->SyncRuntime();auto Blob=InventoryBaseline(Model->Snapshot());
        FSHAHash Hash;FSHA1::HashBuffer(Blob.GetData(),Blob.Num(),Hash.Hash);
        if(Hash.ToString()==Digest)AcknowledgedInventoryBaseline=MoveTemp(Blob);
    }
}
void AColdSteelPlayerState::DispatchInventoryAfterUpload()
{
    if(!bInventoryWaitingUpload)return;
    bInventoryWaitingUpload=false;
    ServerInventoryAction(PendingInventoryRequest);
}
void AColdSteelPlayerState::ServerWarehouseOpen_Implementation(AColdSteelWarehouseChest* Chest,bool Open)
{
    if(!IsValid(Chest)||Chest->GetWorld()!=GetWorld()||!GetPawn())return;
    if(Open&&!Chest->IsWithinReach(GetPawn()))return;
    Chest->SetOpenFor(GetPawn(),Open);
}

void AColdSteelPlayerState::ServerInventoryAction_Implementation(const FColdSteelInventoryRequest& Request)
{
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!HasAuthority()||!PC||PC->PlayerState!=this||!Request.Sequence
        ||static_cast<int32>(Request.Sequence-LastInventoryRequestSequence)<=0)return;
    LastInventoryRequestSequence=Request.Sequence;
    InvalidateTeamTravelReady();
    auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());
    auto* Model=PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():ShadowModel.Get();
    if(Model)Model->SyncRuntime();
    const auto Before=Model?Model->Snapshot():FColdSteelProfile{};
    FString Reason;bool Success=false;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!Pawn||Request.Pawn!=Pawn||!Health||Health->IsDead())Reason=TEXT("角色已变化或无法操作");
    else if(!Model)Reason=TEXT("角色档案正在同步，请稍后重试");
    else if(Model->HasUnconfirmedTransactionSave())Reason=TEXT("交易保存结果待恢复，当前不能继续扣费或领取");
    else if(Request.Revision!=Before.CampfireInventoryRevision)Reason=TEXT("库存正在更新，请稍后重试");
    else if(Request.Action==EColdSteelInventoryAction::Shrine)
    {if(auto* Run=UDungeonRunSubsystem::Get(GetWorld()))Success=Run->ClaimShrine(PC,Request.Target);Reason=Success?TEXT("已获得本次地牢赐福"):TEXT("神龛不可达或已领取");}
    else if(Request.Action==EColdSteelInventoryAction::Shop)
        Success=UColdSteelShopModel::ExecuteNetworkTrade(Model,Request,PC->IsLocalController()?FString():SlotName,Reason);
    else if(Request.Action>=EColdSteelInventoryAction::Harvest)
        Success=ExecuteWorldAction(Request,Model,Reason);
    else if(Request.Action==EColdSteelInventoryAction::Consume)
    {
        Success=Model->UseConsumableAtContact(Request.Item,true);
        Reason=Success?TEXT("已使用物品"):Model->ResultMessage();
    }
    else if(Request.Action==EColdSteelInventoryAction::BowShot)
        Success=ExecuteBowShot(Request,Model,Reason);
    else if(Request.Action==EColdSteelInventoryAction::RecoverArrow)
    {
        if(auto* Arrow=Cast<ABowArrow>(Request.Target))Success=Arrow->TryRecover(Pawn);
        Reason=Success?TEXT("已拾回箭支"):TEXT("箭支不可达或已被拾取");
    }
    else if(Request.Action>=EColdSteelInventoryAction::ContainerOpen&&Request.Action<=EColdSteelInventoryAction::ContainerRetrieveAll)
    {
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())
            Success=Shared->ContainerOperation(Model,PC->IsLocalController()?nullptr:this,Request,Reason);
    }
    else if(Request.Action==EColdSteelInventoryAction::Fountain)
    {
        if(ColdSteelWorldInteraction::IsBlessingFountain(Request.Target)
            &&ColdSteelWorldInteraction::TraceTarget(PC)==Request.Target)
        {
            if(auto* Survival=Pawn->FindComponentByClass<UFPSSurvivalComponent>())
            {
                const auto Previous=Survival->GetState();
                if(Survival->DrinkBlessedWater())
                {
                    Model->SyncRuntime();
                    Success=Model->CommitCampfireState(Model->Snapshot(),TEXT("Inventory"),PC->IsLocalController()?FString():SlotName);
                    if(!Success){Survival->RestoreState(Previous);Model->AdoptNetMirror(Before);}
                }
            }
        }
        Reason=Success?TEXT("清泉赐福：缺水度已补满"):TEXT("泉水不可达或保存失败");
    }
    else if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())
    {
        auto* Guest=PC->IsLocalController()?nullptr:this;
        switch(Request.Action)
        {
        case EColdSteelInventoryAction::Drop:Success=Shared->Drop(Model,Guest,Request.Item,Reason);break;
        case EColdSteelInventoryAction::Pickup:Success=Shared->Pickup(Model,Guest,Cast<AColdSteelPickup>(Request.Target),false,Reason);break;
        case EColdSteelInventoryAction::PickupNearby:Success=Shared->PickupNearby(Model,Guest,Reason);break;
        default:Reason=TEXT("未知物品操作");break;
        }
    }
    if(Reason.IsEmpty())Reason=TEXT("物品已变化或当前无法使用");
    const auto After=Model?Model->Snapshot():Before;
    QueueInventoryReply(Request,Success,Reason,Before,After);
    if(Success)
    {
        bServerDirty=true;ServerSaveTimer=20.f;
        Pawn->ForceNetUpdate();SendSuper90Ammo();
    }
    else if(Model){ShadowMirrorTimer=3.f;}
}

void AColdSteelPlayerState::QueueInventoryReply(const FColdSteelInventoryRequest& Request,bool Success,
    const FString& Reason,const FColdSteelProfile& Before,const FColdSteelProfile& After)
{
    auto* Reply=NewObject<UColdSteelInventoryReply>();
    Reply->Sequence=Request.Sequence;Reply->Revision=After.CampfireInventoryRevision;
    Reply->bSuccess=Success;Reply->Message=Reason;Reply->WorldReceipts=After.CampfireWorldReceipts;
    if(Request.Action>=EColdSteelInventoryAction::ContainerOpen&&Request.Action<=EColdSteelInventoryAction::ContainerRetrieveAll)
        if(auto* Shared=GetWorld()->GetSubsystem<UColdSteelSharedInventorySubsystem>())
        {
            const auto* OwnerPC=Cast<APlayerController>(GetOwner());
            Shared->FillContainerReply(Request.Target,Reply,OwnerPC?OwnerPC->GetPawn().Get():nullptr);
        }
    Reply->ServerSoulCredits=After.ServerSoulCredits;Reply->ServerSoulDebits=After.ServerSoulDebits;
    Reply->bWorldAction=Request.Action>=EColdSteelInventoryAction::Shrine&&Request.Action<=EColdSteelInventoryAction::Workstation;
    if(Reply->bWorldAction){Reply->DungeonRun=After.DungeonRun;Reply->ForgeJob=After.ForgeJob;Reply->GunAssemblyJob=After.GunAssemblyJob;Reply->WoodworkingJob=After.WoodworkingJob;Reply->AlchemyJob=After.AlchemyJob;}
    if(Success)
    {
        for(const auto& Item:After.Items)
        {
            const auto* Old=Before.Items.FindByPredicate([&](const auto& V){return V.InstanceId==Item.InstanceId;});
            if(!Old||!FColdSteelItem::StaticStruct()->CompareScriptStruct(Old,&Item,0))Reply->Changed.Add(Item);
        }
        for(const auto& Item:Before.Items)
            if(!After.Items.ContainsByPredicate([&](const auto& V){return V.InstanceId==Item.InstanceId;}))Reply->Removed.Add(Item.InstanceId);
        for(const auto& Pair:After.AmmoPouch)
        {
            const int64 Delta=Pair.Value-Before.AmmoPouch.FindRef(Pair.Key);
            if(Delta)Reply->PouchDelta.Add(Pair.Key,Delta);
        }
        for(const auto& Pair:Before.AmmoPouch)
            if(!After.AmmoPouch.Contains(Pair.Key)&&Pair.Value)Reply->PouchDelta.Add(Pair.Key,-Pair.Value);
        Reply->bResourcesChanged=Request.Action==EColdSteelInventoryAction::Consume;
        Reply->ManaRestored=FMath::Max(0.f,After.Mana-Before.Mana);
        if(Request.Action==EColdSteelInventoryAction::BowShot||Request.Action==EColdSteelInventoryAction::Harvest)Reply->StaminaSpent=FMath::Max(0.f,Before.Stamina-After.Stamina);
        Reply->bEquipmentChanged=Before.ActiveWeaponSlot!=After.ActiveWeaponSlot||Before.ActiveProductionTool!=After.ActiveProductionTool;
        Reply->ActiveWeaponSlot=After.ActiveWeaponSlot;Reply->ActiveProductionTool=After.ActiveProductionTool;
    }
    InventoryReplyOutgoing.Reset();InventoryReplyChunk=0;ReplySequence=Request.Sequence;
    if(auto* PC=Cast<APlayerController>(GetOwner());PC&&PC->IsLocalController())
    {
        bInventoryRequestPending=false;
        if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        {Model->ApplyNetworkContainerView(Reply,Request.Target);Model->PostNotice(TEXT("物品操作"),Reason);}
        if(Request.Action==EColdSteelInventoryAction::Shop)GetGameInstance()->GetSubsystem<UColdSteelShopModel>()->NetworkTradeFinished(Success,Reason);
        InventoryRequestPawn.Reset();return;
    }
    if(!ColdSteelProfileTransfer::SaveToBlob(Reply,InventoryReplyOutgoing))
    {
        // An unrepresentable receipt must not strand the owning UI's pending lock.
        Reply->Changed.Reset();Reply->Removed.Reset();Reply->PouchDelta.Reset();Reply->ContainerItems.Reset();Reply->bContainerView=false;
        Reply->bSuccess=false;Reply->bResourcesChanged=false;
        Reply->Message=TEXT("操作结果等待完整档案同步");
        ColdSteelProfileTransfer::SaveToBlob(Reply,InventoryReplyOutgoing);
        ShadowMirrorTimer=3.f;
    }
    TickInventoryReply();
}

void AColdSteelPlayerState::TickInventoryReply()
{
    if(InventoryReplyOutgoing.IsEmpty())return;
    auto* PC=Cast<APlayerController>(GetOwner());
    UNetConnection* Connection=PC?PC->GetNetConnection():nullptr;
    if(!Connection||!Connection->IsNetReady())return;
    const double Now=GetWorld()->GetRealTimeSeconds();
    const double Rate=FMath::Min(16.*1024.,double(Connection->CurrentNetSpeed)*.2);
    if(Rate<=0.||Now-LastInventoryReplyAt<(ProfileChunkSize+256.)/Rate)return;
    const int32 Total=FMath::DivideAndRoundUp(InventoryReplyOutgoing.Num(),ProfileChunkSize);
    const int32 Start=InventoryReplyChunk*ProfileChunkSize;
    TArray<uint8> Chunk;
    Chunk.Append(InventoryReplyOutgoing.GetData()+Start,FMath::Min(ProfileChunkSize,InventoryReplyOutgoing.Num()-Start));
    ClientInventoryReplyChunk(ReplySequence,InventoryReplyChunk,Total,Chunk);
    LastInventoryReplyAt=Now;
    if(++InventoryReplyChunk==Total)InventoryReplyOutgoing.Reset();
}

void AColdSteelPlayerState::ClientInventoryReplyChunk_Implementation(uint32 Sequence,int32 Index,int32 Total,const TArray<uint8>& Chunk)
{
    if(!bInventoryRequestPending||Sequence!=InventoryRequestSequence||Total<=0||Total>ColdSteelProfileTransfer::MaxChunks
        ||Index<0||Index>=Total||Chunk.IsEmpty()||Chunk.Num()>ProfileChunkSize)return;
    if(Index==0){InventoryReplyIncoming.Reset();InventoryReplyTotal=Total;}
    if(Total!=InventoryReplyTotal||Index*ProfileChunkSize!=InventoryReplyIncoming.Num())return;
    InventoryReplyIncoming.Append(Chunk);
    if(Index+1!=Total)return;
    auto* Reply=NewObject<UColdSteelInventoryReply>();
    const bool Decoded=ColdSteelProfileTransfer::BlobToSaveObject(InventoryReplyIncoming,Reply)&&Reply->Sequence==Sequence;
    InventoryReplyIncoming.Reset();bInventoryRequestPending=bInventoryWaitingUpload=false;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        Model->SetCampfireInventoryPending(false);
        const bool Applied=Decoded&&(!Reply->bSuccess||Model->ApplyNetworkInventoryReply(Reply,InventoryRequestPawn.Get()));
        if(PendingInventoryRequest.Mode.StartsWith(TEXT("alchemy.")))
            GetGameInstance()->GetSubsystem<UColdSteelAlchemySystem>()->NetworkFinished(PendingInventoryRequest.Mode,Decoded&&Reply->bSuccess&&Applied,
                Decoded&&Applied?Reply->Message:TEXT("炼药结果正在重新同步"));
        if(PendingInventoryRequest.Mode.StartsWith(TEXT("wood.")))
            GetGameInstance()->GetSubsystem<UWoodworkingSystem>()->NetworkTransactionFinished(PendingInventoryRequest.Mode,Decoded&&Reply->bSuccess&&Applied,
                Decoded&&Applied?Reply->Message:TEXT("工件结算正在重新同步"));
        if(PendingInventoryRequest.Action==EColdSteelInventoryAction::Shop)
            GetGameInstance()->GetSubsystem<UColdSteelShopModel>()->NetworkTradeFinished(Decoded&&Reply->bSuccess,
                Decoded&&Applied?Reply->Message:TEXT("交易结果等待档案同步"));
        if(Applied&&Reply->bSuccess)AcknowledgedInventoryBaseline=InventoryBaseline(Model->Snapshot());
        else AcknowledgedInventoryBaseline.Reset();
        const bool InitialOpen=PendingInventoryRequest.Action==EColdSteelInventoryAction::ContainerOpen&&PendingInventoryRequest.Count==0;
        if(Decoded&&InventoryRequestPawn.Get()==GetPawn()&&(InitialOpen||Model->bWarehouseOpen))
            Model->ApplyNetworkContainerView(Reply,PendingInventoryRequest.Target);
        Model->PostNotice(TEXT("联机物品操作"),Applied?Reply->Message:TEXT("结果正在重新同步"));
    }
    if(Decoded&&Reply->bSuccess)AcknowledgeInventoryProfile();else {bHasLastSent=false;HeartbeatTimer=0.f;}
    InventoryRequestPawn.Reset();
}
void AColdSteelPlayerState::ClientContainerInvalidated_Implementation(AActor* Target)
{
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(Model->NetworkContainerAnchor.Get()==Target&&Model->bWarehouseOpen)bContainerNeedsRefresh=true;
}
void AColdSteelPlayerState::TickContainerRefresh()
{
    if(!bContainerNeedsRefresh||bInventoryRequestPending||bCampfirePending)return;
    auto* PC=Cast<APlayerController>(GetOwner());
    auto* Model=PC&&PC->IsLocalController()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!Model||!Model->bWarehouseOpen){bContainerNeedsRefresh=false;return;}
    if(Model->RequestContainerOperation(uint8(EColdSteelInventoryAction::ContainerOpen)))bContainerNeedsRefresh=false;
}
