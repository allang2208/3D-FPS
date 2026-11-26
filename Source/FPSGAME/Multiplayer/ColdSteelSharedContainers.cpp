#include "ColdSteelSharedInventorySubsystem.h"
#include "../UI/ColdSteelContainerSearchSubsystem.h"
#include "ColdSteelPlayerState.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../UI/ColdSteelSceneLoot.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelDungeonLoot.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/ColdSteelWarehouseRules.h"
#include "../Items/FoodSpoilage.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
using namespace ColdSteelInventory;

namespace
{
bool MigrateChangedFootprints(TArray<FColdSteelItem>& Items,int32& Pages,bool& Changed,FString& Reason)
{
    Changed=false;
    for(int32 N=0;N<Items.Num();++N)
    {
        auto& Item=Items[N];
        if(Item.Definition!=TEXT("alchemy_compound_stabilizer")&&Item.Definition!=TEXT("ue_tactical_magazine_belt")
            &&Item.Definition!=TEXT("ue_melee_combat_belt")&&Item.Definition!=TEXT("ue_arcane_conduit_belt"))continue;
        bool ItemChanged=false;
        if(!MigrateAuthoredItemFootprint(Item,ItemChanged,Reason))return false;
        if(!ItemChanged)continue;
        auto Others=Items;Others.RemoveAt(N);
        if(!ColdSteelWarehouse::Fits(Others,Item,Item.Cell,Pages*ColdSteelWarehouse::CellsPerPage))
        {
            int32 Cell=INDEX_NONE;
            while(Cell==INDEX_NONE)
            {
                for(int32 C=0;C<Pages*ColdSteelWarehouse::CellsPerPage;++C)
                    if(ColdSteelWarehouse::Fits(Others,Item,C,Pages*ColdSteelWarehouse::CellsPerPage)){Cell=C;break;}
                if(Cell!=INDEX_NONE)break;
                if(Pages>=8){Reason=TEXT("物品占格迁移空间不足，保留原内容");return false;}
                ++Pages;
            }
            Item.Cell=Cell;
        }
        Changed=true;
    }
    return true;
}
bool CanAccessContainer(const APawn* Pawn,const AActor* Target)
{
    return UColdSteelContainerSearchSubsystem::CanAccess(Pawn,Target);
}
bool ResolveContainer(AActor* Target,FString& Key,int32& Pages,FString& Caption)
{
    return UColdSteelContainerSearchSubsystem::Resolve(Target,Key,Pages,Caption);
}
}
void UColdSteelSharedInventorySubsystem::FillContainerReply(AActor* Target,UColdSteelInventoryReply* Reply,const APawn* Viewer) const
{
    FString Key,Caption;int32 Pages=1;
    if(!Reply||!CanAccessContainer(Viewer,Target)||!ResolveContainer(Target,Key,Pages,Caption))return;
    const auto* Container=Current.Containers.Find(Key);if(!Container||!Container->bSeeded)return;
    Reply->bContainerView=true;Reply->ContainerKey=Key;Reply->ContainerCaption=Caption;
    Reply->ContainerPages=Container->Pages;Reply->ContainerRevision=Container->Revision;Reply->ContainerItems=Container->Items;
    if(auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>())Search->FillView(Cast<APlayerController>(Viewer->GetController()),*Reply);
}
bool UColdSteelSharedInventorySubsystem::ContainerOperation(UColdSteelStatusModel* Model,AColdSteelPlayerState* Guest,
    const FColdSteelInventoryRequest& Request,FString& Reason)
{
    FString Key,Caption;int32 Pages=1;
    auto* Pawn=Model?Model->RuntimePawn():nullptr;
    auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!InitializeAuthority()||!PC||!CanAccessContainer(Pawn,Request.Target)||Request.Target->GetWorld()!=GetWorld()
        ||!ResolveContainer(Request.Target,Key,Pages,Caption))
    {Reason=TEXT("容器不可达");return false;}
    FoodContainerAnchors.Add(Key,Request.Target);
    if(!SettleFoodSpoilage(Reason))return false;
    Model->SyncRuntime();const auto Before=Model->Snapshot();auto Working=Before;
    ColdSteelFood::RebaseProfile(Working,ColdSteelFood::Clock(this));
    UColdSteelStatusModel::StripNetworkContainerView(Working);
    CaptureDropTransforms();auto After=Current;auto& Container=After.Containers.FindOrAdd(Key);
    const bool Open=Request.Action==EColdSteelInventoryAction::ContainerOpen;
    auto* Search=GetWorld()->GetSubsystem<UColdSteelContainerSearchSubsystem>();
    if((!Open||Request.Count==-1)&&(!Search||!Search->IsActive(PC,Request.Target)))
    {Reason=TEXT("请重新打开容器开始搜索");return false;}
    auto* SearchScene=Cast<AColdSteelSceneContainer>(Request.Target);
    const bool SearchLoot=ColdSteelSceneLoot::IsBound(SearchScene);
    const FString LegacyKey=SearchLoot?SearchScene->LegacyStorageKey():Key;
    bool LegacyKeyChanged=false;
    // Older network saves used the map-only key; move the whole record, including contents.
    if(SearchLoot&&!Current.Containers.Contains(Key))
        if(const auto* Legacy=After.Containers.Find(LegacyKey))
        {const auto Copy=*Legacy;After.Containers.Remove(LegacyKey);After.Containers.FindChecked(Key)=Copy;
         for(auto& Item:Container.Items)Item.Container=Key;
         LegacyKeyChanged=true;}
    // The migrated record may have grown beyond the authored actor's page count.
    Pages=FMath::Clamp(FMath::Max(Pages,Container.Pages),1,8);Container.Pages=Pages;
    auto HasPrivate=[&](const FColdSteelProfile& Profile)
    {return Profile.Items.ContainsByPredicate([&](const auto& I){return I.Place==4&&(I.Container==Key||I.Container==LegacyKey);});};
    if(!Open&&(!Container.bSeeded||(SearchLoot&&!Container.bSceneLootResolved)))
    {Reason=TEXT("请先搜索此容器");return false;}
    // Changing from solo to co-op can leave a host-owned private claim/content.
    // Only the host can move that profile and shared inventory in one existing journal.
    if(Open&&Guest&&SearchLoot&&!Container.bSceneLootResolved)
        if(const auto* Host=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Host
            &&(HasPrivate(Host->Snapshot())||(UDungeonRunSubsystem::Get(GetWorld())&&Host->Snapshot().DungeonRun.RunId==UDungeonRunSubsystem::Get(GetWorld())->RunId()&&Host->HasDungeonClaim(ColdSteelSceneLoot::Claim(SearchScene->ContainerId)))))
        {Reason=TEXT("此旧存档容器需要房主先打开一次");return false;}
    if(Open&&Request.Target->ActorHasTag(TEXT("DungeonTreasure.HubTest"))&&Container.Items.IsEmpty())Container.bSeeded=false;
    bool FootprintChanged=false;
    if(Open&&!MigrateChangedFootprints(Container.Items,Pages,FootprintChanged,Reason))return false;
    Container.Pages=Pages;
    if(Open&&!LegacyKeyChanged&&!FootprintChanged&&Container.bSeeded&&(!SearchLoot||Container.bSceneLootResolved)&&!HasPrivate(Working))
    {
        if(Search)Search->Begin(PC,Request.Target);
        if(auto* Scene=Cast<AColdSteelSceneContainer>(Request.Target))Scene->OpenSharedVisual();
        else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())PS->MulticastSharedChestOpened(Request.Target);
        Reason=TEXT("已打开共享容器");return true;
    }
    if(!Open&&!Container.CanMutate(Request.ContainerRevision,SearchLoot))
    {Reason=TEXT("箱内物品已被更新，请重新操作");return false;}
    const FString ViewKey=TEXT("NetView.")+Key;
    bool Success=false;
    {
        TGuardValue<bool> Stage(Model->bStagingNetworkContainer,true);
        TGuardValue<bool> Warehouse(Model->bWarehouseOpen,true);
        TGuardValue<FString> Active(Model->ActiveContainer,ViewKey);
        TGuardValue<int32> Page(Model->WarehousePage,FMath::Clamp(Request.Page,0,Pages-1));
        // Migrate the host's former private cabinet contents exactly once, in
        // the same journal as the shared container and the host inventory.
        if(!Guest)
        {
            for(int32 I=Working.Items.Num()-1;I>=0;--I)
                if(Working.Items[I].Place==4&&(Working.Items[I].Container==Key||Working.Items[I].Container==LegacyKey))
                {
                    auto Item=Working.Items[I];Item.Container=Key;
                    if(!ColdSteelWarehouse::Insert(Container.Items,Item,Pages*ColdSteelWarehouse::CellsPerPage))
                    {Reason=TEXT("共享容器空间不足，旧存档物品保留");return false;}
                    Working.Items.RemoveAt(I);
                }
        }
        if(Open&&SearchLoot&&!Container.bSceneLootResolved)
        {
            if(Container.Items.IsEmpty())
            {
                if(!Model->AppendSceneSearchLoot(Working,SearchScene,Reason))return false;
                for(int32 I=Working.Items.Num()-1;I>=0;--I)
                    if(Working.Items[I].Place==4&&Working.Items[I].Container==Key)
                    {Container.Items.Add(Working.Items[I]);Working.Items.RemoveAt(I);}
            }
            // Existing stored items consume the initial rollout without adding rewards.
            Container.bSceneLootResolved=true;
            Working.DungeonRun.Claimed.Add(ColdSteelSceneLoot::Claim(SearchScene->ContainerId));
        }
        if(!Container.bSeeded&&ColdSteelWorldInteraction::IsTreasureChest(Request.Target))
        {
            Model->AdoptNetMirror(Working);FString LootKey;
            if(!FColdSteelDungeonLoot::StoreFromChest(Request.Target,LootKey,Model))
            {Model->AdoptNetMirror(Before);Reason=TEXT("宝箱战利品尚未就绪");return false;}
            Working=Model->Snapshot();
            for(int32 I=Working.Items.Num()-1;I>=0;--I)
                if(Working.Items[I].Place==4&&Working.Items[I].Container==Key)
                {Container.Items.Add(Working.Items[I]);Working.Items.RemoveAt(I);}
        }
        Working.StoragePages.Add(ViewKey,Pages);
        for(auto Item:Container.Items){Item.Container=ViewKey;Working.Items.Add(MoveTemp(Item));}
        Model->AdoptNetMirror(Working);
        switch(Request.Action)
        {
        case EColdSteelInventoryAction::ContainerOpen:Success=true;break;
        case EColdSteelInventoryAction::ContainerMove:Success=Model->MoveItem(Request.Item,Request.Place,Request.Cell,Request.Orientation);break;
        case EColdSteelInventoryAction::ContainerSplit:Success=Model->Split(Request.Item,Request.Count);break;
        case EColdSteelInventoryAction::ContainerBatch:Success=Model->WarehouseBatch(Request.Count!=0);break;
        case EColdSteelInventoryAction::ContainerSort:Success=Model->SortWarehouse(Request.Mode,Request.Place);break;
        case EColdSteelInventoryAction::ContainerStoreMatching:Success=Model->StoreMatchingToWarehouse();break;
        case EColdSteelInventoryAction::ContainerRetrieveAll:Success=Model->RetrieveAllFromWarehouse();break;
        default:break;
        }
        Reason=Model->ResultMessage();Working=Model->Snapshot();Model->AdoptNetMirror(Before);
    }
    if(!Success)return false;
    const auto PreviousItems=Container.Items;
    Container.Items.Reset();
    for(auto Item:Working.Items)if(Item.Container==ViewKey){Item.Container=Key;Container.Items.Add(MoveTemp(Item));}
    if(!Open&&Search&&!Search->ValidateChange(PC,PreviousItems,Container.Items,Reason))return false;
    const auto UpdatedItems=Container.Items;
    UColdSteelStatusModel::StripNetworkContainerView(Working);
    Container.bSeeded=true;++Container.Revision;
    if(!Commit(Model,Guest,MoveTemp(Working),MoveTemp(After),Reason))return false;
    if(Search){if(Open)Search->Begin(PC,Request.Target);else Search->ObserveChange(PC,PreviousItems,UpdatedItems);}
    if(auto* Scene=Cast<AColdSteelSceneContainer>(Request.Target))Scene->OpenSharedVisual();
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())PS->MulticastSharedChestOpened(Request.Target);
    if(Reason.IsEmpty()||!bBlocked)Reason=Open?TEXT("已打开共享容器"):TEXT("共享物品已更新");
    if(!Open||LegacyKeyChanged||FootprintChanged)for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
        if(*It!=Pawn->GetPlayerState<AColdSteelPlayerState>())It->ClientContainerInvalidated(Request.Target);
    return true;
}
