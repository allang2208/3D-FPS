#include "ColdSteelSharedInventorySubsystem.h"
#include "ColdSteelPlayerState.h"
#include "ColdSteelInventoryRequestTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelSceneContainer.h"
#include "../UI/ColdSteelSceneLoot.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelDungeonLoot.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../UI/ColdSteelWarehouseRules.h"
#include "../FPSGAMECharacter.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "EngineUtils.h"
using namespace ColdSteelInventory;

namespace
{
bool CanAccessContainer(const APawn* Pawn,const AActor* Target)
{
    if(!IsValid(Pawn)||!IsValid(Target)||Pawn->GetWorld()!=Target->GetWorld()||!Pawn->GetController()
        ||FVector::DistSquared(Pawn->GetActorLocation(),Target->GetActorLocation()+FVector(0,0,70))>FMath::Square(250.f))return false;
    if(const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SharedContainerReach),false,Pawn);Query.AddIgnoredActor(Target);
    FHitResult Wall;
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Wall,Pawn->GetPawnViewLocation(),Target->GetActorLocation()+FVector(0,0,70),ECC_Visibility,Query);
}
bool ResolveContainer(AActor* Target,FString& Key,int32& Pages,FString& Caption)
{
    if(auto* Scene=Cast<AColdSteelSceneContainer>(Target))
    {Key=Scene->StorageKey();Pages=FMath::Clamp(Scene->StoragePages,1,8);Caption=Scene->Caption;return !Key.IsEmpty();}
    if(ColdSteelWorldInteraction::IsTreasureChest(Target)&&!Target->ActorHasTag(TEXT("DungeonReward.Locked")))
    {Key=FColdSteelDungeonLoot::ChestStorageKey(Target);Pages=1;Caption=TEXT("宝箱战利品");return !Key.IsEmpty();}
    return false;
}
}
void UColdSteelSharedInventorySubsystem::FillContainerReply(AActor* Target,UColdSteelInventoryReply* Reply,const APawn* Viewer) const
{
    FString Key,Caption;int32 Pages=1;
    if(!Reply||!CanAccessContainer(Viewer,Target)||!ResolveContainer(Target,Key,Pages,Caption))return;
    const auto* Container=Current.Containers.Find(Key);if(!Container||!Container->bSeeded)return;
    Reply->bContainerView=true;Reply->ContainerKey=Key;Reply->ContainerCaption=Caption;
    Reply->ContainerPages=Container->Pages;Reply->ContainerRevision=Container->Revision;Reply->ContainerItems=Container->Items;
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
    Model->SyncRuntime();const auto Before=Model->Snapshot();auto Working=Before;
    UColdSteelStatusModel::StripNetworkContainerView(Working);
    CaptureDropTransforms();auto After=Current;auto& Container=After.Containers.FindOrAdd(Key);Container.Pages=Pages;
    const bool Open=Request.Action==EColdSteelInventoryAction::ContainerOpen;
    auto* SearchScene=Cast<AColdSteelSceneContainer>(Request.Target);
    const bool SearchLoot=ColdSteelSceneLoot::IsBound(SearchScene);
    const FString LegacyKey=SearchLoot?SearchScene->LegacyStorageKey():Key;
    // Older network saves used the map-only key; move the whole record, including contents.
    if(SearchLoot&&!Current.Containers.Contains(Key))
        if(const auto* Legacy=After.Containers.Find(LegacyKey))
        {const auto Copy=*Legacy;After.Containers.Remove(LegacyKey);After.Containers.FindChecked(Key)=Copy;
         for(auto& Item:Container.Items)Item.Container=Key;}
    auto HasPrivate=[&](const FColdSteelProfile& Profile)
    {return Profile.Items.ContainsByPredicate([&](const auto& I){return I.Place==4&&(I.Container==Key||I.Container==LegacyKey);});};
    if(!Open&&(!Container.bSeeded||(SearchLoot&&!Container.bSceneLootResolved)))
    {Reason=TEXT("请先搜索此容器");return false;}
    // Changing from solo to co-op can leave a host-owned private claim/content.
    // Only the host can move that profile and shared inventory in one existing journal.
    if(Open&&Guest&&SearchLoot&&!Container.bSceneLootResolved)
        if(const auto* Host=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Host
            &&(HasPrivate(Host->Snapshot())||Host->HasDungeonClaim(ColdSteelSceneLoot::Claim(SearchScene->ContainerId))))
        {Reason=TEXT("此旧存档容器需要房主先打开一次");return false;}
    if(Open&&Request.Target->ActorHasTag(TEXT("DungeonTreasure.HubTest"))&&Container.Items.IsEmpty())Container.bSeeded=false;
    if(Open&&Container.bSeeded&&(!SearchLoot||Container.bSceneLootResolved)&&!HasPrivate(Working))
    {
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
    Container.Items.Reset();
    for(auto Item:Working.Items)if(Item.Container==ViewKey){Item.Container=Key;Container.Items.Add(MoveTemp(Item));}
    UColdSteelStatusModel::StripNetworkContainerView(Working);
    Container.bSeeded=true;++Container.Revision;
    if(!Commit(Model,Guest,MoveTemp(Working),MoveTemp(After),Reason))return false;
    if(auto* Scene=Cast<AColdSteelSceneContainer>(Request.Target))Scene->OpenSharedVisual();
    else if(auto* PS=Pawn->GetPlayerState<AColdSteelPlayerState>())PS->MulticastSharedChestOpened(Request.Target);
    if(Reason.IsEmpty()||!bBlocked)Reason=Open?TEXT("已打开共享容器"):TEXT("共享物品已更新");
    if(!Open)for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
        if(*It!=Pawn->GetPlayerState<AColdSteelPlayerState>())It->ClientContainerInvalidated(Request.Target);
    return true;
}
