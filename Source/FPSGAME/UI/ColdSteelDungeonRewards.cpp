#include "ColdSteelStatusModel.h"
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
