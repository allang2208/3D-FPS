#include "ColdSteelStatusModel.h"
#include "ColdSteelWarehouseRules.h"
#include "Kismet/GameplayStatics.h"

bool UColdSteelStatusModel::GrantDungeonReward(const FString& RunId,FName Claim,
    const TArray<TPair<FString,int64>>& Loot,FVector DropPosition)
{
    SyncRuntime();auto State=Snapshot();
    if(RunId.IsEmpty()||State.DungeonRun.RunId!=RunId||Claim.IsNone()||Loot.IsEmpty())return false;
    if(!AppendDungeonReward(State,Claim,Loot,DropPosition))return false;
    return CommitState(MoveTemp(State));
}

bool UColdSteelStatusModel::AppendDungeonReward(FColdSteelProfile& State,FName Claim,
    const TArray<TPair<FString,int64>>& Loot,FVector DropPosition)const
{
    if(State.DungeonRun.Claimed.Contains(Claim))return true;
    for(const auto& Pair:Loot)
    {
        if(Pair.Value<=0||Pair.Value>9007199254740991ll)return false;
        if(AmmoType(Pair.Key)){if(!AddAmmoToState(State,Pair.Key,Pair.Value))return false;continue;}
        if(!Definitions.Contains(Pair.Key))return false;
        auto Item=CreateItem(Pair.Key,Pair.Value);
        if(!ColdSteelInventory::Insert(State.Items,Item))
        {
            Item.Place=2;Item.Cell=-1;Item.BackpackCell=-1;
            Item.Map=UGameplayStatics::GetCurrentLevelName(this,true);
            Item.Position=DropPosition+FVector(0,0,12);State.Items.Add(MoveTemp(Item));
        }
    }
    State.DungeonRun.Claimed.Add(Claim);
    return true;
}

bool UColdSteelStatusModel::StoreDungeonChestLoot(const FString& RunId,FName Claim,
    const TArray<TPair<FString,int64>>& Loot,const FString& ContainerKey,int32 Pages,bool bHubTest)
{
    // 主神空间测试箱豁免运行匹配（RunId 可空）；正式地牢箱仍要求 RunId 与当前运行一致。
    if(!bHubTest&&(RunId.IsEmpty()||Current.DungeonRun.RunId!=RunId))return false;
    if(Claim.IsNone()||ContainerKey.IsEmpty())return false;
    if(Current.DungeonRun.Claimed.Contains(Claim))return true; // 已发放：不重 roll，交互层直接开面板
    SyncRuntime();auto State=Snapshot();
    // 容量登记与 BeginStorageSession 同口径（只增不减）；首次开箱即登记，面板后开也占住容量。
    {int32& Stored=State.StoragePages.FindOrAdd(ContainerKey);if(Stored<Pages)Stored=Pages;}
    for(const auto& Pair:Loot)
    {
        if(Pair.Value<=0||Pair.Value>9007199254740991ll)return false;
        if(AmmoType(Pair.Key)){if(!AddAmmoToState(State,Pair.Key,Pair.Value))return false;continue;}
        if(!Definitions.Contains(Pair.Key))return false;
        auto Item=CreateItem(Pair.Key,Pair.Value);
        Item.Place=ColdSteelWarehouse::Place;Item.Container=ContainerKey;
        // 一页 216 格 vs ≤16 次 roll 合并后的堆叠数，放不下只会是容量登记异常；整体失败让宝箱可重试。
        if(!ColdSteelWarehouse::Insert(State.Items,Item,FMath::Max(1,Pages)*ColdSteelWarehouse::CellsPerPage))return false;
    }
    State.DungeonRun.Claimed.Add(Claim);
    return CommitState(MoveTemp(State));
}

bool UColdSteelStatusModel::ReleaseHubTestClaimIfEmpty(const FString& ContainerKey,FName Claim)
{
    if(Claim.IsNone()||!Current.DungeonRun.Claimed.Contains(Claim))return false;
    for(const auto& I:Current.Items)if(I.Place==ColdSteelWarehouse::Place&&I.Container==ContainerKey)return false;
    SyncRuntime();auto State=Snapshot();
    State.DungeonRun.Claimed.Remove(Claim);
    return CommitState(MoveTemp(State));
}

bool UColdSteelStatusModel::ConvertChestAmmoToPool(const FString& Id)
{
    auto State=Snapshot();
    const int32 N=State.Items.IndexOfByPredicate([&](const auto& V){return V.InstanceId==Id;});
    if(N<0)return false;
    const FString Definition=State.Items[N].Definition;const int64 Count=State.Items[N].Count;
    State.Items.RemoveAt(N);
    if(!AddAmmoToState(State,Definition,Count))return false;
    if(!CommitState(MoveTemp(State)))return false;
    Message=FString::Printf(TEXT("弹药 x%lld 已装入弹药袋"),Count);
    OnChanged.Broadcast();
    return true;
}
